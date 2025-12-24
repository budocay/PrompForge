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

    def generate(self, prompt: str, system_prompt: str = "", num_ctx: int = 16384) -> Optional[str]:
        """Génère une réponse via Ollama.

        Args:
            prompt: Le prompt à envoyer
            system_prompt: Le system prompt optionnel
            num_ctx: Taille du contexte (défaut: 16384 pour supporter les gros projets)
        """
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Plus déterministe pour le reformatage
                    "top_p": 0.9,
                    "num_ctx": num_ctx  # Utiliser plus de contexte pour les gros prompts
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


import re

def is_markdown_format(text: str) -> bool:
    """
    Détecte si le texte est au format Markdown plutôt que XML.
    """
    # Patterns Markdown typiques
    markdown_patterns = [
        r'^#{1,6}\s+',           # Headers: # ## ### etc.
        r'\*\*[^*]+\*\*',        # Bold: **text**
        r'^\s*[-*]\s+',          # Lists: - item ou * item
        r'^\s*\d+\.\s+',         # Numbered lists: 1. item
        r'^---+$',               # Horizontal rules: ---
        r'```',                  # Code blocks
    ]
    
    # Si on trouve plusieurs patterns Markdown, c'est du Markdown
    markdown_count = 0
    for pattern in markdown_patterns:
        if re.search(pattern, text, re.MULTILINE):
            markdown_count += 1
    
    # Vérifier si des balises XML existent
    has_xml = bool(re.search(r'<\w+>.*?</\w+>', text, re.DOTALL))
    
    # C'est du Markdown si on a 2+ patterns Markdown ET pas de XML
    return markdown_count >= 2 and not has_xml


