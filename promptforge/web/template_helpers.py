"""
Helpers pour la gestion des templates métier dans l'UI.
"""

from pathlib import Path
from typing import Optional
import os

# Mapping des templates avec leurs descriptions
TEMPLATE_INFO = {
    'seo-specialist': {
        'name': '🔍 SEO Specialist',
        'description': 'Recherche de mots-clés, audits, optimisation',
        'file': 'seo-specialist.md'
    },
    'marketing-digital': {
        'name': '📢 Marketing Digital',
        'description': 'Campagnes, ads, copywriting, growth',
        'file': 'marketing-digital.md'
    },
    'redacteur-web': {
        'name': '✍️ Rédacteur Web',
        'description': 'Articles, landing pages, contenu SEO',
        'file': 'redacteur-web.md'
    },
    'dev-backend': {
        'name': '⚙️ Dev Backend',
        'description': 'API, bases de données, architecture',
        'file': 'dev-backend.md'
    },
    'dev-frontend': {
        'name': '🎨 Dev Frontend',
        'description': 'React, UI/UX, composants',
        'file': 'dev-frontend.md'
    },
    'product-manager': {
        'name': '🎯 Product Manager',
        'description': 'PRD, specs, roadmap, user stories',
        'file': 'product-manager.md'
    },
    'data-analyst': {
        'name': '📊 Data Analyst',
        'description': 'SQL, dashboards, analytics',
        'file': 'data-analyst.md'
    },
    'commercial-sales': {
        'name': '💼 Commercial / Sales',
        'description': 'Prospection, pitch, négociation',
        'file': 'commercial-sales.md'
    },
    'rh-recruteur': {
        'name': '👥 RH / Recruteur',
        'description': 'Fiches de poste, sourcing, onboarding',
        'file': 'rh-recruteur.md'
    },
    'support-client': {
        'name': '🎧 Support Client',
        'description': 'Tickets, FAQ, satisfaction',
        'file': 'support-client.md'
    },
    'legal': {
        'name': '⚖️ Juridique / Legal',
        'description': 'Contrats, conformité, RGPD',
        'file': 'legal.md'
    },
}

def get_template_choices() -> list[tuple[str, str]]:
    """Retourne les choix pour le dropdown de templates."""
    choices = [("-- Sélectionner un template --", "")]
    for key, info in TEMPLATE_INFO.items():
        label = f"{info['name']} - {info['description']}"
        choices.append((label, key))
    return choices


def get_template_content(template_key: str, base_path: Optional[Path] = None) -> Optional[str]:
    """Charge le contenu d'un template métier."""
    if not template_key or template_key not in TEMPLATE_INFO:
        return None
    
    info = TEMPLATE_INFO[template_key]
    
    # Chercher le fichier template
    if base_path is None:
        # Essayer plusieurs chemins possibles
        possible_paths = [
            Path(__file__).parent.parent.parent / "templates" / "metiers" / info['file'],
            Path("templates/metiers") / info['file'],
            Path("/app/templates/metiers") / info['file'],
        ]
    else:
        possible_paths = [base_path / "templates" / "metiers" / info['file']]
    
    for path in possible_paths:
        if path.exists():
            try:
                return path.read_text(encoding='utf-8')
            except Exception:
                continue
    
    return None


def get_template_labels() -> dict[str, str]:
    """Retourne un mapping key -> label pour l'affichage."""
    return {key: info['name'] for key, info in TEMPLATE_INFO.items()}
