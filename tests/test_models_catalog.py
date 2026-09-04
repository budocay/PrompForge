"""Tests du catalogue de modeles Ollama locaux (R-007 bloc 1, DEC-003).

Ces tests verifient les conditions bloquantes de l'ARCHITECTURE GATE amont, en
particulier :

- C1 : le catalogue est un ``dict`` indexe par tag exact, sans enumeration et
  sans acces a repli muet ;
- C2 : aucune arete vers `hardware.py`, qui n'existe pas encore ;
- C3 : un fait non confirme vaut ``None``, jamais ``0`` ;
- C4 : taille de telechargement et empreinte memoire sont deux champs
  distincts, et la nature de l'empreinte (officielle ou estimee) est portee par
  le schema ;
- C6 : `recommend()` classe sur l'empreinte memoire (DEC-006) et ne recommande
  rien quand la memoire n'est pas mesuree ;
- C13 : le module n'utilise aucun module reseau.
"""

import ast
import importlib.util
import sys
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from promptforge import models_catalog as mc
from promptforge.models_catalog import (
    BYTES_PER_SOURCE_GB,
    CATALOG,
    FOOTPRINT_ESTIMATED,
    FOOTPRINT_OFFICIAL,
    UNIFIED_MEMORY_RESERVE_BYTES,
    LocalModel,
    by_memory_footprint,
    get_model,
    known_tags,
    recommend,
)

GIB = 1024**3

MODULE_PATH = Path(mc.__file__)

#: Les dix-huit tags retenus par R-007 bloc 1, tous confirmes par la veille du
#: 2026-09-04. Ce pin fait echouer un retrait ou un ajout silencieux.
EXPECTED_TAGS = {
    "phi4-mini",
    "phi3:mini",
    "llama3.2:3b",
    "gemma3n:e4b",
    "qwen3:4b",
    "mistral:7b",
    "qwen2.5-coder:7b",
    "llama3.1:8b",
    "qwen3:8b",
    "gpt-oss:20b",
    "deepseek-r1:14b",
    "qwen2.5:14b",
    "qwen2.5-coder:14b",
    "qwen3:14b",
    "qwen3:30b-a3b",
    "deepseek-r1:32b",
    "qwen3:32b",
    "llama3.1:70b",
}


def _sample_model(**overrides):
    """Construit un `LocalModel` valide, surchargeable champ par champ."""
    base = dict(
        tag="fake:1b",
        parameters_billions=1.0,
        active_parameters_billions=None,
        download_size_bytes=1 * GIB,
        default_quantization=None,
        memory_footprint_bytes=2 * GIB,
        memory_footprint_low_bytes=2 * GIB,
        memory_footprint_basis=FOOTPRINT_ESTIMATED,
        context_window_tokens=8_000,
        license_name="Apache-2.0",
        license_confirmed=True,
        source_url="https://ollama.com/library/fake",
        verified_on="2026-09-04",
    )
    base.update(overrides)
    return LocalModel(**base)


# ===========================================================================
# C1 — dict indexe par tag, aucune enumeration, aucun repli muet
# ===========================================================================


