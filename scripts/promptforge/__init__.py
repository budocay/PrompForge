"""
PromptForge - Reformateur intelligent de prompts avec contexte projet.

Open-source, 100% local avec Ollama.
Cross-platform: Windows, macOS, Linux.
"""

__version__ = "0.1.0"
__author__ = "PromptForge Contributors"

from .core import PromptForge
from .database import Database, Project, PromptHistory
from .providers import OllamaProvider, OllamaConfig

__all__ = [
    "PromptForge",
    "Database",
    "Project", 
    "PromptHistory",
    "OllamaProvider",
    "OllamaConfig"
]
