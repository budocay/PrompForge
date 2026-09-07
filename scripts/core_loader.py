#!/usr/bin/env python3
"""Pont entre les amorceurs et les deux modules de mesure du coeur.

Pourquoi ce module existe
=========================

`launcher.py` et `scripts/build.py` doivent consommer deux modules du coeur :

* `promptforge/models_catalog.py` — le catalogue unique de DEC-003 ;
* `promptforge/hardware.py` — la mesure materielle de DEC-001.

Ils ne peuvent pas ecrire ``import promptforge``. Mesure du 2026-09-07 sur la
machine de reference, ou `launcher.py` tourne sous le Python systeme :

    $ /usr/bin/python3 --version
    Python 3.9.6
    $ /usr/bin/python3 -c "import promptforge"
    TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
      (promptforge/security.py:696, annotation evaluee a l'execution)

Le paquet exige 3.10 (`pyproject.toml`) et `promptforge/__init__.py` importe
`security.py`. Or `launcher.py` existe precisement pour amorcer une machine
nue, sur laquelle le seul interpreteur present est celui du systeme.

Trois issues ont ete pesees (D-061) :

(a) **Exiger 3.10 et echouer tot.** Honnete, mais l'amorceur cesserait de
    fonctionner sur la machine qu'il existe pour amorcer. C'est refuser le
    service pour respecter une contrainte que le service n'a pas.
(b) **Mode degrade sans catalogue.** Necessaire de toute facon — un depot
    incomplet reste possible — mais insuffisant seul : sous 3.9, le mode
    degrade serait le mode *nominal*, donc une interface qui ne mesure rien.
(c) **Charger les deux modules par chemin.** Retenue. Mesure du 2026-09-07 :

        mc OK ; hw OK ; tags 18
        macos arm64 34359738368 unified_memory True
        gpt-oss:20b / qwen3:32b / marge 16.0 Gio

    Les deux modules portent `from __future__ import annotations`, n'importent
    rien du paquet et n'utilisent aucune syntaxe posterieure a 3.9 a
    l'execution. Les charger par chemin evite `promptforge/__init__.py`, donc
    `security.py`, seul point de rupture.

(c) est retenue parce qu'elle est la seule qui **consomme la source unique**
sans rien en recopier : elle ferme D-018 et D-022 au lieu de les rouvrir sous
un autre nom. (b) reste cablee derriere, comme filet visible.

Piege mesure, a ne pas simplifier
=================================

La recette naive `spec_from_file_location` + `module_from_spec` +
`exec_module` **echoue sous 3.9** sur ces deux modules :

    AttributeError: 'NoneType' object has no attribute '__dict__'

`dataclasses` de 3.9 resout les annotations differees en lisant
``sys.modules[cls.__module__].__dict__`` sans verifier la presence de la cle.
Le module doit donc etre inscrit dans `sys.modules` **avant** `exec_module`.
Sous 3.14, la meme recette passe sans l'inscription : le defaut n'apparait que
sur la version qui compte. C'est la ligne `sys.modules[spec.name] = module`
ci-dessous, et elle n'est pas cosmetique.

Contraintes de ce fichier
=========================

Bibliotheque standard uniquement, et compatible 3.9 a l'execution : il est
importe par un amorceur qui tourne sous le Python systeme.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

__all__ = [
    "CoreBridge",
    "DEFAULT_PACKAGE_DIR",
    "compose_selection",
    "load_core",
]

#: Repertoire du paquet, deduit de l'emplacement de ce fichier.
DEFAULT_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "promptforge"

#: Modules du coeur charges par chemin, dans cet ordre.
_CORE_MODULES = ("models_catalog", "hardware")


def _load_module_at(path: Path, name: str):
    """Charge un module Python par chemin, sans passer par son paquet.

    Raises:
        FileNotFoundError: si le fichier est absent.
        ImportError: si l'interpreteur ne sait pas construire de chargeur.
        Exception: toute erreur levee par le module lui-meme.
    """
    if not path.exists():
        raise FileNotFoundError(str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"aucun chargeur pour {path}")
    module = importlib.util.module_from_spec(spec)
    # Obligatoire sous 3.9 : voir « Piege mesure » dans le docstring du module.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


class CoreBridge:
    """Les deux modules de mesure du coeur, ou l'explication de leur absence.

    Ne leve jamais a la construction : un depot incomplet, un fichier illisible
    ou un interpreteur trop ancien produisent `available is False` et un
    `error` en clair, destine a etre **affiche**. Un pont muet qui retomberait
    sur une liste en dur reconstituerait D-022 ; c'est exactement ce que ce
    type interdit en n'ayant aucune valeur de repli.

    Attributes:
        catalog_module: `promptforge/models_catalog.py` charge, ou ``None``.
        hardware_module: `promptforge/hardware.py` charge, ou ``None``.
        error: Motif de l'indisponibilite, en clair. ``None`` si tout va bien.
    """

    def __init__(self, catalog_module=None, hardware_module=None, error=None):
        self.catalog_module = catalog_module
        self.hardware_module = hardware_module
        self.error = error

    @property
    def available(self) -> bool:
        """``True`` si les deux modules du coeur ont ete charges."""
        return self.catalog_module is not None and self.hardware_module is not None

    # -- Catalogue ---------------------------------------------------------

    def models_by_footprint(self) -> tuple:
        """Le catalogue trie sur l'empreinte memoire decroissante (DEC-006).

        Rend un tuple vide quand le pont est indisponible : l'appelant doit
        alors afficher son etat degrade, pas une liste inventee.
        """
        if not self.available:
            return ()
        return self.catalog_module.by_memory_footprint()

    def known_tags(self) -> tuple:
        """Tags Ollama connus du catalogue, ou tuple vide."""
        if not self.available:
            return ()
        return self.catalog_module.known_tags()

    def is_known_tag(self, tag) -> bool:
        """``True`` si `tag` figure au catalogue."""
        return bool(tag) and tag in self.known_tags()

    def catalog_source(self):
        """Provenance et date de verification du catalogue, ou ``None``.

        Affichee telle quelle : une donnee montree a l'utilisateur porte sa
        source et sa date, sans quoi elle n'est pas montrable (DEC-004).
        """
        if not self.available:
            return None
        return {
            "source": self.catalog_module.CATALOG_SOURCE,
            "verified_on": self.catalog_module.CATALOG_VERIFIED_ON,
        }

    # -- Materiel ----------------------------------------------------------

    def detect_hardware(self):
        """Mesure la machine. Rend un `HardwareProfile`, ou ``None``."""
        if not self.available:
            return None
        return self.hardware_module.detect_hardware()

    def recommend_for(self, profile):
        """Recommande un modele pour un profil materiel mesure.

        Rend ``None`` si le pont est indisponible. Un profil sans mesure
        memoire produit une `Recommendation` marquee ``measured=False`` : le
        catalogue refuse deja de recommander au hasard, ce pont ne comble
        surtout pas ce trou.
        """
        if not self.available or profile is None:
            return None
        return self.catalog_module.recommend(
            profile.available_memory_bytes,
            unified=bool(profile.unified_memory),
        )


def load_core(package_dir=None) -> CoreBridge:
    """Charge le catalogue et la mesure materielle. Ne leve jamais.

    Args:
        package_dir: Repertoire du paquet `promptforge`. `DEFAULT_PACKAGE_DIR`
            par defaut ; explicite pour les tests du mode degrade.

    Returns:
        CoreBridge: toujours un objet, disponible ou non.
    """
    directory = Path(package_dir) if package_dir is not None else DEFAULT_PACKAGE_DIR
    loaded = {}
    for name in _CORE_MODULES:
        path = directory / f"{name}.py"
        try:
            loaded[name] = _load_module_at(path, f"_promptforge_core_{name}")
        except FileNotFoundError:
            return CoreBridge(error=f"module du coeur introuvable : {path}")
        except Exception as exc:  # noqa: BLE001 - le motif doit etre affiche
            return CoreBridge(
                error=f"{path.name} illisible sous Python "
                f"{sys.version_info[0]}.{sys.version_info[1]} : "
                f"{type(exc).__name__}: {exc}"
            )
    return CoreBridge(
        catalog_module=loaded["models_catalog"],
        hardware_module=loaded["hardware"],
    )


# ---------------------------------------------------------------------------
# Selection de compose a partir du materiel mesure
# ---------------------------------------------------------------------------
# Une seule table, consommee par `launcher.py` (qui propose la liste) et par
# `scripts/build.py -c auto` (qui retient la variante GPU). Les deux avaient
# leur propre `detect_gpu()` et leur propre mapping : c'est D-018, dont la
# moitie mesure disparait avec `detect_hardware()`. Laisser deux mappings
# derriere elle rouvrirait la meme faille par l'autre bout.
#
# Regle, en une phrase : `default` (compose.yaml, Ollama natif) partout ;
# une variante a Ollama conteneurise n'est proposee que la ou le GPU peut
# reellement etre expose a Docker, donc jamais sur macOS (D-020).

_SYSTEM_ALIASES = {
    "darwin": "macos",
    "macos": "macos",
    "windows": "windows",
    "win32": "windows",
    "linux": "linux",
}


def _normalize_system(system) -> str:
    """Normalise `platform.system()` ou `HardwareProfile.system`."""
    return _SYSTEM_ALIASES.get(str(system or "").strip().lower(), "unknown")


def compose_selection(system, gpu_vendor) -> dict:
    """Rend les cles de compose adaptees a une plateforme et un GPU mesure.

    Args:
        system: ``"Darwin"``, ``"Windows"``, ``"Linux"`` ou les formes rendues
            par `HardwareProfile.system` (``"macos"``...).
        gpu_vendor: ``"apple"``, ``"nvidia"``, ``"amd"``, ``"intel"``,
            ``"none"``, ou ``None`` quand aucune sonde n'a conclu. ``None`` et
            ``"none"`` sont traites pareil ici : dans les deux cas aucun GPU
            n'est expose a Docker de facon certaine, et proposer une variante
            GPU serait une affirmation non mesuree.

    Returns:
        dict: ``options`` (tuple de cles, `default` toujours en tete),
        ``default`` (toujours ``"default"``) et ``gpu_variant`` (la cle a
        Ollama conteneurise adaptee, ou ``None``).
    """
    host = _normalize_system(system)
    vendor = str(gpu_vendor or "").strip().lower() or None

    if host == "macos":
        # Docker Desktop ne passe pas Metal aux conteneurs : aucune variante
        # a Ollama conteneurise n'a de sens ici (D-020).
        return {"options": ("default",), "default": "default", "gpu_variant": None}

    if host == "windows":
        if vendor == "amd":
            # Docker n'accede pas au GPU AMD sous Windows : Ollama reste natif.
            return {
                "options": ("default", "win-amd", "cpu"),
                "default": "default",
                "gpu_variant": "win-amd",
            }
        if vendor == "nvidia":
            return {
                "options": ("default", "win-nvidia-native", "nvidia", "cpu"),
                "default": "default",
                "gpu_variant": "nvidia",
            }
        return {"options": ("default", "cpu"), "default": "default", "gpu_variant": None}

    if host == "linux":
        if vendor == "amd":
            return {
                "options": ("default", "linux-amd", "linux-amd-max", "cpu"),
                "default": "default",
                "gpu_variant": "linux-amd",
            }
        if vendor == "nvidia":
            return {
                "options": ("default", "nvidia", "cpu"),
                "default": "default",
                "gpu_variant": "nvidia",
            }
        return {"options": ("default", "cpu"), "default": "default", "gpu_variant": None}

    # Plateforme non reconnue : seul le chemin par defaut est sur.
    return {"options": ("default",), "default": "default", "gpu_variant": None}
