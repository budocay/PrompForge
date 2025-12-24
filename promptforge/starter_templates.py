"""
Templates de démarrage rapide par métier.
Permet à un nouvel utilisateur de commencer en < 30 secondes.

Usage:
    from promptforge.starter_templates import STARTER_TEMPLATES, get_template

    template = get_template("seo")
    # Returns: {"name": "...", "config": "...", "description": "..."}
"""

from typing import Optional

# ============================================
# 5 TEMPLATES MÉTIER PRÉ-REMPLIS
# ============================================

STARTER_TEMPLATES = {

    # ==========================================
    # SEO / RÉFÉRENCEMENT
    # ==========================================
    "seo": {
        "name": "SEO Specialist",
        "icon": "🔍",
        "description": "Recherche de mots-clés, optimisation contenu, stratégie SEO",
        "config": """# Profil SEO - [Votre Site]

## Identité
- **Site**: example.com (à modifier)
- **Niche**: Votre thématique principale
- **Langue cible**: Français

## Métriques actuelles
- **DR/DA estimé**: 20-30
- **Trafic mensuel**: 5K-15K visites
- **Pages indexées**: 50-200

## Objectifs SEO
- Augmenter le trafic organique
- Cibler des mots-clés long-tail
- Améliorer le maillage interne

## Contraintes
- **KD maximum**: 30 (mots-clés accessibles)
- **Budget contenu**: 2-4 articles/semaine
- **Intent privilégiée**: Informationnelle (guides, tutoriels)

## Outils disponibles
- Google Search Console
- Google Analytics
- Outil SEO (Ahrefs/SEMrush/Ubersuggest)

## Concurrents à analyser
- concurrent1.com
- concurrent2.fr
- concurrent3.com

## Instructions pour le LLM
Quand je demande de l'aide SEO:
1. Propose des mots-clés avec KD < 30
2. Privilégie les requêtes long-tail (3-5 mots)
3. Suggère des structures d'articles optimisées
4. Inclus des recommandations de maillage interne
"""
    },

    # ==========================================
    # DÉVELOPPEUR BACKEND
    # ==========================================
    "dev_backend": {
        "name": "Dev Backend",
        "icon": "⚙️",
        "description": "APIs, bases de données, architecture serveur",
        "config": """# Profil Développeur Backend

## Stack Technique
- **Langage principal**: Python 3.11+
- **Framework**: FastAPI / Django / Flask (à préciser)
- **Base de données**: PostgreSQL
- **ORM**: SQLAlchemy / Django ORM
- **Cache**: Redis

## Infrastructure
- **Cloud**: AWS / GCP / Azure (à préciser)
- **Conteneurisation**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana

## Conventions de code
- **Formatter**: Black (line-length=100)
- **Linter**: Ruff
- **Tests**: pytest (couverture cible: 80%)
- **Type hints**: Obligatoires

## Architecture
- **Pattern**: Clean Architecture / Hexagonal
- **API Style**: REST (OpenAPI 3.0)
- **Auth**: JWT / OAuth2

## Projet actuel
- **Type**: API REST / Microservices
- **Description**: (à compléter)
- **Taille équipe**: 2-5 devs

## Instructions pour le LLM
Quand je demande de l'aide code:
1. Respecte PEP 8 et les conventions Black
2. Ajoute des type hints
3. Propose des tests unitaires
4. Gère les erreurs proprement (exceptions custom)
5. Docstrings format Google
"""
    },

    # ==========================================
    # MARKETING DIGITAL
    # ==========================================
    "marketing": {
        "name": "Marketing Digital",
        "icon": "📈",
        "description": "Campagnes, copywriting, acquisition, analytics",
        "config": """# Profil Marketing Digital

## Entreprise
- **Nom**: [Votre entreprise]
- **Type**: B2B SaaS / B2C / E-commerce (à préciser)
- **Proposition de valeur**: (1 phrase)

## Cible
- **Persona principal**: [Titre, âge, problème]
- **Taille entreprise cible**: PME / ETI / Grands comptes
- **Secteurs**: Tech, Finance, Retail...

## Canaux actifs
- **Paid**: Google Ads, Meta Ads, LinkedIn Ads
- **Organic**: SEO, Content Marketing
- **Email**: Newsletter, séquences nurturing
- **Social**: LinkedIn, Twitter/X

## Métriques suivies
- **CAC**: Coût d'acquisition client
- **LTV**: Lifetime value
- **ROAS**: Return on ad spend
- **MQL/SQL**: Leads qualifiés

## Budget
- **Ads mensuel**: [X]€
- **Contenu**: [X] articles/mois

## Ton de communication
- Professionnel mais accessible
- Data-driven
- Orienté résultats

## Instructions pour le LLM
Quand je demande de l'aide marketing:
1. Adapte le message à ma cible B2B/B2C
2. Propose des CTAs clairs
3. Inclus des métriques de succès
4. Suggère des variantes A/B
"""
    },

    # ==========================================
    # PRODUCT MANAGER
    # ==========================================
    "product": {
        "name": "Product Manager",
        "icon": "🎯",
        "description": "Specs, user stories, roadmap, priorisation",
        "config": """# Profil Product Manager

## Produit
- **Nom**: [Votre produit]
- **Type**: B2B SaaS / App mobile / Marketplace
- **Stade**: MVP / PMF / Scale
- **Mission**: (1 phrase)

## Utilisateurs
- **Persona principal**: [Nom, rôle, pain point]
- **Users actifs**: [X] MAU
- **NPS actuel**: [X]

## North Star Metric
- **Métrique principale**: [ex: Weekly Active Users]
- **Objectif**: [X] d'ici [date]

## Équipe
- **Squad**: [X] devs, [X] designers
- **Méthodologie**: Scrum / Kanban / Shape Up
- **Sprint**: 2 semaines

## Stack produit
- **Discovery**: Interviews, Analytics, Hotjar
- **Delivery**: Jira / Linear / Notion
- **Analytics**: Amplitude / Mixpanel

## Framework priorisation
- RICE / ICE / MoSCoW
- Critères: Impact, Effort, Confidence

## Instructions pour le LLM
Quand je demande de l'aide produit:
1. Structure en User Stories (As a... I want... So that...)
2. Inclus les critères d'acceptation
3. Identifie les edge cases
4. Propose des métriques de succès
5. Estime la complexité (S/M/L/XL)
"""
    },

    # ==========================================
    # GÉNÉRAL / POLYVALENT
    # ==========================================
    "general": {
        "name": "Polyvalent",
        "icon": "🚀",
        "description": "Template générique adaptable à tout contexte",
        "config": """# Profil Général

## Contexte
- **Rôle**: [Votre fonction]
- **Entreprise/Projet**: [Nom]
- **Secteur**: [Industrie]

## Objectifs principaux
1. [Objectif 1]
2. [Objectif 2]
3. [Objectif 3]

## Contraintes
- **Budget**: [Limité / Modéré / Flexible]
- **Temps**: [Urgent / Normal / Long terme]
- **Ressources**: [Solo / Petite équipe / Grande équipe]

## Outils utilisés
- [Outil 1]
- [Outil 2]
- [Outil 3]

## Style de communication préféré
- [ ] Concis et direct
- [ ] Détaillé avec exemples
- [ ] Technique et précis
- [ ] Accessible et pédagogique

## Instructions pour le LLM
Quand je te demande de l'aide:
1. Demande des clarifications si besoin
2. Propose des solutions concrètes
3. Structure ta réponse clairement
4. Donne des exemples pratiques
"""
    },

    # ==========================================
    # DATA ANALYST (BONUS)
    # ==========================================
    "data": {
        "name": "Data Analyst",
        "icon": "📊",
        "description": "SQL, dashboards, analytics, reporting",
        "config": """# Profil Data Analyst

## Stack Data
- **SQL**: PostgreSQL / BigQuery / Snowflake
- **Niveau**: Avancé (window functions, CTEs)
- **BI Tool**: Looker / Tableau / Metabase / Power BI
- **Python**: Pandas, notebooks Jupyter

## Sources de données
- Base de production (PostgreSQL)
- Analytics (Amplitude/Mixpanel/GA4)
- CRM (Salesforce/HubSpot)
- Marketing (Google Ads, Meta)

## Métriques business
- **Revenue**: MRR, ARR, ARPU
- **Acquisition**: CAC, Leads, Conversion
- **Retention**: Churn, Cohorts, NRR
- **Engagement**: DAU/MAU, Session time

## Stakeholders
- Direction (C-level)
- Product
- Marketing
- Sales

## Conventions
- Nommage: snake_case
- Documentation: dbt-style
- Versionning: Git

## Instructions pour le LLM
Quand je demande de l'aide data:
1. Écris des requêtes SQL optimisées
2. Explique la logique métier
3. Propose des visualisations adaptées
4. Anticipe les edge cases (NULL, doublons)
5. Suggère des améliorations de perf si besoin
"""
    },
}


def get_template(key: str) -> Optional[dict]:
    """Retourne un template par sa clé."""
    return STARTER_TEMPLATES.get(key)


def list_templates() -> list[dict]:
    """Retourne la liste des templates disponibles."""
    return [
        {
            "key": key,
            "name": tpl["name"],
            "icon": tpl["icon"],
            "description": tpl["description"]
        }
        for key, tpl in STARTER_TEMPLATES.items()
    ]


def get_template_config(key: str) -> str:
    """Retourne uniquement le contenu config d'un template."""
    tpl = STARTER_TEMPLATES.get(key)
    return tpl["config"] if tpl else ""


def get_template_choices() -> list[tuple[str, str]]:
    """Retourne les choix pour un dropdown Gradio."""
    return [
        (f"{tpl['icon']} {tpl['name']}", key)
        for key, tpl in STARTER_TEMPLATES.items()
    ]
