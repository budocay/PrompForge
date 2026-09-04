"""Tests de `promptforge.hardware` — mesure materielle du coeur (DEC-001, R-002).

Trois familles de tests, dans cet ordre.

1. **Ce qui est reellement mesure sur ce poste** (Apple M1 Max, 32 Gio unifies) :
   la sonde primaire est confrontee a `sysctl -n hw.memsize`, et les echecs de
   sous-processus sont provoques pour de vrai (outil absent, code de retour non
   nul, delai depasse, sortie vide).
2. **Ce qui ne peut pas l'etre ici**, et qui est donc teste **par injection**,
   jamais en pretendant l'avoir execute : RAM Windows par `ctypes`, VRAM NVIDIA
   et AMD. Ces chemins restent `UNVERIFIED` sur une machine reelle.
3. **Les conditions de forme du gate** : aucune arete d'import avec
   `models_catalog` (C2), aucune dependance externe (C5), et la distinction
   entre « mesure : pas de GPU » et « non mesurable » (C3).
"""

from __future__ import annotations

import ast
import dataclasses
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from promptforge import hardware
from promptforge.hardware import (
    GPU_VENDOR_NONE,
    MEMORY_SOURCE_SYSCONF,
    MEMORY_SOURCE_WIN32,
    HardwareProfile,
    detect_hardware,
)

SOURCE_DIR = Path(hardware.__file__).parent
GIB = 1024**3
MIB = 1024**2


def fake_runner(responses: dict, calls: list | None = None):
    """Executeur de sondes injecte : rend la reponse prevue, sinon ``None``.

    ``None`` est la reponse par defaut, exactement comme quand un outil est
    absent du systeme.
    """

    def run(command, timeout):
        if calls is not None:
            calls.append((tuple(command), timeout))
        return responses.get(command[0])

    return run


def silent_runner(command, timeout):
    """Aucun outil ne repond, sur aucune plateforme."""
    return None


# =============================================================================
# 1. Mesure reelle sur ce poste
# =============================================================================


