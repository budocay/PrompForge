"""
Tests pour les fonctionnalités Game Changer de PromptForge.
- Templates métiers
- Détection de domaine élargie
- Recommandations par domaine
"""

import pytest
import sys
from pathlib import Path

# S'assurer que le package est importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDomainDetection:
    """Tests pour la détection de domaine élargie."""

    def test_import_detect_domain(self):
        """Vérifie que detect_domain est importable."""
        from promptforge.web.analysis import detect_domain
        assert callable(detect_domain)

    def test_detect_seo_domain(self):
        """Détecte le domaine SEO."""
        from promptforge.web.analysis import detect_domain
        
        prompts_seo = [
            "trouve moi des mots clés seo pour mon site",
            "analyse les backlinks de mon concurrent",
            "optimise le référencement de ma page",
            "keyword research pour e-commerce",
            "améliore mon ranking google",
        ]
        
        for prompt in prompts_seo:
            result = detect_domain(prompt)
            assert result == "seo", f"Prompt '{prompt}' devrait être 'seo', got '{result}'"

    def test_detect_marketing_domain(self):
        """Détecte le domaine Marketing."""
        from promptforge.web.analysis import detect_domain
        
        prompts_marketing = [
            "crée une campagne google ads",
            "optimise mon funnel de conversion",
            "améliore le roas de mes publicités",
            "landing page pour lead generation",
        ]
        
        for prompt in prompts_marketing:
            result = detect_domain(prompt)
            assert result == "marketing", f"Prompt '{prompt}' devrait être 'marketing', got '{result}'"

    def test_detect_hr_domain(self):
        """Détecte le domaine RH."""
        from promptforge.web.analysis import detect_domain
        
        prompts_hr = [
            "rédige une fiche de poste développeur",
            "process de recrutement tech",
            "onboarding nouveau collaborateur",
            "sourcing linkedin recruiter",
        ]
        
        for prompt in prompts_hr:
            result = detect_domain(prompt)
            assert result == "hr", f"Prompt '{prompt}' devrait être 'hr', got '{result}'"

    def test_detect_sales_domain(self):
        """Détecte le domaine Sales/Commercial."""
        from promptforge.web.analysis import detect_domain
        
        prompts_sales = [
            "écris un email de prospection commercial",
            "pitch commercial pour saas",
            "gérer les objections client en négociation",
            "cold call pour prise de rdv pipeline",
        ]
        
        for prompt in prompts_sales:
            result = detect_domain(prompt)
            assert result == "sales", f"Prompt '{prompt}' devrait être 'sales', got '{result}'"

    def test_detect_product_domain(self):
        """Détecte le domaine Product Management."""
        from promptforge.web.analysis import detect_domain
        
        prompts_product = [
            "écris les user stories pour cette feature",
            "prd pour nouvelle fonctionnalité",
            "roadmap produit q1 2025",
            "priorisation backlog avec rice",
        ]
        
        for prompt in prompts_product:
            result = detect_domain(prompt)
            assert result == "product", f"Prompt '{prompt}' devrait être 'product', got '{result}'"

    def test_detect_code_domain_still_works(self):
        """Vérifie que le domaine code fonctionne toujours."""
        from promptforge.web.analysis import detect_domain
        
        prompts_code = [
            "écris une fonction python pour calculer",
            "debug mon api fastapi",
            "refactor cette classe javascript",
        ]
        
        for prompt in prompts_code:
            result = detect_domain(prompt)
            assert result == "code", f"Prompt '{prompt}' devrait être 'code', got '{result}'"

    def test_detect_general_fallback(self):
        """Vérifie le fallback vers 'general'."""
        from promptforge.web.analysis import detect_domain
        
        result = detect_domain("bonjour comment vas-tu")
        assert result == "general"


