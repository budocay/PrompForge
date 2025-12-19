"""
Tests pour le module core (PromptForge).
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from promptforge.core import PromptForge


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

    def test_format_no_active_project(self, forge):
        """Test sans projet actif."""
        success, message, formatted = forge.format_prompt("test prompt")
        
        assert success == False
        assert "Aucun projet actif" in message
        assert formatted is None

    def test_format_ollama_unavailable(self, forge, sample_config_file):
        """Test avec Ollama non disponible."""
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        
        # Ollama n'est pas lancé dans les tests
        success, message, formatted = forge.format_prompt("test prompt")
        
        assert success == False
        assert "Ollama" in message

    def test_format_with_mock_ollama(self, forge, sample_config_file, mock_ollama_available):
        """Test avec Ollama simulé."""
        forge.init_project("test", sample_config_file)
        forge.use_project("test")
        forge.ollama = mock_ollama_available
        
        success, file_path, formatted = forge.format_prompt("create user route")
        
        assert success == True
        assert formatted is not None
        assert "Contexte" in formatted
        
        # Vérifier que le fichier d'historique existe
        assert Path(file_path).exists()

    def test_format_with_specific_project(self, forge, sample_config_file, mock_ollama_available):
        """Test avec projet spécifique."""
        forge.init_project("proj1", sample_config_file)
        forge.init_project("proj2", sample_config_file)
        forge.use_project("proj1")
        forge.ollama = mock_ollama_available
        
        # Reformater pour proj2 sans changer le projet actif
        success, _, formatted = forge.format_prompt("test", project_name="proj2")
        
        assert success == True
        # Le projet actif reste proj1
        assert forge.get_current_project().name == "proj1"

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
        
        success, file_path, formatted = forge.format_prompt("create api endpoint")
        
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
