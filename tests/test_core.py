"""
Tests pour le module core (PromptForge).
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from promptforge.core import PromptForge
from promptforge.security import SecurityContext


class TestPromptForgeInit:
    """Tests pour l'initialisation de PromptForge."""

    def test_init_creates_directories(self, temp_dir):
        """Test que l'init crée les dossiers nécessaires."""
        forge = PromptForge(temp_dir)
        
        assert (Path(temp_dir) / "history").exists()
        assert (Path(temp_dir) / "projects").exists()
        assert (Path(temp_dir) / "promptforge.db").exists()
        
        forge.close()

    def test_init_default_path(self):
        """Test de l'init avec chemin par défaut."""
        # Devrait utiliser le répertoire courant
        forge = PromptForge()
        assert forge.base_path == Path.cwd()
        forge.close()


class TestProjectManagement:
    """Tests pour la gestion des projets."""

    def test_init_project_success(self, forge, sample_config_file):
        """Test de l'initialisation d'un projet."""
        success, message = forge.init_project("test-proj", sample_config_file)
        
        assert success == True
        assert "initialisé" in message or "succès" in message
        
        # Vérifier que le projet existe
        project = forge.db.get_project("test-proj")
        assert project is not None
        assert project.name == "test-proj"

    def test_init_project_file_not_found(self, forge):
        """Test avec fichier de config inexistant."""
        success, message = forge.init_project("test", "/nonexistent/file.md")
        
        assert success == False
        assert "introuvable" in message

    def test_init_project_wrong_extension(self, forge, temp_dir):
        """Test avec mauvaise extension de fichier."""
        txt_file = Path(temp_dir) / "config.txt"
        txt_file.write_text("content")
        
        success, message = forge.init_project("test", str(txt_file))
        
        assert success == False
        assert ".md" in message

    def test_init_project_update_existing(self, forge, sample_config_file, temp_dir):
        """Test de mise à jour d'un projet existant."""
        # Créer le projet
        forge.init_project("update-test", sample_config_file)
        
        # Modifier le fichier de config
        new_config = Path(temp_dir) / "updated.md"
        new_config.write_text("# Updated Config\nNew content")
        
        # Réinitialiser
        success, message = forge.init_project("update-test", str(new_config))
        
        assert success == True
        assert "mis à jour" in message
        
        project = forge.db.get_project("update-test")
        assert "Updated Config" in project.config_content

    def test_use_project_success(self, forge, sample_config_file):
        """Test de l'activation d'un projet."""
        forge.init_project("proj1", sample_config_file)
        
        success, message = forge.use_project("proj1")
        
        assert success == True
        assert forge.get_current_project().name == "proj1"

    def test_use_project_not_found(self, forge):
        """Test d'activation d'un projet inexistant."""
        success, message = forge.use_project("nonexistent")
        
        assert success == False
        assert "introuvable" in message

    def test_list_projects(self, forge, sample_config_file):
        """Test de la liste des projets."""
        assert len(forge.list_projects()) == 0
        
        forge.init_project("alpha", sample_config_file)
        forge.init_project("beta", sample_config_file)
        
        projects = forge.list_projects()
        assert len(projects) == 2

    def test_delete_project_success(self, forge, sample_config_file):
        """Test de suppression d'un projet."""
        forge.init_project("to-delete", sample_config_file)
        
        success, message = forge.delete_project("to-delete")
        
        assert success == True
        assert forge.db.get_project("to-delete") is None

    def test_delete_project_not_found(self, forge):
        """Test de suppression d'un projet inexistant."""
        success, message = forge.delete_project("nonexistent")
        
        assert success == False