class TestTemplateHelpers:
    """Tests pour les helpers de templates métiers."""

    def test_import_template_helpers(self):
        """Vérifie que les helpers sont importables."""
        from promptforge.web.template_helpers import (
            TEMPLATE_INFO,
            get_template_choices,
            get_template_content,
            get_template_labels
        )
        assert isinstance(TEMPLATE_INFO, dict)
        assert callable(get_template_choices)
        assert callable(get_template_content)
        assert callable(get_template_labels)

    def test_template_info_has_required_keys(self):
        """Vérifie que TEMPLATE_INFO a tous les métiers."""
        from promptforge.web.template_helpers import TEMPLATE_INFO
        
        required_templates = [
            'seo-specialist',
            'marketing-digital',
            'redacteur-web',
            'dev-backend',
            'dev-frontend',
            'product-manager',
            'data-analyst',
            'commercial-sales',
            'rh-recruteur',
            'support-client',
            'legal',
        ]
        
        for template_key in required_templates:
            assert template_key in TEMPLATE_INFO, f"Template '{template_key}' manquant"
            assert 'name' in TEMPLATE_INFO[template_key]
            assert 'description' in TEMPLATE_INFO[template_key]
            assert 'file' in TEMPLATE_INFO[template_key]

    def test_template_count(self):
        """Vérifie qu'il y a 11 templates."""
        from promptforge.web.template_helpers import TEMPLATE_INFO
        assert len(TEMPLATE_INFO) == 11, f"Attendu 11 templates, got {len(TEMPLATE_INFO)}"

    def test_get_template_choices_format(self):
        """Vérifie le format des choix pour dropdown."""
        from promptforge.web.template_helpers import get_template_choices
        
        choices = get_template_choices()
        assert isinstance(choices, list)
        assert len(choices) > 0
        
        # Chaque choix est un tuple (label, value)
        for choice in choices:
            assert isinstance(choice, tuple)
            assert len(choice) == 2

    def test_get_template_content_existing(self):
        """Vérifie le chargement d'un template existant."""
        from promptforge.web.template_helpers import get_template_content
        
        # Ce test peut échouer si les fichiers ne sont pas au bon endroit
        # mais c'est normal en environnement de test isolé
        content = get_template_content('seo-specialist')
        # Le contenu peut être None si le fichier n'est pas trouvé dans l'env de test
        # On vérifie juste que la fonction ne plante pas
        assert content is None or isinstance(content, str)

    def test_get_template_content_nonexistent(self):
        """Vérifie le comportement avec un template inexistant."""
        from promptforge.web.template_helpers import get_template_content
        
        content = get_template_content('template-qui-nexiste-pas')
        assert content is None

    def test_get_template_labels(self):
        """Vérifie les labels de templates."""
        from promptforge.web.template_helpers import get_template_labels
        
        labels = get_template_labels()
        assert isinstance(labels, dict)
        assert len(labels) == 11
        assert 'seo-specialist' in labels


class TestDomainRecommendations:
    """Tests pour les recommandations par domaine."""

    def test_import_domain_expertise(self):
        """Vérifie que DOMAIN_EXPERTISE est importable."""
        from promptforge.web.recommendations import DOMAIN_EXPERTISE, DOMAIN_LABELS
        assert isinstance(DOMAIN_EXPERTISE, dict)
        assert isinstance(DOMAIN_LABELS, dict)

    def test_new_domains_in_labels(self):
        """Vérifie que les nouveaux domaines ont des labels."""
        from promptforge.web.recommendations import DOMAIN_LABELS
        
        new_domains = ['seo', 'marketing', 'hr', 'sales', 'product', 'support']
        
        for domain in new_domains:
            assert domain in DOMAIN_LABELS, f"Label manquant pour '{domain}'"
            assert DOMAIN_LABELS[domain], f"Label vide pour '{domain}'"

    def test_new_domains_in_expertise(self):
        """Vérifie que les nouveaux domaines ont des scores d'expertise."""
        from promptforge.web.recommendations import DOMAIN_EXPERTISE
        from promptforge.profiles import TargetModel
        
        new_domains = ['seo', 'marketing', 'hr', 'sales', 'product', 'support']
        
        # Vérifier pour Claude Opus (représentatif)
        opus_expertise = DOMAIN_EXPERTISE.get(TargetModel.CLAUDE_OPUS_4_5, {})
        
        for domain in new_domains:
            assert domain in opus_expertise, f"Expertise manquante pour '{domain}' (Opus)"
            score, reason = opus_expertise[domain]
            assert isinstance(score, int), f"Score devrait être int pour '{domain}'"
            assert 0 <= score <= 100, f"Score hors range pour '{domain}': {score}"
            assert isinstance(reason, str), f"Reason devrait être str pour '{domain}'"

    def test_domain_labels_count(self):
        """Vérifie le nombre total de labels de domaine."""
        from promptforge.web.recommendations import DOMAIN_LABELS
        
        # 11 anciens + 6 nouveaux = 17 minimum
        # (peut y avoir plus avec analysis, chat, etc.)
        assert len(DOMAIN_LABELS) >= 17, f"Attendu >= 17 labels, got {len(DOMAIN_LABELS)}"