class TestRealMeasurementOnThisHost:
    def test_detect_hardware_never_raises_here(self):
        assert isinstance(detect_hardware(), HardwareProfile)

    def test_profile_is_internally_coherent(self):
        profile = detect_hardware()
        assert profile.system in {"macos", "linux", "windows", "unknown"}
        for value in (profile.total_memory_bytes, profile.vram_bytes):
            assert value is None or (isinstance(value, int) and value > 0)
        if profile.available_memory_bytes is None:
            assert profile.available_memory_basis is None
        else:
            assert profile.available_memory_basis in {
                "unified_memory",
                "dedicated_vram",
                "system_ram",
            }

    @pytest.mark.skipif(sys.platform != "darwin", reason="sonde comparee propre a macOS")
    def test_sysconf_returns_the_same_byte_as_sysctl_hw_memsize(self):
        """La sonde primaire, sans sous-processus, doit egaler `sysctl hw.memsize`."""
        reference = int(
            subprocess.run(
                ["/usr/sbin/sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.strip()
        )
        measured, source = hardware._total_memory_sysconf()
        assert measured == reference
        assert source == MEMORY_SOURCE_SYSCONF

    @pytest.mark.skipif(sys.platform != "darwin", reason="branche Apple Silicon")
    def test_apple_silicon_reports_unified_memory_and_no_vram(self):
        profile = detect_hardware()
        if profile.machine is None or not profile.machine.startswith("arm"):
            pytest.skip("Mac Intel : autre branche")
        assert profile.unified_memory is True
        assert profile.gpu_vendor == "apple"
        assert profile.vram_bytes is None, "la memoire unifiee n'expose aucun champ VRAM"
        assert profile.available_memory_basis == "unified_memory"
        assert profile.available_memory_bytes == profile.total_memory_bytes
        assert any("iogpu.wired_limit_mb" in note for note in profile.notes)

    @pytest.mark.skipif(sys.platform != "darwin", reason="sonde propre a macOS")
    def test_cpu_brand_is_read_from_the_system(self):
        assert detect_hardware().cpu_brand is not None


class TestRunProbeFailures:
    """C14 : chaque echec de sous-processus produit ``None``, jamais une exception."""

    @pytest.mark.skipif(sys.platform == "win32", reason="outils POSIX")
    def test_missing_tool_returns_none(self):
        assert hardware._run(["promptforge-outil-qui-nexiste-pas"], 5.0) is None

    @pytest.mark.skipif(shutil.which("false") is None, reason="`false` absent")
    def test_non_zero_return_code_returns_none(self):
        assert hardware._run(["false"], 5.0) is None

    @pytest.mark.skipif(shutil.which("true") is None, reason="`true` absent")
    def test_empty_output_returns_none(self):
        assert hardware._run(["true"], 5.0) is None

    @pytest.mark.skipif(shutil.which("sleep") is None, reason="`sleep` absent")
    def test_timeout_returns_none_without_waiting(self):
        started = time.monotonic()
        assert hardware._run(["sleep", "10"], 0.2) is None
        assert time.monotonic() - started < 5.0

    @pytest.mark.skipif(shutil.which("echo") is None, reason="`echo` absent")
    def test_successful_output_is_stripped(self):
        assert hardware._run(["echo", "  mesure  "], 5.0) == "mesure"


# =============================================================================
# 2. Chemins non executables ici : testes par injection (UNVERIFIED en reel)
# =============================================================================


class TestNvidiaVramProbe:
    """UNVERIFIED sur machine reelle : `nvidia-smi` est absent de ce poste."""

    def test_absent_tool_yields_none(self):
        assert hardware._probe_nvidia_vram(silent_runner, 5.0) is None

    def test_unreadable_output_yields_none(self):
        run = fake_runner({"nvidia-smi": "N/A"})
        assert hardware._probe_nvidia_vram(run, 5.0) is None

    def test_zero_is_reported_as_none_never_as_zero(self):
        run = fake_runner({"nvidia-smi": "0"})
        assert hardware._probe_nvidia_vram(run, 5.0) is None

    def test_single_card_is_converted_from_mib(self):
        run = fake_runner({"nvidia-smi": "24576"})
        assert hardware._probe_nvidia_vram(run, 5.0) == 24576 * MIB

    def test_largest_card_wins_and_blank_lines_are_tolerated(self):
        run = fake_runner({"nvidia-smi": "8192\n\n24576\n"})
        assert hardware._probe_nvidia_vram(run, 5.0) == 24576 * MIB

    def test_one_unreadable_line_invalidates_the_whole_measure(self):
        run = fake_runner({"nvidia-smi": "8192\n[Insufficient Permissions]"})
        assert hardware._probe_nvidia_vram(run, 5.0) is None

    def test_query_is_the_documented_one(self):
        calls: list = []
        hardware._probe_nvidia_vram(fake_runner({}, calls), 3.0)
        assert calls == [
            (
                ("nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"),
                3.0,
            )
        ]


class TestRocmVramProbe:
    """UNVERIFIED sur machine reelle : `rocm-smi` est absent de ce poste."""

    def test_absent_tool_yields_none(self):
        assert hardware._probe_rocm_vram(silent_runner, 5.0) is None

    def test_unreadable_output_yields_none(self):
        run = fake_runner({"rocm-smi": "GPU[0] : vram Total Memory : inconnue"})
        assert hardware._probe_rocm_vram(run, 5.0) is None

    def test_total_in_bytes_is_read_as_is(self):
        run = fake_runner({"rocm-smi": "GPU[0] : vram Total Memory (B): 17163091968"})
        assert hardware._probe_rocm_vram(run, 5.0) == 17163091968

    def test_zero_is_reported_as_none(self):
        run = fake_runner({"rocm-smi": "GPU[0] : vram Total Memory (B): 0"})
        assert hardware._probe_rocm_vram(run, 5.0) is None


class TestWindowsMemory:
    """UNVERIFIED sur machine reelle : `ctypes.windll` n'existe pas sur ce poste."""

    @pytest.mark.skipif(sys.platform == "win32", reason="chemin hors Windows")
    def test_off_windows_the_probe_returns_none_without_raising(self):
        assert hardware._total_memory_windows() is None

    def test_measured_memory_is_reported_with_its_source(self, monkeypatch):
        monkeypatch.setattr(hardware, "_total_memory_windows", lambda: 34359738368)
        profile = detect_hardware(system="windows", runner=silent_runner)
        assert profile.total_memory_bytes == 34359738368
        assert profile.total_memory_source == MEMORY_SOURCE_WIN32

    def test_failed_probe_yields_none_and_a_note(self, monkeypatch):
        monkeypatch.setattr(hardware, "_total_memory_windows", lambda: None)
        profile = detect_hardware(system="windows", runner=silent_runner)
        assert profile.total_memory_bytes is None
        assert profile.total_memory_source is None
        assert profile.available_memory_bytes is None
        assert any("GlobalMemoryStatusEx" in note for note in profile.notes)


class TestWindowsDetection:
    """UNVERIFIED sur machine reelle : ni PowerShell ni nvidia-smi ne sont ici."""

    def test_amd_card_is_named_but_its_vram_stays_unmeasured(self, monkeypatch):
        monkeypatch.setattr(hardware, "_total_memory_windows", lambda: 16 * GIB)
        run = fake_runner({"powershell": "AMD Radeon RX 7900 XTX"})
        profile = detect_hardware(system="windows", runner=run)
        assert profile.gpu_vendor == "amd"
        assert profile.gpu_name == "AMD Radeon RX 7900 XTX"
        assert profile.vram_bytes is None
        assert any("aucun outil fiable" in note for note in profile.notes)

    def test_nvidia_vram_is_preferred_over_system_memory(self, monkeypatch):
        monkeypatch.setattr(hardware, "_total_memory_windows", lambda: 64 * GIB)
        run = fake_runner({"nvidia-smi": "12288", "powershell": "NVIDIA GeForce RTX 4070"})
        profile = detect_hardware(system="windows", runner=run)
        assert profile.gpu_vendor == "nvidia"
        assert profile.vram_bytes == 12288 * MIB
        assert profile.vram_source == "nvidia-smi"
        assert profile.available_memory_bytes == 12288 * MIB
        assert profile.available_memory_basis == "dedicated_vram"

    def test_no_tool_at_all_yields_none_everywhere(self, monkeypatch):
        monkeypatch.setattr(hardware, "_total_memory_windows", lambda: None)
        profile = detect_hardware(system="windows", runner=silent_runner)
        assert profile.gpu_vendor is None
        assert profile.gpu_name is None
        assert profile.vram_bytes is None
        assert profile.unified_memory is False


class TestLinuxDetection:
    def test_measured_absence_of_gpu_differs_from_unmeasurable(self):
        """C3 : `lspci` muet vaut ``None``, `lspci` sans GPU vaut `GPU_VENDOR_NONE`."""
        unmeasurable = detect_hardware(system="linux", runner=silent_runner)
        assert unmeasurable.gpu_vendor is None
        assert any("lspci absent ou muet" in note for note in unmeasurable.notes)

        no_gpu = detect_hardware(
            system="linux",
            runner=fake_runner({"lspci": "00:1f.2 SATA controller: Intel Corp. C610"}),
        )
        assert no_gpu.gpu_vendor == GPU_VENDOR_NONE
        assert no_gpu.gpu_vendor is not None
        assert any("sans exposer de GPU" in note for note in no_gpu.notes)

    def test_nvidia_card_is_recognised_on_the_display_line(self):
        run = fake_runner(
            {
                "lspci": (
                    "00:02.0 Host bridge: Intel Corp. Xeon E3\n"
                    "01:00.0 VGA compatible controller: NVIDIA Corp. GA104 [RTX 3070]"
                ),
                "nvidia-smi": "8192",
            }
        )
        profile = detect_hardware(system="linux", runner=run)
        assert profile.gpu_vendor == "nvidia"
        assert "RTX 3070" in profile.gpu_name
        assert profile.vram_bytes == 8192 * MIB

    def test_rocm_is_used_only_when_nvidia_smi_says_nothing(self):
        run = fake_runner(
            {
                "rocm-smi": "GPU[0] : vram Total Memory (B): 17163091968",
                "lspci": "0a:00.0 VGA compatible controller: Advanced Micro Devices, Inc. Navi 31",
            }
        )
        profile = detect_hardware(system="linux", runner=run)
        assert profile.gpu_vendor == "amd"
        assert profile.vram_bytes == 17163091968
        assert profile.vram_source == "rocm-smi"

    def test_without_any_gpu_tool_the_budget_falls_back_to_system_ram(self):
        profile = detect_hardware(system="linux", runner=silent_runner)
        assert profile.unified_memory is False
        assert profile.vram_bytes is None
        assert profile.vram_source is None
        assert any("VRAM non mesurable" in note for note in profile.notes)
        if profile.total_memory_bytes is not None:
            assert profile.available_memory_basis == "system_ram"
            assert profile.available_memory_bytes == profile.total_memory_bytes


class TestUnknownPlatform:
    def test_nothing_is_invented_on_an_uncovered_platform(self):
        profile = detect_hardware(system="haiku", runner=silent_runner)
        assert profile.system == "haiku"
        assert profile.total_memory_bytes is None
        assert profile.vram_bytes is None
        assert profile.gpu_vendor is None
        assert profile.unified_memory is None
        assert profile.available_memory_bytes is None
        assert profile.notes


# =============================================================================
# 3. Contrat de la dataclass et conditions de forme du gate
# =============================================================================


class TestHardwareProfileContract:
    def test_zero_bytes_is_refused_because_absence_is_written_none(self):
        for field_name in ("total_memory_bytes", "vram_bytes"):
            with pytest.raises(ValueError, match="jamais 0"):
                HardwareProfile(system="linux", **{field_name: 0})

    def test_negative_bytes_is_refused(self):
        with pytest.raises(ValueError):
            HardwareProfile(system="linux", total_memory_bytes=-1)

    def test_profile_is_frozen(self):
        profile = HardwareProfile(system="linux")
        with pytest.raises(dataclasses.FrozenInstanceError):
            profile.total_memory_bytes = 1

    def test_unified_memory_uses_the_whole_pool_without_any_fraction(self):
        profile = HardwareProfile(system="macos", total_memory_bytes=32 * GIB, unified_memory=True)
        assert profile.available_memory_bytes == 32 * GIB
        assert profile.available_memory_basis == "unified_memory"

    def test_dedicated_vram_wins_over_system_ram(self):
        profile = HardwareProfile(
            system="linux",
            total_memory_bytes=64 * GIB,
            vram_bytes=8 * GIB,
            unified_memory=False,
        )
        assert profile.available_memory_bytes == 8 * GIB
        assert profile.available_memory_basis == "dedicated_vram"

    def test_no_measure_at_all_yields_none_not_zero(self):
        profile = HardwareProfile(system="unknown")
        assert profile.available_memory_bytes is None
        assert profile.available_memory_basis is None
        assert profile.notes == ()


class TestGateConditions:
    """C2 et C5, verifies par lecture de l'arbre syntaxique, pas par confiance."""

    @staticmethod
    def _imports(module_path: Path) -> set:
        roots = set()
        for node in ast.walk(ast.parse(module_path.read_text())):
            if isinstance(node, ast.Import):
                roots.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    roots.add("." * node.level + (node.module or ""))
                elif node.module:
                    roots.add(node.module)
        return roots

    def test_no_edge_between_hardware_and_models_catalog(self):
        """C2 : aucune arete, dans aucun sens, annotations comprises."""
        from_hardware = self._imports(SOURCE_DIR / "hardware.py")
        from_catalog = self._imports(SOURCE_DIR / "models_catalog.py")
        assert not any("models_catalog" in name for name in from_hardware)
        assert not any("hardware" in name for name in from_catalog)

    def test_the_two_modules_form_a_graph_without_any_cycle(self):
        """C2 : sous-graphe des deux modules, zero arete donc zero cycle."""
        edges = {
            "hardware": {
                n for n in self._imports(SOURCE_DIR / "hardware.py") if "models_catalog" in n
            },
            "models_catalog": {
                n for n in self._imports(SOURCE_DIR / "models_catalog.py") if "hardware" in n
            },
        }
        assert edges == {"hardware": set(), "models_catalog": set()}

    def test_hardware_imports_only_the_standard_library(self):
        """C5 : aucune dependance obligatoire nouvelle, `psutil` compris."""
        for name in self._imports(SOURCE_DIR / "hardware.py"):
            root = name.split(".")[0]
            assert root in sys.stdlib_module_names, f"import non stdlib : {name}"

    def test_psutil_is_never_imported_even_conditionally(self):
        """C5 : un import conditionnel recreerait deux chemins et deux verites."""
        source = (SOURCE_DIR / "hardware.py").read_text()
        assert not any("psutil" in name for name in self._imports(SOURCE_DIR / "hardware.py"))
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            target = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if target in {"import_module", "__import__"}:
                for arg in node.args:
                    assert not (isinstance(arg, ast.Constant) and "psutil" in str(arg.value))

    def test_no_gpu_ratio_is_probed_nor_applied_on_apple_silicon(self):
        """C7 : `iogpu.wired_limit_mb` rend 0, un defaut systeme, pas une capacite.

        Verifie sur le comportement et non sur le texte : aucune commande lancee
        sur la branche macOS ne l'interroge, et la memoire rapportee est le
        reservoir unifie entier, sans la moindre fraction.
        """
        calls: list = []
        profile = detect_hardware(system="macos", runner=fake_runner({}, calls))
        assert calls, "la branche macOS doit lancer au moins la sonde de marque CPU"
        for command, _timeout in calls:
            joined = " ".join(command)
            assert "iogpu" not in joined
            assert "wired_limit" not in joined
        assert profile.available_memory_bytes == profile.total_memory_bytes

        unified = HardwareProfile(system="macos", total_memory_bytes=32 * GIB, unified_memory=True)
        assert unified.available_memory_bytes == 32 * GIB
