"""Mesure du materiel de la machine hote (DEC-001).

Repond a une seule question : **de combien de memoire cette machine dispose-t-elle
pour faire tourner un modele en local ?** Rend un `HardwareProfile` gele, et rien
d'autre : ni modele, ni catalogue, ni recommandation.

Quatre regles le structurent.

1. **Un champ non mesure vaut ``None``, jamais ``0``, jamais une valeur devinee.**
   « Mesure : pas de GPU » et « non mesurable » sont deux etats differents : le
   premier s'ecrit `GPU_VENDOR_NONE`, le second ``None``. Leur confusion est la
   cause exacte de D-018, ou `scripts/build.py:71` retombe silencieusement sur
   ``"cpu"`` sur macOS faute de branche Darwin.
2. **Aucune dependance externe.** ``psutil`` est refuse, y compris en extra
   importe conditionnellement : cela recreerait deux chemins de code et deux
   verites sur le meme chiffre.
3. **La sonde primaire ne lance aucun sous-processus.** ``os.sysconf`` rend le
   meme octet exact que ``sysctl -n hw.memsize`` (mesure du 2026-09-04 sur Apple
   M1 Max : 34359738368 des deux cotes) et vaut aussi sous Linux. Les
   sous-processus ne servent qu'a ce qu'il ne donne pas : marque de GPU et VRAM.
4. **Aucune fraction de memoire unifiee n'est devinee.** Sur Apple Silicon, CPU et
   GPU puisent dans le meme reservoir et il n'existe **aucun champ VRAM** a
   mesurer (Apple, `developer.apple.com/videos/play/tech-talks/10580/`, consulte
   le 2026-09-04, releve dans `MEMORY/VEILLE.md`).

Ce module n'importe rien du catalogue de modeles, et reciproquement : garder
l'arete absente permet de livrer et de tester les deux separement. La composition
se fait chez l'appelant, en deux lignes.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

__all__ = [
    "GPU_VENDOR_NONE",
    "MEMORY_SOURCE_SYSCONF",
    "MEMORY_SOURCE_WIN32",
    "PROBE_TIMEOUT_SECONDS",
    "HardwareProfile",
    "detect_hardware",
]

#: Delai maximal accorde a un outil externe. Depasse, la sonde rend ``None``.
PROBE_TIMEOUT_SECONDS = 5.0

#: `HardwareProfile.gpu_vendor` : la sonde a **repondu** et n'a vu aucun GPU
#: discret. A ne jamais confondre avec ``None``, qui signifie « non mesurable ».
GPU_VENDOR_NONE = "none"

MEMORY_SOURCE_SYSCONF = "os.sysconf(SC_PHYS_PAGES) * os.sysconf(SC_PAGE_SIZE)"
MEMORY_SOURCE_WIN32 = "ctypes.windll.kernel32.GlobalMemoryStatusEx"

_MIB = 1024**2

# Notes rendues a l'utilisateur. Chacune dit ce qui n'a pas ete mesure et
# pourquoi ; aucune ne comble un trou par une valeur plausible.
_NOTE_UNIFIED = (
    "Memoire unifiee Apple Silicon : aucun champ VRAM n'existe a mesurer, CPU et GPU "
    "partagent le meme reservoir (tech-talks/10580, consulte le 2026-09-04)."
)
_NOTE_NO_GPU_RATIO = (
    "Fraction allouable au GPU non mesuree : `sysctl -n iogpu.wired_limit_mb` rend 0, "
    "qui signifie « defaut systeme » et non une capacite."
)
_NOTE_MAC_INTEL = (
    "Mac Intel : marque du GPU et VRAM non sondees. Non mesurable, pas « pas de GPU »."
)
_NOTE_NO_ARCH = "Architecture non lisible : memoire unifiee indeterminee."
_NOTE_NO_RAM_SYSCONF = "Memoire totale non mesurable : os.sysconf n'a pas repondu."
_NOTE_NO_RAM_WINDOWS = "Memoire totale non mesurable : GlobalMemoryStatusEx en echec."
_NOTE_NO_VRAM_LINUX = (
    "VRAM non mesurable : ni nvidia-smi ni rocm-smi n'ont produit de valeur exploitable. "
    "Absence de mesure, pas absence de GPU."
)
_NOTE_NO_VRAM_WINDOWS = (
    "VRAM non mesurable : nvidia-smi absent ou muet ; cote AMD aucun outil fiable n'est "
    "connu sous Windows, aucune valeur n'est donc devinee."
)
_NOTE_NO_VENDOR_LSPCI = "Marque du GPU non mesurable : lspci absent ou muet."
_NOTE_NO_VENDOR_WMI = "Marque du GPU non mesurable : PowerShell absent ou muet."
_NOTE_LSPCI_NO_GPU = "lspci a repondu sans exposer de GPU NVIDIA, AMD ou Intel."

#: Signature d'une sonde par sous-processus : commande et delai en entree,
#: sortie standard non vide ou ``None`` en sortie. Injectable pour les tests.
Runner = Callable[[list, float], "str | None"]


@dataclass(frozen=True)
class HardwareProfile:
    """Ce que la machine a laisse mesurer d'elle-meme.

    Attributes:
        system: ``"macos"``, ``"linux"``, ``"windows"`` ou ``"unknown"``.
        machine: Architecture rendue par ``platform.machine()``. ``None`` si
            vide.
        cpu_brand: Marque du processeur telle qu'annoncee par le systeme.
        gpu_vendor: ``"apple"``, ``"nvidia"``, ``"amd"``, ``"intel"``,
            `GPU_VENDOR_NONE` si la sonde a repondu sans voir de GPU discret,
            ``None`` si aucune sonde n'a pu repondre.
        gpu_name: Libelle du GPU quand la sonde en donne un.
        total_memory_bytes: Memoire physique totale. ``None`` si non mesuree.
        total_memory_source: Sonde ayant produit `total_memory_bytes`.
        vram_bytes: Memoire dediee du GPU. ``None`` si non mesuree **ou** si
            l'architecture n'en expose pas, ce qui est le cas de toute memoire
            unifiee.
        vram_source: Sonde ayant produit `vram_bytes`.
        unified_memory: ``True`` si CPU et GPU partagent le meme reservoir
            physique, ``False`` si la memoire est separee, ``None`` si
            indeterminable.
        notes: Ce qui n'a pas pu etre mesure, et pourquoi, en clair.
    """

    system: str
    machine: str | None = None
    cpu_brand: str | None = None
    gpu_vendor: str | None = None
    gpu_name: str | None = None
    total_memory_bytes: int | None = None
    total_memory_source: str | None = None
    vram_bytes: int | None = None
    vram_source: str | None = None
    unified_memory: bool | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("total_memory_bytes", "vram_bytes"):
            value = getattr(self, name)
            if value is None:
                continue
            if value <= 0:
                raise ValueError(f"{name} vaut {value} : une mesure absente s'ecrit None, jamais 0")

    @property
    def available_memory_bytes(self) -> int | None:
        """Octets utilisables pour l'inference, ou ``None`` si non mesures.

        Trois cas, dans cet ordre : memoire unifiee, le total physique est le
        budget ; VRAM dediee mesuree, elle seule compte, car les poids doivent
        tenir dans la carte ; sinon le total physique, l'inference se faisant
        alors sur le processeur. Aucune fraction, aucun abattement : deduire
        une reserve pour le systeme est une decision de recommandation, pas de
        mesure.
        """
        if self.unified_memory:
            return self.total_memory_bytes
        if self.vram_bytes is not None:
            return self.vram_bytes
        return self.total_memory_bytes

    @property
    def available_memory_basis(self) -> str | None:
        """Nature de `available_memory_bytes`, pour que rien ne soit implicite."""
        if self.available_memory_bytes is None:
            return None
        if self.unified_memory:
            return "unified_memory"
        if self.vram_bytes is not None:
            return "dedicated_vram"
        return "system_ram"


def detect_hardware(
    *,
    system: str | None = None,
    runner: Runner | None = None,
    timeout: float = PROBE_TIMEOUT_SECONDS,
) -> HardwareProfile:
    """Mesure la machine hote et rend son profil.

    Ne leve jamais sur une sonde en echec : outil absent, sortie illisible,
    delai depasse ou code de retour non nul produisent ``None`` sur le champ
    concerne et une note en clair, jamais une exception ni un ``0``.

    Args:
        system: Plateforme a sonder, parmi ``"macos"``, ``"linux"``,
            ``"windows"``. Deduite de ``sys.platform`` par defaut ; explicite
            pour tester une plateforme depuis une autre.
        runner: Executeur de sondes externes, injectable pour les tests.
        timeout: Delai accorde a chaque outil externe, en secondes.

    Returns:
        HardwareProfile: toujours un objet, jamais ``None``.
    """
    run = runner if runner is not None else _run
    host = system if system is not None else _current_system()
    machine = platform.machine().strip() or None

    if host == "macos":
        return _detect_macos(machine, run, timeout)
    if host == "linux":
        return _detect_linux(machine, run, timeout)
    if host == "windows":
        return _detect_windows(machine, run, timeout)
    return HardwareProfile(
        system=host,
        machine=machine,
        notes=(f"Plateforme {host!r} non couverte : rien n'a ete mesure.",),
    )


def _current_system() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    return "unknown"


def _detect_macos(machine: str | None, run: Runner, timeout: float) -> HardwareProfile:
    total, total_source = _total_memory_sysconf()
    apple_silicon = machine.startswith("arm") if machine else None
    notes: list[str] = []

    if apple_silicon:
        vendor: str | None = "apple"
        unified: bool | None = True
        notes.append(_NOTE_UNIFIED)
        notes.append(_NOTE_NO_GPU_RATIO)
    elif apple_silicon is False:
        vendor, unified = None, False
        notes.append(_NOTE_MAC_INTEL)
    else:
        vendor, unified = None, None
        notes.append(_NOTE_NO_ARCH)

    if total is None:
        notes.append(_NOTE_NO_RAM_SYSCONF)

    return HardwareProfile(
        system="macos",
        machine=machine,
        cpu_brand=run(["sysctl", "-n", "machdep.cpu.brand_string"], timeout),
        gpu_vendor=vendor,
        total_memory_bytes=total,
        total_memory_source=total_source,
        unified_memory=unified,
        notes=tuple(notes),
    )


def _detect_linux(machine: str | None, run: Runner, timeout: float) -> HardwareProfile:
    total, total_source = _total_memory_sysconf()
    notes: list[str] = []

    vram = _probe_nvidia_vram(run, timeout)
    vram_source: str | None = "nvidia-smi" if vram is not None else None
    if vram is None:
        vram = _probe_rocm_vram(run, timeout)
        vram_source = "rocm-smi" if vram is not None else None
    if vram is None:
        notes.append(_NOTE_NO_VRAM_LINUX)

    vendor, gpu_name = _probe_lspci_vendor(run, timeout)
    if vendor is None:
        notes.append(_NOTE_NO_VENDOR_LSPCI)
    elif vendor == GPU_VENDOR_NONE:
        notes.append(_NOTE_LSPCI_NO_GPU)
    if total is None:
        notes.append(_NOTE_NO_RAM_SYSCONF)

    return HardwareProfile(
        system="linux",
        machine=machine,
        cpu_brand=None,
        gpu_vendor=vendor,
        gpu_name=gpu_name,
        total_memory_bytes=total,
        total_memory_source=total_source,
        vram_bytes=vram,
        vram_source=vram_source,
        unified_memory=False,
        notes=tuple(notes),
    )


def _detect_windows(machine: str | None, run: Runner, timeout: float) -> HardwareProfile:
    total = _total_memory_windows()
    notes: list[str] = []
    if total is None:
        notes.append(_NOTE_NO_RAM_WINDOWS)

    vram = _probe_nvidia_vram(run, timeout)
    vendor, gpu_name = _probe_windows_vendor(run, timeout)
    if vram is None:
        notes.append(_NOTE_NO_VRAM_WINDOWS)
    if vendor is None:
        notes.append(_NOTE_NO_VENDOR_WMI)

    return HardwareProfile(
        system="windows",
        machine=machine,
        cpu_brand=os.environ.get("PROCESSOR_IDENTIFIER") or None,
        gpu_vendor=vendor,
        gpu_name=gpu_name,
        total_memory_bytes=total,
        total_memory_source=MEMORY_SOURCE_WIN32 if total is not None else None,
        vram_bytes=vram,
        vram_source="nvidia-smi" if vram is not None else None,
        unified_memory=False,
        notes=tuple(notes),
    )


def _run(command: list, timeout: float) -> str | None:
    """Execute un outil externe et rend sa sortie standard non vide.

    Rend ``None`` — jamais une exception, jamais ``0`` — si l'outil est absent,
    si le delai est depasse, si le code de retour n'est pas nul ou si la sortie
    est vide. Le binaire est resolu par `shutil.which` et lance sans shell.
    """
    executable = shutil.which(command[0])
    if executable is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - binaire resolu, aucun shell
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _total_memory_sysconf() -> tuple[int | None, str | None]:
    """Memoire physique totale par ``os.sysconf``, sans aucun sous-processus.

    Identique a ``sysctl -n hw.memsize`` sur macOS, a l'octet pres, et
    disponible aussi sur Linux.
    """
    names = getattr(os, "sysconf_names", {})
    if not hasattr(os, "sysconf") or "SC_PHYS_PAGES" not in names or "SC_PAGE_SIZE" not in names:
        return None, None
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError):
        return None, None
    if not isinstance(pages, int) or not isinstance(page_size, int):
        return None, None
    if pages <= 0 or page_size <= 0:
        return None, None
    return pages * page_size, MEMORY_SOURCE_SYSCONF


def _total_memory_windows() -> int | None:
    """Memoire physique totale sous Windows, par ``ctypes``, sans sous-processus.

    UNVERIFIED : non executable sur le poste de developpement (macOS). Ce
    chemin n'est couvert que par injection dans les tests.
    """
    import ctypes

    class _MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(_MemoryStatusEx)
    try:
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    except (AttributeError, OSError):
        return None
    if not ok:
        return None
    return int(status.ullTotalPhys) or None


def _probe_nvidia_vram(run: Runner, timeout: float) -> int | None:
    """VRAM NVIDIA en octets, ou ``None``.

    UNVERIFIED : ``nvidia-smi`` est absent du poste de developpement. Sur
    plusieurs cartes, la plus grande est retenue, un modele devant tenir dans
    une seule d'entre elles. Une seule ligne illisible invalide toute la
    mesure : mieux vaut ne rien rendre qu'un chiffre partiel.
    """
    output = run(
        ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], timeout
    )
    if output is None:
        return None
    values = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            mib = int(float(stripped))
        except ValueError:
            return None
        if mib > 0:
            values.append(mib)
    return max(values) * _MIB if values else None


def _probe_rocm_vram(run: Runner, timeout: float) -> int | None:
    """VRAM AMD en octets, ou ``None``.

    UNVERIFIED : ``rocm-smi`` est absent du poste de developpement, et le
    libelle exact de sa sortie n'a pas pu etre confirme. Le motif ne retient
    qu'un total exprime en octets ; toute autre forme rend ``None``.
    """
    output = run(["rocm-smi", "--showmeminfo", "vram"], timeout)
    if output is None:
        return None
    found = re.findall(r"[Tt]otal\s+[Mm]emory\s*\(B\)\s*:?\s*(\d+)", output)
    values = [int(value) for value in found if int(value) > 0]
    return max(values) if values else None


def _probe_lspci_vendor(run: Runner, timeout: float) -> tuple[str | None, str | None]:
    """Marque du GPU sous Linux, ou ``(None, None)`` si ``lspci`` n'a rien dit."""
    output = run(["lspci"], timeout)
    if output is None:
        return None, None
    for line in output.splitlines():
        lowered = line.lower()
        if not any(tag in lowered for tag in ("vga", "3d controller", "display controller")):
            continue
        vendor = _classify_gpu(lowered)
        if vendor is not None:
            return vendor, line.strip()
    return GPU_VENDOR_NONE, None


def _probe_windows_vendor(run: Runner, timeout: float) -> tuple[str | None, str | None]:
    """Marque du GPU sous Windows par WMI, ou ``(None, None)``.

    UNVERIFIED : PowerShell est absent du poste de developpement. La commande
    est celle deja utilisee par `launcher.py:194-259`, pour ne pas creer une
    seconde facon de poser la meme question.
    """
    output = run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name",
        ],
        timeout,
    )
    if output is None:
        return None, None
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        vendor = _classify_gpu(stripped.lower())
        if vendor is not None:
            return vendor, stripped
    return GPU_VENDOR_NONE, None


def _classify_gpu(lowered: str) -> str | None:
    """Marque reconnue dans un libelle de GPU, ou ``None`` si aucune."""
    if "nvidia" in lowered or "geforce" in lowered or "quadro" in lowered:
        return "nvidia"
    if "amd" in lowered or "advanced micro devices" in lowered or "radeon" in lowered:
        return "amd"
    if "intel" in lowered:
        return "intel"
    if "apple" in lowered:
        return "apple"
    return None