class TestCatalogShape:
    def test_catalog_is_a_plain_dict_keyed_by_tag(self):
        assert isinstance(CATALOG, dict)
        assert CATALOG, "catalogue vide"
        for key, model in CATALOG.items():
            assert isinstance(key, str), f"cle non textuelle : {key!r}"
            assert key == model.tag, f"cle {key!r} desynchronisee du tag {model.tag!r}"

    def test_catalog_holds_the_eighteen_verified_tags(self):
        assert set(CATALOG) == EXPECTED_TAGS
        assert set(known_tags()) == EXPECTED_TAGS

    def test_module_declares_no_enum_of_local_models(self):
        """`TargetModel` a produit D-029 : pas de seconde enumeration cablee."""
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert "Enum" not in source
        assert "from enum" not in source
        assert "import enum" not in source

    def test_get_model_returns_the_requested_entry(self):
        assert get_model("qwen3:8b") is CATALOG["qwen3:8b"]

    def test_get_model_raises_on_unknown_tag_instead_of_falling_back(self):
        """Le `.get()` a repli muet de `get_profile()` est l'autre moitie de D-029."""
        with pytest.raises(KeyError) as excinfo:
            get_model("qwen3:9999b")
        assert "qwen3:9999b" in str(excinfo.value)
        assert "qwen3:8b" in str(excinfo.value), "le message doit lister les tags connus"

    def test_get_model_accepts_an_injected_catalog(self):
        catalog = {"fake:1b": _sample_model()}
        assert get_model("fake:1b", catalog).tag == "fake:1b"
        with pytest.raises(KeyError):
            get_model("qwen3:8b", catalog)

    def test_entries_are_frozen(self):
        with pytest.raises(FrozenInstanceError):
            CATALOG["qwen3:8b"].tag = "autre"


# ===========================================================================
# C2 et C13 — aucune arete vers hardware.py, aucun module reseau
# ===========================================================================


class _StringBlanker(ast.NodeTransformer):
    """Vide les chaines litterales pour ne laisser que le code executable.

    Sans cela, le simple fait de citer une URL de source (`https://...`) ferait
    apparaitre le mot `http` dans le texte du module.
    """

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.copy_location(ast.Constant(value=""), node)
        return node


def _code_without_string_literals() -> str:
    tree = _StringBlanker().visit(ast.parse(MODULE_PATH.read_text(encoding="utf-8")))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _imported_roots() -> set:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


class TestNoForbiddenEdges:
    def test_module_uses_no_network_module(self):
        """DEC-003 : la promesse « 100 % local » est verifiee, pas declaree."""
        code = _code_without_string_literals()
        for forbidden in ("urllib", "socket", "http", "requests"):
            assert forbidden not in code, f"{forbidden} apparait dans le code du module"

    def test_module_imports_only_the_standard_library_it_needs(self):
        assert _imported_roots() == {"__future__", "re", "dataclasses"}

    def test_module_has_no_edge_to_hardware(self):
        """C2 : `hardware.py` n'existe pas encore, et l'arete ne doit jamais exister."""
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert "hardware" not in _code_without_string_literals()
        assert "import hardware" not in source
        assert "from promptforge.hardware" not in source

    def test_recommend_signature_takes_bytes_not_a_hardware_profile(self):
        import inspect

        params = inspect.signature(recommend).parameters
        assert list(params) == ["available_memory_bytes", "unified", "catalog"]
        assert params["unified"].kind is inspect.Parameter.KEYWORD_ONLY
        assert params["catalog"].kind is inspect.Parameter.KEYWORD_ONLY
        assert params["catalog"].default is CATALOG

    def test_module_loads_standalone_without_the_promptforge_package(self):
        """Utile a `launcher.py`, qui amorce une machine nue (D-061)."""
        name = "_isolated_models_catalog"
        spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            assert len(module.CATALOG) == len(CATALOG)
        finally:
            sys.modules.pop(name, None)


# ===========================================================================
# C4 — taille de telechargement et empreinte memoire, deux nombres distincts
# ===========================================================================