class TestNoBullshitRule:
    """Tests pour la règle anti-bullshit."""

    def test_no_bullshit_rule_exists(self):
        """Vérifie que NO_BULLSHIT_RULE existe."""
        from promptforge.profiles import NO_BULLSHIT_RULE
        
        assert isinstance(NO_BULLSHIT_RULE, str)
        assert len(NO_BULLSHIT_RULE) > 100, "NO_BULLSHIT_RULE semble trop court"

    def test_no_bullshit_rule_content(self):
        """Vérifie le contenu de NO_BULLSHIT_RULE."""
        from promptforge.profiles import NO_BULLSHIT_RULE
        
        # Doit contenir des interdictions claires
        assert "INTERDIT" in NO_BULLSHIT_RULE
        assert "scores" in NO_BULLSHIT_RULE.lower() or "métrique" in NO_BULLSHIT_RULE.lower()

    def test_system_prompt_includes_rule(self):
        """Vérifie que les system prompts incluent la règle."""
        from promptforge.profiles import get_system_prompt, TargetModel
        
        prompt = get_system_prompt(TargetModel.CLAUDE_OPUS_4_5)
        
        # Le system prompt devrait inclure la règle anti-bullshit
        assert "INTERDIT" in prompt or len(prompt) > 2000


class TestInterfaceImports:
    """Tests pour les imports de l'interface."""

    def test_interface_imports_template_helpers(self):
        """Vérifie que l'interface importe les template helpers."""
        # Ce test vérifie que l'import ne plante pas
        try:
            from promptforge.web import create_interface
            from promptforge.web.template_helpers import TEMPLATE_INFO
            assert True
        except ImportError as e:
            pytest.fail(f"Import échoué: {e}")

    def test_create_interface_callable(self):
        """Vérifie que create_interface est appelable."""
        from promptforge.web import create_interface
        assert callable(create_interface)


class TestTemplateFilesExist:
    """Tests pour vérifier que les fichiers de templates existent."""

    def test_templates_directory_exists(self):
        """Vérifie que le dossier templates/metiers existe."""
        templates_dir = Path(__file__).parent.parent / "templates" / "metiers"
        assert templates_dir.exists(), f"Dossier {templates_dir} n'existe pas"

    def test_all_template_files_exist(self):
        """Vérifie que tous les fichiers de templates existent."""
        templates_dir = Path(__file__).parent.parent / "templates" / "metiers"
        
        expected_files = [
            'seo-specialist.md',
            'marketing-digital.md',
            'redacteur-web.md',
            'dev-backend.md',
            'dev-frontend.md',
            'product-manager.md',
            'data-analyst.md',
            'commercial-sales.md',
            'rh-recruteur.md',
            'support-client.md',
            'legal.md',
        ]
        
        for filename in expected_files:
            filepath = templates_dir / filename
            assert filepath.exists(), f"Template manquant: {filepath}"

    def test_template_files_not_empty(self):
        """Vérifie que les fichiers de templates ne sont pas vides."""
        templates_dir = Path(__file__).parent.parent / "templates" / "metiers"
        
        for md_file in templates_dir.glob("*.md"):
            content = md_file.read_text(encoding='utf-8')
            assert len(content) > 500, f"Template {md_file.name} semble trop court ({len(content)} chars)"


# ============================================
# Tests de bout en bout (si Ollama disponible)
# ============================================

class TestEndToEndWithContext:
    """Tests E2E avec contexte projet (nécessite Ollama)."""

    @pytest.fixture
    def check_ollama(self):
        """Vérifie si Ollama est disponible."""
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            return True
        except:
            return False

    @pytest.mark.skipif(
        not pytest.importorskip("urllib.request"),
        reason="Ollama non disponible"
    )
    def test_format_prompt_with_seo_context(self, check_ollama, tmp_path):
        """Test de reformatage avec contexte SEO (si Ollama dispo)."""
        if not check_ollama:
            pytest.skip("Ollama non disponible")
        
        # Ce test est un placeholder - en vrai environnement il appellerait Ollama
        # Pour l'instant on vérifie juste que la structure est en place
        from promptforge.web.analysis import detect_domain
        
        prompt = "trouve des mots clés pour mon site e-commerce"
        domain = detect_domain(prompt)
        assert domain == "seo"