def convert_markdown_to_xml(text: str, profile_name: Optional[str] = None) -> str:
    """
    Convertit le Markdown généré par un petit modèle en XML structuré.
    
    Cette fonction est un filet de sécurité pour les modèles qui ne suivent pas
    les instructions de format XML.
    """
    # Nettoyer le texte
    text = text.strip()
    
    # Supprimer les blocs de code Markdown
    text = re.sub(r'```\w*\n?', '', text)
    text = re.sub(r'```', '', text)
    
    # Supprimer les lignes de séparation ---
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    
    # Mapping des headers Markdown vers balises XML universelles (v2.0)
    # Balises harmonisées: <task>, <context>, <instructions>, <constraints>, <output_format>
    section_mapping = {
        # Task / Objectif
        'objectif': 'task',
        'objective': 'task',
        'but': 'task',
        'task': 'task',
        'tâche': 'task',
        'principal': 'task',
        'main': 'task',
        'goal': 'task',
        'définition': 'task',
        'definition': 'task',
        
        # Context
        'contexte': 'context',
        'context': 'context',
        'background': 'context',
        'technologies': 'context',
        'stack': 'context',
        'projet': 'context',
        'project': 'context',
        'environnement': 'context',
        'environment': 'context',
        
        # Instructions / Steps
        'instructions': 'instructions',
        'étapes': 'instructions',
        'steps': 'instructions',
        'procedure': 'instructions',
        'procédure': 'instructions',
        'actions': 'instructions',
        'process': 'instructions',
        'workflow': 'instructions',
        
        # Requirements / Specifications
        'specifications': 'requirements',
        'spécifications': 'requirements',
        'requirements': 'requirements',
        'exigences': 'requirements',
        'besoins': 'requirements',
        'needs': 'requirements',
        'features': 'requirements',
        'fonctionnalités': 'requirements',
        
        # Constraints
        'contraintes': 'constraints',
        'constraints': 'constraints',
        'limites': 'constraints',
        'limits': 'constraints',
        'règles': 'constraints',
        'rules': 'constraints',
        'bonnes pratiques': 'constraints',
        'best practices': 'constraints',
        'restrictions': 'constraints',
        
        # Output format
        'format': 'output_format',
        'output': 'output_format',
        'sortie': 'output_format',
        'résultat': 'output_format',
        'result': 'output_format',
        'attendu': 'output_format',
        'expected': 'output_format',
        'livrables': 'output_format',
        'deliverables': 'output_format',
        
        # Thinking (pour GPT-5 Pro)
        'thinking': 'thinking',
        'raisonnement': 'thinking',
        'reasoning': 'thinking',
        'réflexion': 'thinking',
        'analyse': 'thinking',
        'analysis': 'thinking',
        
        # Examples (few-shot)
        'exemples': 'examples',
        'examples': 'examples',
        'exemple': 'examples',
        'example': 'examples',
        
        # Autres
        'fichiers': 'files',
        'files': 'files',
        'ressources': 'resources',
        'resources': 'resources',
    }
    
    # Trouver les sections avec headers Markdown
    sections = {}
    current_section = None
    current_content = []
    
    lines = text.split('\n')
    
    for line in lines:
        # Ignorer les lignes vides de séparation
        if re.match(r'^---+\s*$', line):
            continue
            
        # Détecter les headers Markdown (# ## ### etc.)
        header_match = re.match(r'^#{1,6}\s+\**(.+?)\**\s*$', line)
        
        if header_match:
            # Sauvegarder la section précédente
            if current_section and current_content:
                content = '\n'.join(current_content).strip()
                # Nettoyer les --- restants
                content = re.sub(r'\n---+\s*$', '', content)
                content = re.sub(r'^---+\s*\n', '', content)
                if content:
                    sections[current_section] = content
            
            # Nouvelle section
            header_text = header_match.group(1).lower()
            header_text = re.sub(r'\*+', '', header_text).strip()
            
            # Trouver le tag XML correspondant
            current_section = None
            for key, tag in section_mapping.items():
                if key in header_text:
                    current_section = tag
                    break
            
            # Si pas trouvé, utiliser un tag générique basé sur le header
            if not current_section:
                # Créer un tag à partir du header
                tag_name = re.sub(r'[^a-z0-9]+', '_', header_text)
                tag_name = tag_name.strip('_')
                if tag_name:
                    current_section = tag_name
                else:
                    current_section = 'section'
            
            current_content = []
        else:
            # Nettoyer le contenu
            cleaned_line = line
            # Supprimer le bold Markdown
            cleaned_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned_line)
            # Convertir les tirets de liste
            cleaned_line = re.sub(r'^\s*[-*]\s+', '- ', cleaned_line)
            # Supprimer les backticks inline
            cleaned_line = re.sub(r'`([^`]+)`', r'\1', cleaned_line)
            
            if cleaned_line.strip():
                current_content.append(cleaned_line)
    
    # Sauvegarder la dernière section
    if current_section and current_content:
        content = '\n'.join(current_content).strip()
        content = re.sub(r'\n---+\s*$', '', content)
        content = re.sub(r'^---+\s*\n', '', content)
        if content:
            sections[current_section] = content
    
    # Si pas de sections trouvées, créer une structure minimale
    if not sections:
        # Nettoyer le Markdown
        cleaned = re.sub(r'#{1,6}\s+', '', text)
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'^[-*]\s+', '- ', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^---+\s*$', '', cleaned, flags=re.MULTILINE)
        
        sections = {
            'task': 'Accomplir la tâche demandée par l\'utilisateur.',
            'context': 'Contexte extrait de la demande.',
            'instructions': cleaned.strip(),
            'output_format': 'Réponse structurée et complète.'
        }
    
    # Construire le XML
    xml_parts = []
    
    # Ordre préféré des balises (format universel v2.0)
    preferred_order = [
        'task', 'context', 'thinking', 'instructions', 
        'requirements', 'constraints', 'examples',
        'output_format', 'files', 'resources'
    ]
    
    # D'abord les sections dans l'ordre préféré
    for tag in preferred_order:
        if tag in sections:
            content = sections[tag]
            xml_parts.append(f'<{tag}>\n{content}\n</{tag}>')
    
    # Puis les autres sections
    for tag, content in sections.items():
        if tag not in preferred_order:
            xml_parts.append(f'<{tag}>\n{content}\n</{tag}>')
    
    return '\n\n'.join(xml_parts)


def ensure_xml_format(text: str, profile_name: Optional[str] = None) -> str:
    """
    S'assure que la sortie est au format XML.
    Si du Markdown est détecté, le convertit automatiquement.
    """
    if not text:
        return text
    
    # Si c'est déjà du XML, retourner tel quel
    if not is_markdown_format(text):
        return text
    
    # Convertir le Markdown en XML
    return convert_markdown_to_xml(text, profile_name)