class TestDownloadSizeVersusMemoryFootprint:
    def test_schema_carries_both_numbers_separately(self):
        names = {f.name for f in fields(LocalModel)}
        assert {"download_size_bytes", "memory_footprint_bytes"} <= names
        assert "memory_footprint_basis" in names

    def test_no_entry_confuses_the_two_numbers(self):
        """Une empreinte egale au poids telecharge serait la confusion de D-053."""
        for model in CATALOG.values():
            assert model.memory_footprint_bytes != model.download_size_bytes, model.tag
            assert model.memory_footprint_low_bytes >= model.download_size_bytes, model.tag

    def test_only_gpt_oss_20b_carries_an_official_footprint(self):
        official = [m.tag for m in CATALOG.values() if not m.memory_footprint_is_estimated]
        assert official == ["gpt-oss:20b"]

    def test_gpt_oss_20b_official_footprint_is_sixteen_gb(self):
        model = CATALOG["gpt-oss:20b"]
        assert model.memory_footprint_basis == FOOTPRINT_OFFICIAL
        assert model.memory_footprint_bytes == 16 * GIB
        assert model.memory_footprint_low_bytes == model.memory_footprint_bytes
        assert model.download_size_bytes == 14 * GIB

    def test_every_other_entry_is_flagged_as_an_estimate(self):
        for tag, model in CATALOG.items():
            if tag == "gpt-oss:20b":
                continue
            assert model.memory_footprint_basis == FOOTPRINT_ESTIMATED, tag
            assert model.memory_footprint_is_estimated, tag

    def test_moe_footprint_is_budgeted_on_total_parameters(self):
        """Un MoE charge tous ses experts : jamais budgeter sur les actifs."""
        moe = CATALOG["qwen3:30b-a3b"]
        assert moe.parameters_billions == 30.5
        assert moe.active_parameters_billions is None
        assert moe.memory_footprint_low_bytes > moe.download_size_bytes

    def test_download_sizes_corrected_by_the_veille(self):
        """launcher.py annonce 40GB et 3GB ; la veille mesure 43 Go et 7,5 Go."""
        assert CATALOG["llama3.1:70b"].download_size_gb == pytest.approx(43.0)
        assert CATALOG["gemma3n:e4b"].download_size_gb == pytest.approx(7.5)

    def test_source_gb_unit_is_documented_and_conservative(self):
        assert BYTES_PER_SOURCE_GB == 1024**3


# ===========================================================================
# C3 — un fait non confirme vaut None, jamais 0, jamais une valeur devinee
# ===========================================================================


class TestUnconfirmedFactsAreNone:
    def test_no_numeric_field_is_used_as_a_placeholder_zero(self):
        for model in CATALOG.values():
            assert model.download_size_bytes > 0, model.tag
            assert model.memory_footprint_bytes > 0, model.tag
            assert model.parameters_billions is None or model.parameters_billions > 0
            assert model.context_window_tokens is None or model.context_window_tokens > 0

    def test_unconfirmed_quantization_is_none_not_a_plausible_default(self):
        """Q4_K_M est l'usage d'Ollama, mais il n'est pas confirme partout."""
        assert CATALOG["qwen3:8b"].default_quantization is None
        assert CATALOG["deepseek-r1:32b"].default_quantization is None
        assert CATALOG["qwen3:32b"].default_quantization == "Q4_K_M"
        assert CATALOG["gpt-oss:20b"].default_quantization == "MXFP4"

    def test_unconfirmed_context_window_is_none(self):
        assert CATALOG["qwen3:30b-a3b"].context_window_tokens is None
        assert CATALOG["llama3.1:70b"].context_window_tokens is None

    def test_unconfirmed_parameter_count_is_none(self):
        """Le tag porte « 14b », la fiche ne l'enonce pas : on ne recopie pas le tag."""
        assert CATALOG["qwen2.5-coder:14b"].parameters_billions is None

    def test_deduced_licence_is_flagged_as_unconfirmed(self):
        assert CATALOG["qwen2.5-coder:14b"].license_confirmed is False
        assert CATALOG["qwen2.5-coder:7b"].license_confirmed is False
        assert CATALOG["gemma3n:e4b"].license_confirmed is True

    def test_every_entry_carries_its_source_and_date(self):
        for model in CATALOG.values():
            assert model.source_url.startswith("https://ollama.com/library/"), model.tag
            assert model.verified_on == "2026-09-04", model.tag
            assert model.license_name, model.tag


class TestNoQualityScore:
    def test_schema_carries_no_quality_score(self):
        """D-021 : aucune source ne publie de score de suivi de format."""
        for f in fields(LocalModel):
            if f.name == "notes":  # texte libre des reserves de la veille
                continue
            lowered = f.name.lower()
            for banned in ("score", "quality", "note", "rank", "rating"):
                assert banned not in lowered, f"{f.name} ressemble a une note de qualite"


