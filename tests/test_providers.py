"""
Tests pour le module providers (Ollama).
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from urllib.error import URLError

from promptforge.providers import (
    OllamaProvider, 
    OllamaConfig, 
    format_prompt_with_ollama,
    REFORMAT_SYSTEM_PROMPT
)


class TestOllamaConfig:
    """Tests pour OllamaConfig."""

    def test_default_values(self):
        """Test des valeurs par défaut."""
        config = OllamaConfig()
        
        # L'URL peut varier selon l'environnement (WSL vs normal)
        assert "11434" in config.base_url
        assert config.model == "llama3.1"
        assert config.timeout == 120

    def test_custom_values(self):
        """Test des valeurs personnalisées."""
        config = OllamaConfig(
            base_url="http://custom:8080",
            model="mistral",
            timeout=60
        )
        
        assert config.base_url == "http://custom:8080"
        assert config.model == "mistral"
        assert config.timeout == 60


class TestOllamaProvider:
    """Tests pour OllamaProvider."""

    def test_init_default_config(self):
        """Test de l'initialisation avec config par défaut."""
        provider = OllamaProvider()
        
        assert provider.config.base_url == "http://localhost:11434"
        assert provider.config.model == "llama3.1"

    def test_init_custom_config(self):
        """Test de l'initialisation avec config personnalisée."""
        config = OllamaConfig(model="mistral")
        provider = OllamaProvider(config)
        
        assert provider.config.model == "mistral"

    @patch('urllib.request.urlopen')
    def test_is_available_success(self, mock_urlopen):
        """Test de disponibilité quand Ollama répond."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        provider = OllamaProvider()
        assert provider.is_available() == True

    @patch('urllib.request.urlopen')
    def test_is_available_failure(self, mock_urlopen):
        """Test de disponibilité quand Ollama ne répond pas."""
        mock_urlopen.side_effect = URLError("Connection refused")
        
        provider = OllamaProvider()
        assert provider.is_available() == False

    @patch('urllib.request.urlopen')
    def test_list_models_success(self, mock_urlopen):
        """Test de la liste des modèles."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "llama3.1:latest"},
                {"name": "mistral:latest"}
            ]
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        provider = OllamaProvider()
        models = provider.list_models()
        
        assert len(models) == 2
        assert "llama3.1:latest" in models
        assert "mistral:latest" in models

    @patch('urllib.request.urlopen')
    def test_list_models_failure(self, mock_urlopen):
        """Test de la liste des modèles en cas d'erreur."""
        mock_urlopen.side_effect = URLError("Connection refused")
        
        provider = OllamaProvider()
        models = provider.list_models()
        
        assert models == []

    @patch('urllib.request.urlopen')
    def test_generate_success(self, mock_urlopen):
        """Test de génération de texte."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "Generated text response"
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        provider = OllamaProvider()
        result = provider.generate("Test prompt", "System prompt")
        
        assert result == "Generated text response"
        
        # Vérifier l'appel
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.full_url == "http://localhost:11434/api/generate"
        
        # Vérifier le payload
        payload = json.loads(request.data.decode())
        assert payload["model"] == "llama3.1"
        assert payload["prompt"] == "Test prompt"
        assert payload["system"] == "System prompt"

    @patch('urllib.request.urlopen')
    def test_generate_failure(self, mock_urlopen):
        """Test de génération en cas d'erreur."""
        mock_urlopen.side_effect = URLError("Connection refused")
        
        provider = OllamaProvider()
        result = provider.generate("Test prompt")
        
        assert result is None


class TestFormatPromptWithOllama:
    """Tests pour la fonction format_prompt_with_ollama."""

    def test_format_with_available_provider(self, mock_ollama_available, sample_config_content):
        """Test du formatage avec provider disponible."""
        result = format_prompt_with_ollama(
            raw_prompt="create user route",
            project_context=sample_config_content,
            provider=mock_ollama_available
        )
        
        assert result is not None
        assert "Contexte" in result

    def test_format_with_unavailable_provider(self, mock_ollama_unavailable, sample_config_content):
        """Test du formatage avec provider indisponible."""
        result = format_prompt_with_ollama(
            raw_prompt="create user route",
            project_context=sample_config_content,
            provider=mock_ollama_unavailable
        )
        
        assert result is None

    def test_system_prompt_exists(self):
        """Vérifie que le system prompt est bien défini."""
        assert REFORMAT_SYSTEM_PROMPT is not None
        assert len(REFORMAT_SYSTEM_PROMPT) > 100
        # Vérifie que le prompt contient des mots-clés attendus
        prompt_lower = REFORMAT_SYSTEM_PROMPT.lower()
        assert "xml" in prompt_lower or "prompt" in prompt_lower or "réécris" in prompt_lower
