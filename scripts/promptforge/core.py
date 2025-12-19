"""
Core de PromptForge - Logique principale de reformatage des prompts.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import re

from .database import Database, Project
from .providers import OllamaProvider, OllamaConfig, format_prompt_with_ollama


class PromptForge:
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialise PromptForge.
        
        Args:
            base_path: Chemin de base pour la DB et l'historique.
                       Si None, utilise le répertoire courant.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.db_path = self.base_path / "promptforge.db"
        self.history_path = self.base_path / "history"
        self.projects_path = self.base_path / "projects"
        
        # Création des dossiers si nécessaire
        self.history_path.mkdir(exist_ok=True)
        self.projects_path.mkdir(exist_ok=True)
        
        # Initialisation
        self.db = Database(str(self.db_path))
        self.ollama = OllamaProvider()
    
    def configure_ollama(self, model: str = "llama3.1", 
                         base_url: str = "http://localhost:11434") -> bool:
        """Configure le provider Ollama."""
        self.ollama = OllamaProvider(OllamaConfig(
            base_url=base_url,
            model=model
        ))
        return self.ollama.is_available()

    def init_project(self, name: str, config_path: str) -> tuple[bool, str]:
        """
        Initialise un nouveau projet à partir d'un fichier de configuration.
        
        Args:
            name: Nom du projet
            config_path: Chemin vers le fichier .md de configuration
        
        Returns:
            Tuple (succès, message)
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            return False, f"Fichier de configuration introuvable: {config_path}"
        
        if not config_file.suffix.lower() == ".md":
            return False, "Le fichier de configuration doit être un fichier .md"
        
        try:
            config_content = config_file.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Erreur de lecture du fichier: {e}"
        
        # Vérifier si le projet existe déjà
        existing = self.db.get_project(name)
        if existing:
            # Mise à jour du projet existant
            self.db.update_project(name, config_content)
            return True, f"Projet '{name}' mis à jour avec succès"
        
        # Création du nouveau projet
        self.db.add_project(name, str(config_file.absolute()), config_content)
        return True, f"Projet '{name}' initialisé avec succès"

    def use_project(self, name: str) -> tuple[bool, str]:
        """
        Active un projet pour l'utiliser.
        
        Args:
            name: Nom du projet à activer
        
        Returns:
            Tuple (succès, message)
        """
        if self.db.set_active_project(name):
            return True, f"Projet '{name}' activé"
        return False, f"Projet '{name}' introuvable"

    def get_current_project(self) -> Optional[Project]:
        """Retourne le projet actuellement actif."""
        return self.db.get_active_project()

    def list_projects(self) -> list[Project]:
        """Liste tous les projets disponibles."""
        return self.db.list_projects()

    def delete_project(self, name: str) -> tuple[bool, str]:
        """Supprime un projet."""
        if self.db.delete_project(name):
            return True, f"Projet '{name}' supprimé"
        return False, f"Projet '{name}' introuvable"

    def format_prompt(self, raw_prompt: str, 
                      project_name: Optional[str] = None,
                      profile_name: Optional[str] = None) -> tuple[bool, str, Optional[str]]:
        """
        Reformate un prompt en utilisant le contexte projet.
        
        Args:
            raw_prompt: Le prompt brut à reformater
            project_name: Nom du projet (utilise le projet actif si None)
            profile_name: Profil de reformatage (claude_technique, chatgpt_standard, etc.)
        
        Returns:
            Tuple (succès, message/erreur, prompt_reformaté)
        """
        # Récupération du projet
        if project_name:
            project = self.db.get_project(project_name)
        else:
            project = self.db.get_active_project()
        
        if not project:
            return False, "Aucun projet actif. Utilisez 'use <projet>' ou spécifiez --project", None
        
        # Vérification Ollama
        if not self.ollama.is_available():
            return False, "Ollama n'est pas disponible. Vérifiez qu'il est lancé.", None
        
        # Reformatage via Ollama
        formatted = format_prompt_with_ollama(
            raw_prompt=raw_prompt,
            project_context=project.config_content,
            provider=self.ollama,
            profile_name=profile_name
        )
        
        if not formatted:
            return False, "Erreur lors du reformatage avec Ollama", None
        
        # Sauvegarde dans l'historique
        file_path = self._save_history(project, raw_prompt, formatted)
        
        # Enregistrement en base
        self.db.add_history(
            project_id=project.id,
            raw_prompt=raw_prompt,
            formatted_prompt=formatted,
            file_path=str(file_path)
        )
        
        return True, str(file_path), formatted

    def _save_history(self, project: Project, raw_prompt: str, 
                      formatted_prompt: str) -> Path:
        """Sauvegarde le prompt dans un fichier d'historique."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        
        # Création d'un nom de fichier basé sur le prompt
        slug = self._slugify(raw_prompt[:50])
        filename = f"{timestamp}_{project.name}_{slug}.md"
        
        file_path = self.history_path / filename
        
        content = f"""# Prompt History - {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Projet
**Nom:** {project.name}

---

## Prompt Original (brut)
```
{raw_prompt}
```

---

## Prompt Reformaté
{formatted_prompt}

---

## Contexte Projet Utilisé
<details>
<summary>Voir le contexte</summary>

{project.config_content}

</details>
"""
        
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _slugify(self, text: str) -> str:
        """Convertit un texte en slug pour nom de fichier."""
        # Supprime les caractères spéciaux
        text = re.sub(r'[^\w\s-]', '', text.lower())
        # Remplace les espaces par des underscores
        text = re.sub(r'[\s]+', '_', text)
        return text[:30].strip('_')

    def get_history(self, project_name: Optional[str] = None, 
                    limit: int = 20) -> list:
        """Récupère l'historique des prompts."""
        return self.db.get_history(project_name, limit)

    def check_status(self) -> dict:
        """Retourne le statut du système."""
        active_project = self.get_current_project()
        ollama_ok = self.ollama.is_available()
        models = self.ollama.list_models() if ollama_ok else []
        
        return {
            "ollama_available": ollama_ok,
            "ollama_models": models,
            "current_model": self.ollama.config.model,
            "active_project": active_project.name if active_project else None,
            "total_projects": len(self.list_projects()),
            "db_path": str(self.db_path),
            "history_path": str(self.history_path)
        }

    def close(self):
        """Ferme proprement les ressources."""
        self.db.close()