# ===========================================================================
# Validation du schema — cas d'erreur
# ===========================================================================


class TestLocalModelValidation:
    def test_valid_sample_is_accepted(self):
        assert _sample_model().tag == "fake:1b"

    @pytest.mark.parametrize(
        "overrides",
        [
            {"tag": ""},
            {"tag": " qwen3:8b "},
            {"download_size_bytes": 0},
            {"download_size_bytes": -1},
            {"memory_footprint_basis": "devine"},
            {"memory_footprint_low_bytes": 3 * GIB},
            {
                "memory_footprint_bytes": 512 * 1024 * 1024,
                "memory_footprint_low_bytes": 512 * 1024 * 1024,
            },
            {"parameters_billions": 0},
            {"context_window_tokens": 0},
            {"source_url": ""},
            {"source_url": "http://ollama.com/library/fake"},
            {"verified_on": "04-09-2026"},
            {"verified_on": ""},
        ],
    )
    def test_invalid_entries_are_rejected(self, overrides):
        with pytest.raises(ValueError):
            _sample_model(**overrides)

    def test_footprint_below_download_size_is_rejected(self):
        with pytest.raises(ValueError, match="inferieure au poids telecharge"):
            _sample_model(
                download_size_bytes=5 * GIB,
                memory_footprint_bytes=4 * GIB,
                memory_footprint_low_bytes=4 * GIB,
            )


# ===========================================================================
# DEC-006 — classement sur l'empreinte memoire, jamais sur une note
# ===========================================================================


class TestOrdering:
    def test_descending_order_is_monotonic_on_memory_footprint(self):
        ordered = by_memory_footprint()
        footprints = [m.memory_footprint_bytes for m in ordered]
        assert footprints == sorted(footprints, reverse=True)
        assert len(ordered) == len(CATALOG)

    def test_ascending_order_is_the_exact_reverse(self):
        assert by_memory_footprint(descending=False) == tuple(reversed(by_memory_footprint()))

    def test_order_is_stable_across_calls(self):
        assert by_memory_footprint() == by_memory_footprint()

    def test_order_does_not_follow_download_size_when_the_two_diverge(self):
        """gpt-oss:20b pese 14 Go mais demande 16 Go : le tri suit l'empreinte."""
        order = [m.tag for m in by_memory_footprint()]
        assert order.index("gpt-oss:20b") < order.index("qwen3:14b")
        assert CATALOG["gpt-oss:20b"].download_size_bytes < CATALOG["qwen3:32b"].download_size_bytes

    def test_empty_catalog_orders_to_nothing(self):
        assert by_memory_footprint({}) == ()


# ===========================================================================
# C6 — recommend()
# ===========================================================================


class TestRecommendWithoutMeasurement:
    def test_none_yields_an_explicitly_unmeasured_result(self):
        result = recommend(None)
        assert result.measured is False
        assert result.recommended is None
        assert result.maximum is None
        assert result.fits == ()
        assert result.basis is None
        assert result.available_memory_bytes is None
        assert result.margin_bytes is None

    def test_none_never_falls_back_to_a_hardcoded_model(self):
        assert "qwen3:8b" not in recommend(None).reason
        assert "mesure" in recommend(None).reason.lower()

    def test_none_is_unmeasured_even_when_unified(self):
        result = recommend(None, unified=True)
        assert result.measured is False
        assert result.recommended is None
        assert result.unified is True