class TestFormatPrompt:
    """Tests pour le reformatage de prompts."""

    def test_format_no_active_project(self, forge, mock_ollama_available):
        """Sans projet actif, le reformatage aboutit mais n'ecrit aucun historique.

        Le message « Aucun projet actif » qu'attendait la version precedente
        n'existe plus : le mode « sans projet » est un cas nominal, utilise par
        l'interface web (`project_name=""`) et par le CLI quand aucun projet
        n'est active. Le double est injecte explicitement pour que la
        disponibilite reelle d'Ollama sur la machine ne decide pas du verdict.
        """
        forge.ollama = mock_ollama_available

        result = forge.format_prompt("test prompt")

        assert len(result) == 4
        success, message, formatted, security_ctx = result

        assert success is True
        assert "sans projet" in message.lower()
        assert formatted is not None
        # Aucun historique n'est ecrit hors projet
        assert forge.get_history() == []
        # check_security vaut True par defaut : l'analyse a bien eu lieu
        assert isinstance(security_ctx, SecurityContext)

    def test_format_ollama_unavailable(self, forge, sample_config_file, mock_ollama_unavailable):
        """Ollama indisponible : quadruplet (False, message, None, None).

        Le quatrieme membre vaut None parce que la fonction sort avant l'analyse
        de securite, pas parce que celle-ci serait desactivee.
        """
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        forge.ollama = mock_ollama_unavailable

        result = forge.format_prompt("test prompt")

        assert len(result) == 4
        success, message, formatted, security_ctx = result

        assert success is False
        assert "Ollama" in message
        assert formatted is None
        assert security_ctx is None

    def test_format_with_mock_ollama(self, forge, sample_config_file, mock_ollama_available):
        """Chemin nominal avec projet : quadruplet complet et historique ecrit."""
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        forge.ollama = mock_ollama_available

        result = forge.format_prompt("create user route")

        assert len(result) == 4
        success, file_path, formatted, security_ctx = result

        assert success is True
        assert formatted is not None

        # L'assertion porte sur le contenu utile du prompt reformate, pas sur la
        # syntaxe des delimiteurs. La sortie simulee est du Markdown que
        # `providers.py` reecrit aujourd'hui en XML (« ## Contexte » devient
        # « <context> ») ; DEC-007 prevoit de supprimer cette reecriture. Assertion
        # volontairement neutre vis-a-vis des deux comportements : le choix du
        # format est tranche par R-009, pas ici.
        assert "Stack: Python 3.12, FastAPI, PostgreSQL" in formatted
        assert "/api/v1/users" in formatted

        # Le fichier d'historique existe et son chemin est bien le 2e membre
        assert Path(file_path).exists()

        # La config projet mentionne Python, FastAPI et PostgreSQL : contexte dev
        assert isinstance(security_ctx, SecurityContext)
        assert security_ctx.is_dev is True
        assert "python" in security_ctx.languages

    def test_format_without_security_check(self, forge, sample_config_file, mock_ollama_available):
        """check_security=False : le quatrieme membre vaut None, le reste est intact.

        Contre-partie de `test_format_with_mock_ollama`, qui couvre l'etat
        « SecurityContext present ». Les deux etats du quatrieme membre sont ainsi
        couverts sur le chemin de succes.
        """
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        forge.ollama = mock_ollama_available

        success, file_path, formatted, security_ctx = forge.format_prompt(
            "create user route", check_security=False
        )

        assert success is True
        assert formatted is not None
        assert Path(file_path).exists()
        assert security_ctx is None

    def test_format_with_specific_project(self, forge, sample_config_file, mock_ollama_available):
        """Test avec projet specifique."""
        forge.init_project("proj1", sample_config_file)
        forge.init_project("proj2", sample_config_file)
        forge.use_project("proj1")
        forge.ollama = mock_ollama_available

        # Reformater pour proj2 sans changer le projet actif
        success, _, formatted, security_ctx = forge.format_prompt("test", project_name="proj2")

        assert success is True
        assert formatted is not None
        assert isinstance(security_ctx, SecurityContext)
        # Le projet actif reste proj1
        assert forge.get_current_project().name == "proj1"
        # L'historique est bien impute a proj2 et non au projet actif
        assert len(forge.get_history("proj2")) == 1
        assert forge.get_history("proj1") == []

    def test_format_saves_to_history(self, forge, sample_config_file, mock_ollama_available):
        """Test que le prompt est sauvegardé dans l'historique."""
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        forge.ollama = mock_ollama_available
        
        forge.format_prompt("my test prompt")
        
        history = forge.get_history()
        assert len(history) == 1
        assert history[0].raw_prompt == "my test prompt"


class TestHistoryFile:
    """Tests pour la génération des fichiers d'historique."""

    def test_history_file_content(self, forge, sample_config_file, mock_ollama_available):
        """Test du contenu du fichier d'historique."""
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        forge.ollama = mock_ollama_available
        
        success, file_path, formatted, security_ctx = forge.format_prompt("create api endpoint")

        assert success is True
        assert security_ctx is not None
        
        content = Path(file_path).read_text()
        
        assert "# Prompt History" in content
        assert "Projet" in content
        assert "test" in content
        assert "Prompt Original" in content
        assert "create api endpoint" in content
        assert "Prompt Reformaté" in content

    def test_slugify(self, forge):
        """Test de la création de slugs."""
        assert forge._slugify("Hello World!") == "hello_world"
        assert forge._slugify("Test@#$%^&*()") == "test"
        assert forge._slugify("A" * 50)[:30] == "a" * 30


class TestCheckStatus:
    """Tests pour le statut du système."""

    def test_check_status_structure(self, forge, sample_config_file):
        """Test de la structure du statut."""
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        
        status = forge.check_status()
        
        assert "ollama_available" in status
        assert "ollama_models" in status
        assert "current_model" in status
        assert "active_project" in status
        assert "total_projects" in status
        assert "db_path" in status
        assert "history_path" in status

    def test_check_status_values(self, forge, sample_config_file):
        """Test des valeurs du statut."""
        forge.init_project("status-test", sample_config_file)
        forge.use_project("status-test")
        
        status = forge.check_status()
        
        assert status["active_project"] == "status-test"
        assert status["total_projects"] == 1
        assert status["current_model"] == "llama3.1"


