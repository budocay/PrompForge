"""Catalogue unique des modeles Ollama locaux (DEC-003).

Source unique et statique des faits connus sur les modeles executables en
local. Alimente depuis `MEMORY/VEILLE.md`, section « Catalogue de modeles
Ollama locaux », **verifiee le 2026-09-04**. Aucun chiffre n'est invente ici :
ce que la veille n'a pas confirme vaut ``None``, jamais ``0`` et jamais une
valeur devinee.

Trois regles structurent ce module.

1. **Aucun appel reseau, jamais.** Ce module n'importe ni ``urllib``, ni
   ``socket``, ni ``http``, ni ``requests`` : la promesse « 100 % local » de
   DEC-003 est verifiee par un test, pas seulement declaree. Les URL presentes
   sont des chaines de provenance destinees a l'affichage, jamais des cibles
   d'appel.

2. **Taille de telechargement et empreinte memoire sont deux nombres
   differents.** `LocalModel.download_size_bytes` est un **fait** releve sur la
   fiche officielle. `LocalModel.memory_footprint_bytes` est, pour toutes les
   entrees sauf une, une **estimation d'ingenierie** produite par la veille
   (taille des poids quantifies, integralement charges en memoire, plus 10 a
   20 % pour le cache K/V et les tampons, a fenetre de contexte courte a
   moyenne). `LocalModel.memory_footprint_basis` dit laquelle des deux natures
   s'applique, afin qu'une interface ne puisse pas presenter une estimation
   comme un fait. Seul ``gpt-oss:20b`` porte un chiffre officiel d'empreinte.
   Pour un modele a experts (MoE), l'empreinte est budgetee sur les parametres
   **totaux** : tous les experts resident en memoire, seuls quelques-uns
   s'activent par jeton.

3. **Aucune note de qualite.** Aucune source officielle, pour aucun modele, ne
   publie de score de suivi de format XML ou Markdown (veille du 2026-09-04,
   confirmee tag par tag ; dette D-021). Le classement se fait donc sur
   l'empreinte memoire et sur rien d'autre (DEC-006). Le banc d'evaluation de
   DEC-004 §2 pourra plus tard ajouter un second axe, mesure celui-la.

Le catalogue est un ``dict`` indexe par le **tag Ollama exact**, jamais par une
enumeration : un tag de registre bouge hors de notre controle, et le precedent
mesure de `TargetModel` (D-029) montre ce que coute une enumeration cablee au
niveau module. `get_model()` leve ``KeyError`` sur un tag inconnu ; il n'existe
aucun acces a repli muet, l'autre moitie de D-029.

Ce module ne connait pas le materiel : il n'importe rien de `hardware.py` et
`recommend()` ne prend pas de profil materiel, seulement un nombre d'octets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "BYTES_PER_SOURCE_GB",
    "CATALOG",
    "CATALOG_SOURCE",
    "CATALOG_VERIFIED_ON",
    "FOOTPRINT_ESTIMATED",
    "FOOTPRINT_OFFICIAL",
    "LocalModel",
    "Recommendation",
    "UNIFIED_MEMORY_RESERVE_BYTES",
    "by_memory_footprint",
    "get_model",
    "known_tags",
    "recommend",
]


CATALOG_SOURCE = "MEMORY/VEILLE.md, section « Catalogue de modeles Ollama locaux »"
CATALOG_VERIFIED_ON = "2026-09-04"

#: Nature d'une empreinte memoire : chiffre publie par la source officielle.
FOOTPRINT_OFFICIAL = "official"
#: Nature d'une empreinte memoire : estimation d'ingenierie de la veille.
FOOTPRINT_ESTIMATED = "estimated"

_FOOTPRINT_BASES = (FOOTPRINT_OFFICIAL, FOOTPRINT_ESTIMATED)

#: Interpretation du « GB » affiche par les fiches ``ollama.com/library``.
#:
#: Ces pages ecrivent par exemple « 5.2GB » sans preciser si l'unite est
#: decimale (10^9) ou binaire (2^30). Faute de source, on retient la lecture
#: binaire, qui est la **plus grande** des deux : si les fiches parlaient en
#: fait de gigaoctets decimaux, l'ecart de 7,4 % nous fait surestimer la
#: memoire requise, donc refuser un modele limite plutot que le recommander a
#: tort. L'erreur possible part ainsi du cote sur.
BYTES_PER_SOURCE_GB = 1024**3

#: Memoire laissee au systeme et aux applications sur une machine a memoire
#: unifiee, pour la recommandation **par defaut** uniquement.
#:
#: Fait source (Apple, `developer.apple.com/videos/play/tech-talks/10580/`,
#: consulte le 2026-09-04) : sur Apple Silicon, CPU et GPU puisent dans le meme
#: reservoir physique ; le modele charge, le systeme et les applications
#: ouvertes se partagent le meme total.
#:
#: **Jugement d'ingenierie, pas un seuil publie.** Aucune source Ollama ou
#: Apple ne documente de reserve minimale (`docs.ollama.com/gpu` consulte le
#: 2026-09-04 : une seule phrase sur Apple, rien de chiffre). La valeur retenue
#: encadre la seule graduation que la veille pose explicitement sur la machine
#: de reference (32 Go unifies) : elle qualifie « ~16 Go restants » de « choix
#: le plus sur » et « ~8-10 Go restants » de « marge etroite, a proposer comme
#: choix maximal, pas comme defaut ». 12 Gio se place entre les deux. Cette
#: reserve ne s'applique **qu'a** `Recommendation.recommended` ;
#: `Recommendation.maximum` et `Recommendation.fits` ne la subissent pas et
#: restent disponibles pour une interface qui veut afficher le choix maximal.
UNIFIED_MEMORY_RESERVE_BYTES = 12 * 1024**3

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _source_gb(value: float) -> int:
    """Convertit un chiffre releve en « GB » sur la fiche officielle en octets.

    Le nombre passe est celui **affiche par la source**, jamais un calcul
    maison. Voir `BYTES_PER_SOURCE_GB` pour l'interpretation de l'unite.
    """
    return int(round(value * BYTES_PER_SOURCE_GB))


@dataclass(frozen=True)
class LocalModel:
    """Faits connus sur un modele Ollama executable en local.

    Un champ vaut ``None`` quand la veille n'a pas confirme l'information sur
    la fiche officielle. Jamais ``0``, jamais une valeur plausible : le
    precedent `cached_input=0.0` de `ModelPricing` aurait facture un cache
    gratuit inexistant.

    Attributes:
        tag: Tag Ollama exact, tel qu'il s'ecrit dans ``ollama pull``.
        parameters_billions: Nombre **total** de parametres, en milliards.
            ``None`` si la fiche ne l'enonce pas.
        active_parameters_billions: Parametres actifs ou « effectifs » par
            jeton quand la source les annonce. Renseigne le cout de calcul,
            **jamais** l'empreinte memoire : un MoE charge tous ses experts.
        download_size_bytes: Taille de telechargement. **Fait source.**
        default_quantization: Quantization du tag par defaut. ``None`` quand la
            fiche ne la precise pas, ce qui est le cas le plus frequent.
        memory_footprint_bytes: Haut de fourchette de l'empreinte memoire
            d'inference, en octets. **Cle de tri du catalogue** (DEC-006).
            Nature donnee par `memory_footprint_basis` : ce n'est pas la taille
            de telechargement.
        memory_footprint_low_bytes: Bas de la meme fourchette. Egal au haut
            quand la source publie un chiffre unique.
        memory_footprint_basis: `FOOTPRINT_OFFICIAL` si la fiche publie
            l'empreinte, `FOOTPRINT_ESTIMATED` si elle est estimee.
        context_window_tokens: Fenetre de contexte annoncee. ``None`` si non
            confirmee pour ce tag precis.
        license_name: Nom de la licence tel qu'annonce.
        license_confirmed: ``True`` si la licence a ete lue sur la fiche ou la
            page de licence du tag, ``False`` si elle est deduite de la
            famille.
        source_url: Page officielle consultee.
        verified_on: Date de verification, ISO 8601.
        notes: Reserves et precisions de la veille, en clair.
    """

    tag: str
    parameters_billions: float | None
    active_parameters_billions: float | None
    download_size_bytes: int
    default_quantization: str | None
    memory_footprint_bytes: int
    memory_footprint_low_bytes: int
    memory_footprint_basis: str
    context_window_tokens: int | None
    license_name: str
    license_confirmed: bool
    source_url: str
    verified_on: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.tag or self.tag != self.tag.strip():
            raise ValueError(f"tag Ollama invalide : {self.tag!r}")
        if self.download_size_bytes <= 0:
            raise ValueError(f"{self.tag} : taille de telechargement invalide")
        if self.memory_footprint_basis not in _FOOTPRINT_BASES:
            raise ValueError(
                f"{self.tag} : nature d'empreinte inconnue "
                f"{self.memory_footprint_basis!r}, attendu l'une de {_FOOTPRINT_BASES}"
            )
        if self.memory_footprint_low_bytes > self.memory_footprint_bytes:
            raise ValueError(f"{self.tag} : fourchette d'empreinte inversee")
        if self.memory_footprint_low_bytes < self.download_size_bytes:
            raise ValueError(
                f"{self.tag} : empreinte memoire inferieure au poids telecharge ; "
                "les poids quantifies sont charges en entier en memoire"
            )
        if self.parameters_billions is not None and self.parameters_billions <= 0:
            raise ValueError(f"{self.tag} : nombre de parametres invalide")
        if self.context_window_tokens is not None and self.context_window_tokens <= 0:
            raise ValueError(f"{self.tag} : fenetre de contexte invalide")
        if not self.source_url.startswith("https://"):
            raise ValueError(f"{self.tag} : source_url absente ou non https")
        if not _ISO_DATE.match(self.verified_on):
            raise ValueError(f"{self.tag} : date de verification non ISO 8601")

    @property
    def memory_footprint_is_estimated(self) -> bool:
        """``True`` si l'empreinte est une estimation, pas un chiffre publie."""
        return self.memory_footprint_basis == FOOTPRINT_ESTIMATED

    @property
    def download_size_gb(self) -> float:
        """Taille de telechargement, dans l'unite affichee par la source."""
        return self.download_size_bytes / BYTES_PER_SOURCE_GB

    @property
    def memory_footprint_gb(self) -> float:
        """Haut de fourchette de l'empreinte memoire, en unites source."""
        return self.memory_footprint_bytes / BYTES_PER_SOURCE_GB

    @property
    def memory_footprint_low_gb(self) -> float:
        """Bas de fourchette de l'empreinte memoire, en unites source."""
        return self.memory_footprint_low_bytes / BYTES_PER_SOURCE_GB