class TestRecommendOnTheReferenceMachine:
    """Apple M1 Max, 32 Go unifies : la machine de reference du dev."""

    def test_default_recommendation_matches_the_veille(self):
        result = recommend(32 * GIB, unified=True)
        assert result.measured is True
        assert result.recommended is not None
        assert result.recommended.tag == "gpt-oss:20b"
        assert result.basis == FOOTPRINT_OFFICIAL

    def test_maximum_is_offered_apart_from_the_default(self):
        result = recommend(32 * GIB, unified=True)
        assert result.maximum is not None
        assert result.maximum.tag == "qwen3:32b"
        assert result.maximum is not result.recommended

    def test_every_fitting_model_is_listed_heaviest_first(self):
        result = recommend(32 * GIB, unified=True)
        assert result.fits[0].tag == "qwen3:32b"
        assert "llama3.1:70b" not in [m.tag for m in result.fits]
        footprints = [m.memory_footprint_bytes for m in result.fits]
        assert footprints == sorted(footprints, reverse=True)

    def test_the_reserve_is_reported_not_hidden(self):
        result = recommend(32 * GIB, unified=True)
        assert result.reserved_bytes == UNIFIED_MEMORY_RESERVE_BYTES
        assert result.unified is True
        assert result.margin_bytes == 32 * GIB - 16 * GIB

    def test_reason_states_the_nature_of_the_footprint(self):
        assert "officiel" in recommend(32 * GIB, unified=True).reason


class TestRecommendEdgeCases:
    def test_no_reserve_is_applied_outside_unified_memory(self):
        result = recommend(32 * GIB)
        assert result.reserved_bytes == 0
        assert result.recommended is result.maximum
        assert result.recommended.tag == "qwen3:32b"

    def test_zero_memory_fits_nothing_and_recommends_nothing(self):
        result = recommend(0)
        assert result.measured is True
        assert result.fits == ()
        assert result.recommended is None
        assert result.maximum is None
        assert result.basis is None

    def test_memory_below_the_lightest_model_recommends_nothing(self):
        result = recommend(1 * GIB)
        assert result.fits == ()
        assert result.recommended is None
        assert "Aucun modele" in result.reason

    def test_unified_reserve_can_leave_a_maximum_without_a_default(self):
        """14 Gio unifies : qwen3:14b tient, mais pas en laissant 12 Gio au systeme."""
        result = recommend(14 * GIB, unified=True)
        assert result.maximum is not None
        assert result.maximum.tag == "qwen3:14b"
        assert result.recommended is None
        assert result.basis is None
        assert "choix maximal" in result.reason

    def test_estimated_footprint_is_announced_as_such(self):
        result = recommend(12 * GIB)
        assert result.recommended.tag == "qwen3:14b"
        assert result.basis == FOOTPRINT_ESTIMATED
        assert "estimation" in result.reason

    def test_negative_memory_is_rejected(self):
        with pytest.raises(ValueError, match="negative"):
            recommend(-1)

    def test_huge_memory_fits_the_whole_catalog(self):
        result = recommend(512 * GIB)
        assert len(result.fits) == len(CATALOG)
        assert result.recommended.tag == "llama3.1:70b"

    def test_empty_catalog_is_handled_without_crashing(self):
        result = recommend(32 * GIB, catalog={})
        assert result.measured is True
        assert result.fits == ()
        assert result.recommended is None
        assert "Catalogue vide" in result.reason

    def test_injected_catalog_is_used_instead_of_the_default(self):
        catalog = {"fake:1b": _sample_model()}
        result = recommend(32 * GIB, catalog=catalog)
        assert result.recommended.tag == "fake:1b"
        assert [m.tag for m in result.fits] == ["fake:1b"]

    def test_result_reports_the_measurement_it_received(self):
        result = recommend(8 * GIB)
        assert result.available_memory_bytes == 8 * GIB
        assert result.recommended.tag == "qwen3:8b"
        assert result.margin_bytes == 8 * GIB - CATALOG["qwen3:8b"].memory_footprint_bytes

    def test_a_model_exactly_filling_the_memory_still_fits(self):
        """Borne inclusive : 9 Gio disponibles, empreinte de 9 Gio."""
        result = recommend(9 * GIB)
        assert result.recommended.tag == "gemma3n:e4b"
        assert result.margin_bytes == 0