REFORMAT_SYSTEM_PROMPT = """Tu transformes des demandes utilisateur en prompts XML ultra-structurés.

⚠️ CONTEXTE: Outil de DÉVELOPPEMENT LOGICIEL (PromptForge).
Les demandes concernent du code, de la programmation, des projets informatiques.
- "scanner" = analyser du CODE SOURCE (pas d'OCR physique)
- "projet" = projet de DÉVELOPPEMENT (repo git, fichiers)
- "analyse" = analyse de CODE ou d'architecture

RÈGLE ABSOLUE: Ta réponse DOIT être UNIQUEMENT des balises XML.
❌ INTERDIT: #, ##, **, -, ```, Markdown
✅ OBLIGATOIRE: <balise>contenu</balise>

BALISES XML À UTILISER:
<task>          Objectif principal clair
<context>       Informations contextuelles projet/technique
<instructions>  Étapes numérotées (1. 2. 3.)
<constraints>   Limites et règles à respecter
<output_format> Format de sortie attendu

EXEMPLE DE TRANSFORMATION:

Demande: "j'ai besoin d'une page de login"

<task>
Créer une page de connexion sécurisée et responsive pour l'application web.
</task>

<context>
Application web nécessitant un système d'authentification utilisateur.
Page de login comme point d'entrée principal.
</context>

<instructions>
1. Créer le formulaire avec champs email et mot de passe
2. Implémenter la validation côté client
3. Gérer les états de chargement et d'erreur
4. Ajouter la redirection après connexion réussie
5. Styliser de manière responsive (mobile/desktop)
</instructions>

<constraints>
Ne pas stocker le mot de passe en clair
Utiliser HTTPS pour la transmission
Protéger contre les attaques CSRF
Messages d'erreur non révélateurs
</constraints>

<output_format>
Composant React/Vue avec:
- Formulaire validé
- Gestion d'erreurs
- Styles responsives
- Tests unitaires
</output_format>

RAPPEL:
- Commence DIRECTEMENT par <task>
- PAS de texte avant ou après le XML
- MÊME LANGUE que l'utilisateur"""


def format_prompt_with_ollama(
    raw_prompt: str, 
    project_context: str,
    provider: Optional[OllamaProvider] = None,
    profile_name: Optional[str] = None,
    return_conversion_info: bool = False
) -> Optional[str]:
    """
    Reformate un prompt en utilisant Ollama.
    
    Args:
        raw_prompt: Le prompt brut de l'utilisateur
        project_context: Le contenu du fichier de configuration projet
        provider: Instance OllamaProvider (créée si non fournie)
        profile_name: Nom du profil de reformatage (claude_technique, chatgpt_standard, etc.)
        return_conversion_info: Si True, retourne un tuple (result, was_converted_from_markdown)
    
    Returns:
        Le prompt reformaté ou None en cas d'erreur
        Si return_conversion_info=True: tuple (prompt, was_converted)
    """
    if provider is None:
        provider = OllamaProvider()
    
    if not provider.is_available():
        return (None, False) if return_conversion_info else None
    
    # Utiliser un profil si spécifié
    if profile_name:
        from .profiles import get_profile, build_reformat_prompt
        profile = get_profile(profile_name)
        system_prompt, full_prompt = build_reformat_prompt(
            raw_prompt, project_context, profile
        )
    else:
        # Fallback simple
        system_prompt = REFORMAT_SYSTEM_PROMPT
        if project_context.strip():
            full_prompt = f"""CONTEXTE PROJET:
{project_context}

DEMANDE À REFORMATER:
{raw_prompt}

Réécris cette demande en prompt structuré."""
        else:
            full_prompt = f"""DEMANDE À REFORMATER:
{raw_prompt}

Réécris cette demande en prompt structuré."""

    # Générer avec Ollama
    result = provider.generate(full_prompt, system_prompt)
    
    # POST-TRAITEMENT: Convertir Markdown -> XML si nécessaire
    # Les petits modèles (8B et moins) génèrent souvent du Markdown
    # même quand on leur demande du XML
    was_converted = False
    if result:
        if is_markdown_format(result):
            result = convert_markdown_to_xml(result, profile_name)
            was_converted = True
    
    if return_conversion_info:
        return (result, was_converted)
    return result