class TestConfigureOllama:
    """Tests pour la configuration d'Ollama."""

    def test_configure_model(self, forge):
        """Test du changement de modèle."""
        forge.configure_ollama(model="mistral")
        
        assert forge.ollama.config.model == "mistral"

    def test_configure_base_url(self, forge):
        """Test du changement d'URL."""
        forge.configure_ollama(base_url="http://custom:8080")
        
        assert forge.ollama.config.base_url == "http://custom:8080"


class TestModelPricingContract:
    """Tests du contrat de ModelPricing et de la table MODEL_PRICING (F-022).

    Placés ici faute de fichier de tests dédié à profiles.py dans le périmètre
    d'agent-backend ; à déplacer vers tests/test_profiles.py si ce fichier est
    créé un jour.
    """

    def test_pricing_table_covers_exactly_target_model(self):
        """Parité stricte : une entrée de tarif par modèle cible, ni plus ni moins."""
        from promptforge.profiles import MODEL_PRICING, TargetModel

        assert set(MODEL_PRICING) == set(TargetModel)

    def test_every_pricing_entry_is_a_model_pricing(self):
        """Chaque valeur est bien une ModelPricing exploitable."""
        from promptforge.profiles import MODEL_PRICING, ModelPricing

        for model, pricing in MODEL_PRICING.items():
            assert isinstance(pricing, ModelPricing), model
            assert pricing.input_price > 0, model
            assert pricing.output_price > 0, model
            assert pricing.context_window > 0, model

    def test_cached_input_is_never_zero(self):
        """Un cache absent vaut None, jamais 0.0 : zéro facturerait un cache gratuit."""
        from promptforge.profiles import MODEL_PRICING

        for model, pricing in MODEL_PRICING.items():
            assert pricing.cached_input is None or pricing.cached_input > 0, model

    def test_sourced_entries_carry_url_and_date(self):
        """Une entrée qui porte une source porte aussi sa date de vérification."""
        from promptforge.profiles import MODEL_PRICING

        for model, pricing in MODEL_PRICING.items():
            if pricing.source_url:
                assert pricing.source_url.startswith("https://"), model
                assert pricing.verified_on, model
                # ISO 8601, forme AAAA-MM-JJ
                assert len(pricing.verified_on) == 10, model
                assert pricing.verified_on[4] == "-" and pricing.verified_on[7] == "-", model

    def test_estimate_cost_without_cache_price_ignores_cached_pct(self):
        """Sans tarif de cache confirmé, la remise n'est pas appliquée."""
        from promptforge.profiles import ModelPricing

        pricing = ModelPricing(input_price=15.0, output_price=120.0, context_window=400_000)

        assert pricing.cached_input is None
        full = pricing.estimate_cost(1_000_000, 0, cached_pct=0)
        discounted = pricing.estimate_cost(1_000_000, 0, cached_pct=1.0)
        assert full == pytest.approx(15.0)
        assert discounted == pytest.approx(full)

    def test_estimate_cost_applies_confirmed_cache_price(self):
        """Avec un tarif de cache confirmé, la remise s'applique."""
        from promptforge.profiles import ModelPricing

        pricing = ModelPricing(
            input_price=1.0,
            output_price=5.0,
            context_window=200_000,
            cached_input=0.1,
        )

        assert pricing.estimate_cost(1_000_000, 0, cached_pct=1.0) == pytest.approx(0.1)
        assert pricing.estimate_cost(1_000_000, 0, cached_pct=0.5) == pytest.approx(0.55)
        assert pricing.estimate_cost(0, 1_000_000) == pytest.approx(5.0)

    def test_gpt_5_pro_has_no_input_cache(self):
        """GPT-5 Pro ne propose pas de cache d'entrée (source officielle 2026-09-03)."""
        from promptforge.profiles import MODEL_PRICING, TargetModel

        assert MODEL_PRICING[TargetModel.GPT_5_PRO].cached_input is None

    def test_corrected_values_match_the_official_sources(self):
        """Les quatre corrections de F-022, vérifiées le 2026-09-03."""
        from promptforge.profiles import MODEL_PRICING, TargetModel

        haiku = MODEL_PRICING[TargetModel.CLAUDE_HAIKU_4_5]
        assert (haiku.input_price, haiku.output_price) == (1.0, 5.0)

        gpt5pro = MODEL_PRICING[TargetModel.GPT_5_PRO]
        assert (gpt5pro.input_price, gpt5pro.output_price) == (15.0, 120.0)
        assert gpt5pro.context_window == 400_000

        assert MODEL_PRICING[TargetModel.GPT_5_1].context_window == 400_000
        assert MODEL_PRICING[TargetModel.CLAUDE_SONNET_4_5].context_window == 200_000

    def test_model_pricing_has_no_dead_member(self):
        """avg_price_per_1k est supprimée : aucun appelant, contrat nettoyé."""
        from promptforge.profiles import ModelPricing

        assert not hasattr(ModelPricing, "avg_price_per_1k")