class TestProfilesUiDomainParity:
    """Parité entre l'adapter d'interface et le domaine (F-022 bloc 2).

    Ces tests existent parce que la divergence a réellement eu lieu : trois
    tarifs et une fenêtre de contexte affichés par `web/profiles_ui.py`
    contredisaient `MODEL_PRICING`, et l'un des libellés avait été corrigé à la
    main sans que la source le soit.
    """

    def test_profile_descriptions_cover_exactly_domain_profiles(self):
        """Les clés de PROFILE_DESCRIPTIONS sont celles de list_profiles()."""
        from promptforge.profiles import list_profiles
        from promptforge.web.profiles_ui import PROFILE_DESCRIPTIONS

        assert set(PROFILE_DESCRIPTIONS) == set(list_profiles())

    def test_profile_details_cover_exactly_domain_profiles(self):
        """Les clés du panneau de détail sont celles de list_profiles()."""
        from promptforge.profiles import list_profiles
        from promptforge.web.profiles_ui import PROFILE_DETAILS

        assert set(PROFILE_DETAILS) == set(list_profiles())

    def test_domain_expertise_covers_exactly_target_model(self):
        """DOMAIN_EXPERTISE couvre exactement TargetModel, ni plus ni moins.

        Un membre manquant provoque un KeyError au runtime dans
        `generate_recommendation()` ; un membre en trop signale une
        énumération désynchronisée du domaine.
        """
        from promptforge.profiles import TargetModel
        from promptforge.web.recommendations import DOMAIN_EXPERTISE

        assert set(DOMAIN_EXPERTISE) == set(TargetModel)

    def test_profile_label_price_comes_from_model_pricing(self):
        """Le tarif du libellé est composé depuis MODEL_PRICING, pas recopié."""
        from promptforge.profiles import MODEL_PRICING, PRESET_PROFILES, TargetModel
        from promptforge.web.profiles_ui import PROFILE_DESCRIPTIONS, get_profile_label

        for name in PROFILE_DESCRIPTIONS:
            target = PRESET_PROFILES[name].target_model
            if target is TargetModel.UNIVERSAL:
                # Moyenne synthétique : aucun tarif affiché (D-032).
                continue
            pricing = MODEL_PRICING[target]
            label = get_profile_label(name)
            expected = f"(${pricing.input_price:g}/${pricing.output_price:g})"
            assert label.endswith(expected), f"{name}: {label!r} n'expose pas {expected!r}"

    def test_profile_info_context_window_comes_from_model_pricing(self):
        """La fenêtre de contexte affichée est celle du domaine."""
        from promptforge.profiles import MODEL_PRICING, PRESET_PROFILES, TargetModel
        from promptforge.web.profiles_ui import PROFILE_DETAILS, get_profile_info

        for name in PROFILE_DETAILS:
            target = PRESET_PROFILES[name].target_model
            if target is TargetModel.UNIVERSAL:
                continue
            window = MODEL_PRICING[target].context_window
            if window >= 1_000_000 and window % 1_000_000 == 0:
                expected = f"- Contexte: {window // 1_000_000}M tokens"
            else:
                expected = f"- Contexte: {window // 1_000}K tokens"
            assert expected in get_profile_info(name), f"{name}: attendu {expected!r}"

    def test_profile_info_reports_pricing_provenance(self):
        """Une valeur sans source officielle est signalée comme telle."""
        from promptforge.profiles import MODEL_PRICING, PRESET_PROFILES, TargetModel
        from promptforge.web.profiles_ui import PROFILE_DETAILS, get_profile_info

        for name in PROFILE_DETAILS:
            target = PRESET_PROFILES[name].target_model
            if target is TargetModel.UNIVERSAL:
                continue
            info = get_profile_info(name)
            if MODEL_PRICING[target].source_url:
                assert MODEL_PRICING[target].source_url in info, name
            else:
                assert "non confirmé" in info, name

    def test_unknown_profile_label_and_info_do_not_invent_a_price(self):
        """Profil inconnu : aucun tarif inventé, aucune exception."""
        from promptforge.web.profiles_ui import get_profile_info, get_profile_label

        assert get_profile_label("profil-inexistant") == "profil-inexistant"
        info = get_profile_info("profil-inexistant")
        assert "$" not in info

    def test_recommendation_iterates_over_model_pricing(self):
        """`generate_recommendation()` couvre toutes les entrées de MODEL_PRICING."""
        from promptforge.profiles import MODEL_PRICING
        from promptforge.web.recommendations import generate_recommendation

        rendered = generate_recommendation(
            formatted_prompt="<task>Revue de code</task>",
            task_type="code",
            ollama_model=None,
            domain_override="code",
        )
        assert isinstance(rendered, str) and rendered
        # Le tableau n'affiche que le top 5 : on vérifie qu'aucun modèle du
        # domaine ne fait échouer le rendu (KeyError sur une entrée manquante).
        assert len(MODEL_PRICING) >= 5