# =============================================================================
# Le catalogue
#
# Un dict indexe par tag Ollama exact. Toutes les valeurs proviennent de
# MEMORY/VEILLE.md, section « Catalogue de modeles Ollama locaux », verifiee le
# 2026-09-04, fiche par fiche. Les fourchettes d'empreinte sont transcrites
# telles que la veille les publie ; elles ne sont pas recalculees ici.
# =============================================================================

_OLLAMA = "https://ollama.com/library"
_V = CATALOG_VERIFIED_ON

CATALOG: dict[str, LocalModel] = {
    # --- Palier CPU seul / faible RAM -----------------------------------
    "phi4-mini": LocalModel(
        tag="phi4-mini",
        parameters_billions=3.8,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(2.5),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(3.5),
        memory_footprint_low_bytes=_source_gb(3.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=128_000,
        license_name="MIT",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/phi4-mini",
        verified_on=_V,
        notes=(
            "Quantization non precisee sur la fiche ; le Q4_K_M usuel d'Ollama "
            "n'est pas confirme pour ce tag, donc non inscrit."
        ),
    ),
    "phi3:mini": LocalModel(
        tag="phi3:mini",
        parameters_billions=3.8,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(2.2),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(3.0),
        memory_footprint_low_bytes=_source_gb(2.5),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=128_000,
        license_name="MIT",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/phi3",
        verified_on=_V,
        notes=(
            "128K exige Ollama >= 0.1.39 ; la fiche annonce 4K par defaut en "
            "deca. Generation precedente de phi4-mini, meme editeur et meme "
            "palier : la veille le signale comme candidat au retrait "
            "(cutoff d'entrainement octobre 2023 affiche sur sa propre fiche)."
        ),
    ),
    "llama3.2:3b": LocalModel(
        tag="llama3.2:3b",
        parameters_billions=3.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(2.0),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(2.7),
        memory_footprint_low_bytes=_source_gb(2.3),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=128_000,
        license_name="Llama 3.2 Community License (seuil 700M MAU)",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/llama3.2",
        verified_on=_V,
        notes="Restriction contractuelle Meta : ce n'est pas de l'open source au sens OSI.",
    ),
    "gemma3n:e4b": LocalModel(
        tag="gemma3n:e4b",
        parameters_billions=6.87,
        active_parameters_billions=4.0,
        download_size_bytes=_source_gb(7.5),
        default_quantization="Q4_K_M",
        memory_footprint_bytes=_source_gb(9.0),
        memory_footprint_low_bytes=_source_gb(8.5),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=32_000,
        license_name="Gemma Terms of Use",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/gemma3n:e4b",
        verified_on=_V,
        notes=(
            "7,5 Go confirme sur la page de blob/licence du tag. Corrige les "
            "« 3GB » toujours affiches par launcher.py:1033 et "
            "OLLAMA_MODELS_INFO : sous-estimation d'un facteur 2,5 sur le "
            "palier qui vise justement les petites machines. « 4B effectifs » "
            "est le vocabulaire de la fiche, pour 6,87B bruts ; l'empreinte "
            "reste budgetee sur les poids telecharges. Licence lue sur la page "
            "de licence elle-meme, restriction contractuelle Google."
        ),
    ),
    "qwen3:4b": LocalModel(
        tag="qwen3:4b",
        parameters_billions=4.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(2.5),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(3.0),
        memory_footprint_low_bytes=_source_gb(2.8),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=256_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/qwen3/tags",
        verified_on=_V,
        notes=(
            "L'empreinte estimee vaut pour une fenetre courte a moyenne, "
            "conforme a la tache de PromptForge. Exploiter les 256K ferait "
            "grimper le cache K/V tres au-dela (docs.ollama.com/faq)."
        ),
    ),
    # --- Palier 8-16 Go --------------------------------------------------
    "mistral:7b": LocalModel(
        tag="mistral:7b",
        parameters_billions=7.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(4.4),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(5.3),
        memory_footprint_low_bytes=_source_gb(5.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=32_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/mistral",
        verified_on=_V,
    ),
    "qwen2.5-coder:7b": LocalModel(
        tag="qwen2.5-coder:7b",
        parameters_billions=7.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(4.7),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(5.6),
        memory_footprint_low_bytes=_source_gb(5.3),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=32_000,
        license_name="Apache-2.0",
        license_confirmed=False,
        source_url=f"{_OLLAMA}/qwen2.5-coder",
        verified_on=_V,
        notes=(
            "Licence deduite de la famille Qwen2.5, non affichee en toutes "
            "lettres sur la fiche consultee."
        ),
    ),
    "llama3.1:8b": LocalModel(
        tag="llama3.1:8b",
        parameters_billions=8.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(4.9),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(6.0),
        memory_footprint_low_bytes=_source_gb(5.5),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=128_000,
        license_name="Llama 3.1 Community License (seuil 700M MAU)",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/llama3.1",
        verified_on=_V,
        notes=(
            "Le tag nu « llama3.1 » resout vers celui-ci (confirme le "
            "2026-09-04). C'est le defaut cable dans providers.py et core.py, "
            "alors qu'aucune liste de recommandation du produit ne le propose "
            "(D-022). Restriction contractuelle Meta."
        ),
    ),
    "qwen3:8b": LocalModel(
        tag="qwen3:8b",
        parameters_billions=8.2,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(5.2),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(6.5),
        memory_footprint_low_bytes=_source_gb(6.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=40_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/qwen3/tags",
        verified_on=_V,
        notes=(
            "40K natif ; l'extension via YaRN n'a pas ete revalidee le "
            "2026-09-04, elle n'est donc pas portee ici. Quantization non "
            "confirmee sur cette fiche."
        ),
    ),
    "gpt-oss:20b": LocalModel(
        tag="gpt-oss:20b",
        parameters_billions=20.9,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(14.0),
        default_quantization="MXFP4",
        memory_footprint_bytes=_source_gb(16.0),
        memory_footprint_low_bytes=_source_gb(16.0),
        memory_footprint_basis=FOOTPRINT_OFFICIAL,
        context_window_tokens=128_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/gpt-oss:20b",
        verified_on=_V,
        notes=(
            "Seule entree du catalogue dont l'empreinte memoire est un chiffre "
            "officiel et non une estimation : la fiche affirme « enables the "
            "smaller model to run on systems with as little as 16GB memory ». "
            "MoE : 20,9B de parametres totaux tous residents en memoire, "
            "quantifies en MXFP4 (4,25 bits/parametre) ; le nombre de "
            "parametres actifs par jeton n'est pas enonce par la fiche, il "
            "reste donc absent. La fiche cite « structured outputs » parmi les "
            "capacites supportees ; c'est une fonctionnalite annoncee, pas une "
            "mesure de conformite de format."
        ),
    ),
    # --- Palier 12-16 Go dense -------------------------------------------
    "deepseek-r1:14b": LocalModel(
        tag="deepseek-r1:14b",
        parameters_billions=14.8,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(9.0),
        default_quantization="Q4_K_M",
        memory_footprint_bytes=_source_gb(10.5),
        memory_footprint_low_bytes=_source_gb(10.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=128_000,
        license_name="MIT (poids DeepSeek-R1) ; base Qwen2.5-14B sous Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/deepseek-r1:14b",
        verified_on=_V,
    ),
    "qwen2.5:14b": LocalModel(
        tag="qwen2.5:14b",
        parameters_billions=14.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(9.0),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(10.5),
        memory_footprint_low_bytes=_source_gb(10.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=32_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/qwen2.5",
        verified_on=_V,
        notes=(
            "32K est le contexte par defaut sous Ollama, pas la limite du "
            "modele : la fiche mentionne un support jusqu'a 128K. Generation "
            "precedente de qwen3:14b, meme palier : la veille le signale comme "
            "redondance intra-produit."
        ),
    ),
    "qwen2.5-coder:14b": LocalModel(
        tag="qwen2.5-coder:14b",
        parameters_billions=None,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(9.0),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(10.5),
        memory_footprint_low_bytes=_source_gb(10.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=32_000,
        license_name="Apache-2.0",
        license_confirmed=False,
        source_url=f"{_OLLAMA}/qwen2.5-coder",
        verified_on=_V,
        notes=(
            "Le nom du tag porte « 14b » mais la fiche ne l'enonce pas en "
            "toutes lettres : le champ parametres reste vide plutot que "
            "recopier le tag. Licence deduite de la famille Qwen2.5."
        ),
    ),
    "qwen3:14b": LocalModel(
        tag="qwen3:14b",
        parameters_billions=14.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(9.3),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(11.0),
        memory_footprint_low_bytes=_source_gb(10.5),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=40_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/qwen3/tags",
        verified_on=_V,
    ),
    # --- Palier 20-24 Go --------------------------------------------------
    "qwen3:30b-a3b": LocalModel(
        tag="qwen3:30b-a3b",
        parameters_billions=30.5,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(19.0),
        default_quantization="Q4_K_M",
        memory_footprint_bytes=_source_gb(23.0),
        memory_footprint_low_bytes=_source_gb(21.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=None,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/qwen3:30b-a3b",
        verified_on=_V,
        notes=(
            "MoE : empreinte budgetee sur les 30,5B de parametres totaux, "
            "jamais sur les parametres actifs. Les « ~3B actifs » se deduisent "
            "de la convention de nommage « A3B » et ne sont enonces nulle part "
            "sur la fiche : ils ne sont donc pas inscrits. Contexte non "
            "affiche sur la fiche de ce tag le 2026-09-04 (la famille qwen3 "
            "annonce 256K, non revalide pour ce tag)."
        ),
    ),
    "deepseek-r1:32b": LocalModel(
        tag="deepseek-r1:32b",
        parameters_billions=32.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(20.0),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(24.0),
        memory_footprint_low_bytes=_source_gb(22.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=128_000,
        license_name="MIT (poids)",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/deepseek-r1",
        verified_on=_V,
        notes=(
            "Quantization non confirmee pour ce tag precis (Q4_K_M confirme "
            "sur deepseek-r1:14b de la meme famille). Base distillee non "
            "confirmee pour ce tag : la licence de la base n'est donc pas "
            "inscrite, contrairement a deepseek-r1:14b."
        ),
    ),
    "qwen3:32b": LocalModel(
        tag="qwen3:32b",
        parameters_billions=32.0,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(20.0),
        default_quantization="Q4_K_M",
        memory_footprint_bytes=_source_gb(24.0),
        memory_footprint_low_bytes=_source_gb(22.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=40_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/qwen3:32b",
        verified_on=_V,
    ),
    # --- Au-dela de 32 Go -------------------------------------------------
    "llama3.1:70b": LocalModel(
        tag="llama3.1:70b",
        parameters_billions=None,
        active_parameters_billions=None,
        download_size_bytes=_source_gb(43.0),
        default_quantization=None,
        memory_footprint_bytes=_source_gb(50.0),
        memory_footprint_low_bytes=_source_gb(47.0),
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=None,
        license_name="Llama 3.1 Community License (seuil 700M MAU)",
        license_confirmed=True,
        source_url=f"{_OLLAMA}/llama3.1",
        verified_on=_V,
        notes=(
            "43 Go confirme, ce qui corrige les « 40GB » affiches par "
            "launcher.py:1043. Ne tient pas dans 32 Go unifies. La veille ne "
            "publie ni parametres ni fenetre de contexte pour ce tag precis : "
            "ces champs restent vides plutot que recopies de la famille. La "
            "veille signale llama3.3:70b comme remplacant de meme classe, "
            "encore absent du catalogue faute de faits complets."
        ),
    ),
}


def known_tags() -> tuple[str, ...]:
    """Tags du catalogue, dans l'ordre d'insertion."""
    return tuple(CATALOG)


def get_model(tag: str, catalog: dict[str, LocalModel] = CATALOG) -> LocalModel:
    """Rend l'entree de catalogue d'un tag Ollama.

    Aucun repli : un tag absent leve ``KeyError``. Servir silencieusement une
    autre entree est precisement ce qui rend D-029 indetectable.

    Raises:
        KeyError: si le tag n'est pas au catalogue.
    """
    try:
        return catalog[tag]
    except KeyError:
        raise KeyError(
            f"tag absent du catalogue : {tag!r}. Tags connus : {', '.join(catalog)}"
        ) from None


def by_memory_footprint(
    catalog: dict[str, LocalModel] = CATALOG, *, descending: bool = True
) -> tuple[LocalModel, ...]:
    """Trie le catalogue sur l'empreinte memoire d'inference (DEC-006).

    Le tri porte sur un fait ou une estimation de memoire, **jamais** sur une
    note de qualite : aucune source officielle n'en publie (D-021). Les egalites
    d'empreinte haute sont departagees par le bas de fourchette puis par le tag,
    pour un ordre stable et reproductible ; l'ordre decroissant est l'exact
    inverse de l'ordre croissant, egalites comprises.
    """
    ordered = sorted(
        catalog.values(),
        key=lambda m: (m.memory_footprint_bytes, m.memory_footprint_low_bytes, m.tag),
    )
    return tuple(reversed(ordered)) if descending else tuple(ordered)


@dataclass(frozen=True)
class Recommendation:
    """Resultat d'une recommandation de modele local.

    Attributes:
        recommended: Modele le plus lourd tenant dans le budget **par defaut**,
            reserve systeme deduite quand la memoire est unifiee. ``None`` si
            la memoire n'a pas ete mesuree ou si aucun modele ne tient.
        maximum: Modele le plus lourd tenant dans la memoire disponible, sans
            reserve. Egal a `recommended` hors memoire unifiee.
        fits: Tous les modeles tenant dans la memoire disponible, du plus lourd
            au plus leger.
        measured: ``False`` quand aucune mesure memoire n'a ete fournie. Dans
            ce cas rien n'est recommande : pas de repli muet vers un modele
            arbitraire.
        unified: Lecture memoire unifiee demandee par l'appelant.
        available_memory_bytes: Mesure recue, telle quelle.
        reserved_bytes: Reserve appliquee pour `recommended`.
        basis: Nature de l'empreinte de `recommended`, `FOOTPRINT_OFFICIAL` ou
            `FOOTPRINT_ESTIMATED`. ``None`` s'il n'y a pas de recommandation.
            Une interface doit le rendre visible : recommander « parce que ca
            tient » sur une estimation est plus faible que sur un chiffre
            officiel.
        reason: Explication en clair, destinee a l'utilisateur.
    """

    recommended: LocalModel | None
    maximum: LocalModel | None
    fits: tuple[LocalModel, ...]
    measured: bool
    unified: bool
    available_memory_bytes: int | None
    reserved_bytes: int
    basis: str | None
    reason: str

    @property
    def margin_bytes(self) -> int | None:
        """Memoire restante apres chargement de `recommended`, si connue."""
        if self.recommended is None or self.available_memory_bytes is None:
            return None
        return self.available_memory_bytes - self.recommended.memory_footprint_bytes


def recommend(
    available_memory_bytes: int | None,
    *,
    unified: bool = False,
    catalog: dict[str, LocalModel] = CATALOG,
) -> Recommendation:
    """Recommande un modele local a partir d'une mesure memoire, en octets.

    Cette fonction ne mesure rien et n'importe rien du materiel : elle recoit
    un nombre d'octets. La mesure est la charge de R-002 ; garder l'arete
    absente evite le couplage que DEC-001 et DEC-003 doivent pouvoir livrer
    separement.

    Le classement est celui de DEC-006 : empreinte memoire decroissante, jamais
    une note de qualite.

    Args:
        available_memory_bytes: Memoire disponible pour l'inference. ``None``
            quand aucune mesure n'a pu etre faite : le resultat est alors
            explicitement marque non mesure et ne recommande rien.
        unified: ``True`` pour une memoire unifiee, ou systeme et applications
            puisent dans le meme reservoir que le modele. Une reserve
            (`UNIFIED_MEMORY_RESERVE_BYTES`, jugement d'ingenierie) est alors
            deduite pour la recommandation par defaut, jamais pour `maximum`.
        catalog: Catalogue a consulter. Injectable pour les tests.

    Returns:
        Recommendation: toujours un objet, jamais ``None``.

    Raises:
        ValueError: si `available_memory_bytes` est negatif.
    """
    if available_memory_bytes is not None and available_memory_bytes < 0:
        raise ValueError(f"memoire disponible negative : {available_memory_bytes} octets")

    reserve = UNIFIED_MEMORY_RESERVE_BYTES if unified else 0

    if available_memory_bytes is None:
        return Recommendation(
            recommended=None,
            maximum=None,
            fits=(),
            measured=False,
            unified=unified,
            available_memory_bytes=None,
            reserved_bytes=reserve,
            basis=None,
            reason=(
                "Aucune mesure de memoire disponible : aucun modele n'est "
                "recommande. Choisir un modele au hasard reviendrait a "
                "presenter un defaut cable comme une recommandation."
            ),
        )

    ordered = by_memory_footprint(catalog)
    fits = tuple(m for m in ordered if m.memory_footprint_bytes <= available_memory_bytes)
    budget = available_memory_bytes - reserve
    default_fits = tuple(m for m in fits if m.memory_footprint_bytes <= budget)

    maximum = fits[0] if fits else None
    recommended = default_fits[0] if default_fits else None

    if recommended is None:
        if maximum is None:
            reason = (
                f"Aucun modele du catalogue ne tient dans "
                f"{_human_gb(available_memory_bytes)} de memoire disponible. "
                f"Le plus leger catalogue demande "
                f"{_human_gb(ordered[-1].memory_footprint_bytes)}."
                if ordered
                else "Catalogue vide : rien a recommander."
            )
        else:
            reason = (
                f"Aucun modele ne tient en laissant "
                f"{_human_gb(reserve)} au systeme. {maximum.tag} tient dans la "
                f"memoire disponible mais ne laisse que "
                f"{_human_gb(available_memory_bytes - maximum.memory_footprint_bytes)} : "
                "a proposer comme choix maximal, pas comme defaut."
            )
    else:
        nature = (
            "chiffre officiel de la fiche du modele"
            if recommended.memory_footprint_basis == FOOTPRINT_OFFICIAL
            else "estimation d'ingenierie, non mesuree sur cette machine"
        )
        reason = (
            f"{recommended.tag} est le modele le plus lourd tenant dans "
            f"{_human_gb(budget)}"
            + (
                f" ({_human_gb(available_memory_bytes)} disponibles moins "
                f"{_human_gb(reserve)} laisses au systeme et aux applications, "
                "memoire unifiee)"
                if unified
                else ""
            )
            + f". Empreinte retenue : {_human_gb(recommended.memory_footprint_bytes)} "
            f"({nature})."
        )

    return Recommendation(
        recommended=recommended,
        maximum=maximum,
        fits=fits,
        measured=True,
        unified=unified,
        available_memory_bytes=available_memory_bytes,
        reserved_bytes=reserve,
        basis=recommended.memory_footprint_basis if recommended else None,
        reason=reason,
    )


def _human_gb(num_bytes: int) -> str:
    """Rend un nombre d'octets en Go lisibles, pour les messages utilisateur."""
    return f"{num_bytes / BYTES_PER_SOURCE_GB:.1f} Go"
