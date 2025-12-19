"""
Provider Ollama pour le reformatage intelligent des prompts.
Gère la communication avec Ollama en local.
"""

import subprocess
import json
import os
from typing import Optional
from dataclasses import dataclass, field
import urllib.request
import urllib.error


def get_default_ollama_url() -> str:
    """Récupère l'URL Ollama depuis l'environnement ou détecte automatiquement."""
    if "OLLAMA_HOST" in os.environ:
        return os.environ["OLLAMA_HOST"]
    
    # Détecter WSL
    try:
        with open("/proc/version", "r") as f:
            if "microsoft" in f.read().lower():
                return "http://host.docker.internal:11434"
    except:
        pass
    
    return "http://localhost:11434"


@dataclass
class OllamaConfig:
    base_url: str = field(default_factory=get_default_ollama_url)
    model: str = "llama3.1"
    timeout: int = 120


class OllamaProvider:
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
    
    def is_available(self) -> bool:
        """Vérifie si Ollama est disponible et répond."""
        try:
            req = urllib.request.Request(
                f"{self.config.base_url}/api/tags",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return False

    def list_models(self) -> list[str]:
        """Liste les modèles disponibles dans Ollama."""
        try:
            req = urllib.request.Request(
                f"{self.config.base_url}/api/tags",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                return [model["name"] for model in data.get("models", [])]
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            return []

    def generate(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Génère une réponse via Ollama."""
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Plus déterministe pour le reformatage
                    "top_p": 0.9
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.config.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode())
                return result.get("response")
                
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            print(f"Erreur Ollama: {e}")
            return None

    def pull_model(self, model: str) -> bool:
        """Télécharge un modèle si nécessaire."""
        try:
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max pour le téléchargement
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


REFORMAT_SYSTEM_PROMPT = """Tu es un expert en ingénierie de prompts. Ta mission est de reformater et améliorer les prompts utilisateur pour les rendre plus précis et efficaces.

Tu reçois:
1. Le contexte d'un projet (stack technique, structure, conventions)
2. Un prompt brut de l'utilisateur

Tu dois:
1. Analyser l'intention de l'utilisateur
2. Restructurer le prompt de manière claire et précise
3. Intégrer le contexte projet pertinent
4. Ajouter des spécifications implicites utiles

Format de sortie attendu:
- Section "Contexte" avec les éléments projet pertinents
- Section "Demande" reformulée clairement
- Section "Spécifications" avec les détails techniques attendus
- Section "Contraintes" si applicable

Réponds UNIQUEMENT avec le prompt reformaté, sans explications supplémentaires.
Réponds dans la même langue que le prompt original."""


def format_prompt_with_ollama(
    raw_prompt: str, 
    project_context: str,
    provider: Optional[OllamaProvider] = None,
    profile_name: Optional[str] = None
) -> Optional[str]:
    """
    Reformate un prompt en utilisant Ollama.
    
    Args:
        raw_prompt: Le prompt brut de l'utilisateur
        project_context: Le contenu du fichier de configuration projet
        provider: Instance OllamaProvider (créée si non fournie)
        profile_name: Nom du profil de reformatage (claude_technique, chatgpt_standard, etc.)
    
    Returns:
        Le prompt reformaté ou None en cas d'erreur
    """
    if provider is None:
        provider = OllamaProvider()
    
    if not provider.is_available():
        return None
    
    # Utiliser un profil si spécifié
    if profile_name:
        from .profiles import get_profile, build_reformat_prompt
        profile = get_profile(profile_name)
        system_prompt, full_prompt = build_reformat_prompt(
            raw_prompt, project_context, profile
        )
    else:
        # Fallback sur l'ancien comportement
        system_prompt = REFORMAT_SYSTEM_PROMPT
        full_prompt = f"""## Contexte du projet
{project_context}

## Prompt à reformater
{raw_prompt}

## Ta tâche
Reformate ce prompt en intégrant le contexte projet pour le rendre optimal."""

    return provider.generate(full_prompt, system_prompt)
