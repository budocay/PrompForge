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
from .tokens import estimate_tokens, count_tokens_detailed, get_token_info
from .logging_config import init_logging, get_logger
from .scanner import ProjectScanner, ScanResult, scan_directory
from .security import (
    detect_dev_context,
    check_cve_osv,
    check_package_cve,
    get_security_guidelines,
    enrich_prompt_with_security,
    CVEInfo,
    SecurityContext,
)

__all__ = [
    "PromptForge",
    "Database",
    "Project",
    "PromptHistory",
    "OllamaProvider",
    "OllamaConfig",
    "estimate_tokens",
    "count_tokens_detailed",
    "get_token_info",
    "init_logging",
    "get_logger",
    "ProjectScanner",
    "ScanResult",
    "scan_directory",
    # Security
    "detect_dev_context",
    "check_cve_osv",
    "check_package_cve",
    "get_security_guidelines",
    "enrich_prompt_with_security",
    "CVEInfo",
    "SecurityContext",
]
