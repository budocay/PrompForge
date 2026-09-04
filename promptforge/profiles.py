"""
Profils de reformatage optimisés pour différents modèles LLM.

Tarifs et fenêtres de contexte vérifiés le 2026-09-03 sur les pages officielles
de tarification Anthropic et OpenAI (cf. MEMORY/VEILLE.md). Chaque entrée de
MODEL_PRICING porte sa source et sa date ; une source vide signale une valeur
qu'aucune source officielle ne confirme.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TargetModel(Enum):
    """Modèle LLM cible pour le reformatage."""
    # Claude (Anthropic) - Décembre 2025
    CLAUDE_OPUS_4_5 = "claude-opus-4.5"
    CLAUDE_SONNET_4_5 = "claude-sonnet-4.5"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4.5"
    
    # GPT (OpenAI) - Décembre 2025
    GPT_5_1 = "gpt-5.1"
    GPT_5_1_MINI = "gpt-5.1-mini"
    GPT_5_PRO = "gpt-5-pro"
    
    # Gemini (Google) - Décembre 2025
    GEMINI_3_PRO = "gemini-3-pro"
    GEMINI_3_FLASH = "gemini-3-flash"
    
    # Universel
    UNIVERSAL = "universal"


class PromptStyle(Enum):
    """Style de prompt souhaité."""
    CONCIS = "concis"
    DETAILLE = "detaille"
    TECHNIQUE = "technique"
    CREATIF = "creatif"


@dataclass
class ModelPricing:
    """Prix d'un modèle par million de tokens, avec sa provenance.

    `cached_input` vaut ``None`` quand aucun tarif de cache n'est confirmé par
    une source officielle. Surtout pas ``0.0`` : zéro facturerait silencieusement
    un cache gratuit qui n'existe pas. `estimate_cost()` force alors
    ``cached_pct = 0`` et facture tout en entrée fraîche.

    `source_url` vide signale une valeur qu'aucune source officielle ne confirme
    aujourd'hui (modèle arrêté, identifiant sans existence connue, ou moyenne
    synthétique). Voir F-028 pour le sort de ces entrées.
    """
    input_price: float      # $ par million de tokens en entrée
    output_price: float     # $ par million de tokens en sortie
    context_window: int     # Fenêtre de contexte max, en tokens
    cached_input: Optional[float] = None  # $ / MTok en cache hit ; None = non confirmé
    source_url: str = ""    # Page officielle consultée
    verified_on: str = ""   # Date de vérification, ISO 8601

    def estimate_cost(self, input_tokens: int, output_tokens: int, cached_pct: float = 0) -> float:
        """Estime le coût d'une requête.

        Sans tarif de cache confirmé, `cached_pct` est ignoré et forcé à 0 :
        on préfère surestimer le coût que d'appliquer une remise inventée.
        """
        if self.cached_input is None:
            cached_pct = 0
        cached_tokens = input_tokens * cached_pct
        fresh_tokens = input_tokens - cached_tokens
        cached_price = 0.0 if self.cached_input is None else self.cached_input
        input_cost = (fresh_tokens * self.input_price + cached_tokens * cached_price) / 1_000_000
        output_cost = output_tokens * self.output_price / 1_000_000
        return input_cost + output_cost


@dataclass
class ReformatProfile:
    """Profil de reformatage complet."""
    target_model: TargetModel
    style: PromptStyle
    include_examples: bool = False
    include_constraints: bool = True
    include_output_format: bool = True
    pricing: Optional[ModelPricing] = None


# ============================================
# Prix des modèles
# Vérifiés le 2026-09-03 sur les pages officielles de tarification
# (voir MEMORY/VEILLE.md, section « Modèles cibles du reformatage et tarifs »).
# Chaque entrée porte son URL de source et sa date de vérification.
# Une source vide = aucune source officielle ne confirme la valeur (F-028).
# ============================================

ANTHROPIC_PRICING_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
OPENAI_PRICING_URL = "https://developers.openai.com/api/docs/pricing"
PRICING_VERIFIED_ON = "2026-09-03"

MODEL_PRICING = {
    # Claude (Anthropic) - tarifs et fenêtres relevés sur la page officielle
    TargetModel.CLAUDE_OPUS_4_5: ModelPricing(
        input_price=5.0,
        output_price=25.0,
        context_window=200_000,  # antérieur à Claude 4.6 : pas de contexte 1M
        cached_input=0.5,
        source_url=ANTHROPIC_PRICING_URL,
        verified_on=PRICING_VERIFIED_ON,
    ),
    TargetModel.CLAUDE_SONNET_4_5: ModelPricing(
        input_price=3.0,
        output_price=15.0,
        # Corrigé : le contexte 1M à prix standard est réservé à Claude 4.6+.
        context_window=200_000,
        cached_input=0.3,
        source_url=ANTHROPIC_PRICING_URL,
        verified_on=PRICING_VERIFIED_ON,
    ),
    TargetModel.CLAUDE_HAIKU_4_5: ModelPricing(
        # Corrigé : le dépôt affichait 0.25 / 1.25, soit un facteur 4 sous le
        # tarif officiel.
        input_price=1.0,
        output_price=5.0,
        context_window=200_000,
        cached_input=0.1,  # multiplicateur standard 0.1x
        source_url=ANTHROPIC_PRICING_URL,
        verified_on=PRICING_VERIFIED_ON,
    ),

    # GPT (OpenAI)
    TargetModel.GPT_5_1: ModelPricing(
        input_price=1.25,
        output_price=10.0,
        context_window=400_000,  # corrigé : le dépôt annonçait 272 000
        cached_input=0.125,
        source_url=OPENAI_PRICING_URL,
        verified_on=PRICING_VERIFIED_ON,
    ),
    TargetModel.GPT_5_1_MINI: ModelPricing(
        # Aucune source : `gpt-5.1-mini` n'a aucune existence officielle connue
        # (404 sur la fiche modèle). Les valeurs ci-dessous sont celles déjà
        # présentes dans le dépôt, recopiées du tarif de `gpt-5-mini`.
        # Elles ne sont ni corrigées ni sourcées ici : le sort de ce membre de
        # TargetModel relève de F-028.
        input_price=0.25,
        output_price=2.0,
        context_window=200_000,
        cached_input=0.025,
    ),
    TargetModel.GPT_5_PRO: ModelPricing(
        # Corrigé : le dépôt sous-estimait l'entrée d'un facteur 3 et la sortie
        # d'un facteur 6.
        input_price=15.0,
        output_price=120.0,
        # Corrigé : 272 000 est le plafond de sortie, pas la fenêtre de contexte.
        context_window=400_000,
        # GPT-5 Pro ne propose pas de cache d'entrée : aucun tarif à facturer.
        cached_input=None,
        source_url=OPENAI_PRICING_URL,
        verified_on=PRICING_VERIFIED_ON,
    ),

    # Gemini (Google)
    TargetModel.GEMINI_3_PRO: ModelPricing(
        # Aucune source : `gemini-3-pro-preview` est arrêté depuis le
        # 2026-03-09. Valeurs du dépôt conservées telles quelles ; le
        # remplacement de l'identifiant relève de F-028.
        input_price=2.0,
        output_price=12.0,
        context_window=1_000_000,
        cached_input=0.2,
    ),
    TargetModel.GEMINI_3_FLASH: ModelPricing(
        # Aucune source : `gemini-3-flash-preview` est déprécié et ces tarifs ne
        # correspondent à aucune version active. Valeurs du dépôt conservées
        # telles quelles ; leur sort relève de F-028.
        input_price=0.5,
        output_price=2.0,
        context_window=1_000_000,
        cached_input=0.05,
    ),

    # Universel
    TargetModel.UNIVERSAL: ModelPricing(
        # Aucune source par construction : moyenne synthétique, ne désigne aucun
        # modèle réel. Traité par F-028.
        input_price=1.0,
        output_price=5.0,
        context_window=128_000,
        cached_input=0.1,
    ),
}


# ============================================
# System Prompts par Modèle
# Basés sur les documentations officielles:
# - Anthropic: docs.anthropic.com (XML tags)
# - OpenAI: platform.openai.com (Markdown + delimiters)
# - Google: ai.google.dev (XML-style tags ou Markdown)
# ============================================

# =============================================================================
# 🚨 RÈGLE ANTI-BULLSHIT - Appliquée à tous les prompts système
# =============================================================================

NO_BULLSHIT_RULE = """

🚨 RÈGLE CRITIQUE - AUCUNE MÉTRIQUE INVENTÉE 🚨

Tu reformates des prompts, tu ne prédis PAS les performances. INTERDICTIONS ABSOLUES:

❌ INTERDIT d'inventer des scores (pas de "SWE-bench: 92/100", "Code Quality: 98%")
❌ INTERDIT d'inventer des temps (pas de "Temps: 15s → 3s", "-80%")
❌ INTERDIT d'inventer des pourcentages de gain (pas de "+48% clarté")
❌ INTERDIT de mentionner des benchmarks comme si tu les avais mesurés
❌ INTERDIT d'inventer des IDs ou chemins de fichiers fictifs
❌ INTERDIT de faire des tableaux "Avant/Après" avec des chiffres fictifs
❌ INTERDIT d'ajouter des sections "Analyse", "Métriques", "Gains", "Conclusion"

✅ AUTORISÉ: Reformater le prompt avec une structure XML claire
✅ AUTORISÉ: Ajouter du contexte, des instructions, des contraintes
✅ AUTORISÉ: Proposer un format de sortie approprié

🎯 Ta réponse = UNIQUEMENT le prompt XML reformaté. RIEN D'AUTRE.
Pas d'analyse, pas de métriques, pas de tableaux, pas de conclusion."""

# =============================================================================

SYSTEM_PROMPT_CLAUDE_OPUS = """⚠️ FORMAT OBLIGATOIRE: XML UNIQUEMENT - PAS DE MARKDOWN ⚠️

Tu transformes des demandes utilisateur en prompts XML optimisés pour Claude Opus 4.5.

⚠️ CONTEXTE IMPORTANT: Tu opères dans un outil de DÉVELOPPEMENT LOGICIEL (PromptForge).
Les demandes concernent TOUJOURS du code, de la programmation, des projets informatiques.
- "scanner" = analyser/parcourir du CODE SOURCE (PAS de l'OCR physique)
- "projet" = projet de DÉVELOPPEMENT (repo git, fichiers code)
- "analyse" = analyse de CODE ou d'architecture logicielle

RÈGLE CRITIQUE: Ta réponse DOIT être UNIQUEMENT des balises XML.
❌ INTERDIT: #, ##, **, -, *, ```, titres Markdown, listes avec tirets
✅ OBLIGATOIRE: <balise>contenu</balise>

=== BALISES XML À UTILISER ===
<task_definition> - Objectif principal clair
<context> - Informations de contexte projet/technique
<requirements> - Liste des exigences fonctionnelles
<constraints> - Contraintes techniques/business
<output_format> - Format de sortie attendu
<thinking_approach> - Approche de raisonnement (optionnel, pour tâches complexes)

=== EXEMPLE CORRECT ===

Demande: "refonte UI backoffice"

<task_definition>
Créer un thème global unifié pour le backoffice qui harmonise l'UI et les couleurs.
</task_definition>

<context>
Projet: Application backoffice existante
Problème: Incohérence visuelle entre les pages, plusieurs jeux de couleurs
Stack: Tailwind CSS, TypeScript
</context>

<requirements>
Thème global applicable à toutes les pages
Fonction getSectionColor() pour cohérence des couleurs
Support dark mode avec classes dark:*
Représentation UI/UX unique par typologie mais cohérente globalement
</requirements>

<constraints>
Respecter les conventions de code existantes
Maintenir la lisibilité du code
Compatibilité avec le système de design actuel
</constraints>

<output_format>
Configuration theme.config.ts mise à jour
Fonction getSectionColor() implémentée
Classes Tailwind pour dark mode
Documentation des changements
</output_format>

=== FIN EXEMPLE ===

⚠️ RAPPEL FINAL:
- JAMAIS de Markdown (pas de #, ##, **, -, listes)
- UNIQUEMENT des balises XML <...>...</...>
- Commence DIRECTEMENT par <task_definition>
- Même langue que l'utilisateur
- Détaille chaque section (Opus excelle sur les tâches complexes)
- TOUJOURS interpréter dans le contexte du DÉVELOPPEMENT LOGICIEL"""


SYSTEM_PROMPT_CLAUDE_SONNET = """⚠️ FORMAT OBLIGATOIRE: XML UNIQUEMENT - PAS DE MARKDOWN ⚠️

Tu transformes des demandes en prompts XML optimisés pour Claude Sonnet 4.5.

⚠️ CONTEXTE: Outil de DÉVELOPPEMENT LOGICIEL. Les demandes concernent du CODE/programmation.
- "scanner" = analyser du CODE SOURCE (pas OCR)
- "projet" = projet de développement (git, fichiers code)

RÈGLE CRITIQUE: Ta réponse DOIT être UNIQUEMENT des balises XML.
❌ INTERDIT: #, ##, **, -, *, ```, titres Markdown, listes avec tirets
✅ OBLIGATOIRE: <balise>contenu</balise>

=== BALISES XML À UTILISER ===
<task> - Objectif principal
<context> - Contexte technique/projet
<instructions> - Étapes numérotées (1. 2. 3. dans le contenu XML)
<output_format> - Format de sortie attendu

=== EXEMPLE CORRECT ===

Demande: "corrige mon code"

<task>
Analyser et corriger le code fourni en identifiant bugs et améliorations possibles.
</task>

<context>
Code existant nécessitant debug et optimisation.
Langage et framework à détecter depuis le code fourni.
</context>

<instructions>
1. Identifier les bugs et erreurs de logique
2. Corriger les problèmes de syntaxe
3. Améliorer la lisibilité et les performances
4. Suggérer des refactorisations si pertinent
</instructions>

<output_format>
Code corrigé avec commentaires sur les changements
Liste des bugs identifiés et corrigés
Suggestions d'amélioration optionnelles
</output_format>

=== FIN EXEMPLE ===

⚠️ RAPPEL: JAMAIS de Markdown (#, ##, **, -). Commence DIRECTEMENT par <task>. Même langue."""


SYSTEM_PROMPT_CLAUDE_HAIKU = """⚠️ XML UNIQUEMENT - PAS DE MARKDOWN ⚠️

Contexte: Outil de DÉVELOPPEMENT LOGICIEL. Demandes = CODE/programmation.

Réécris en XML court et efficace pour Claude Haiku 4.5.

❌ INTERDIT: #, ##, **, -, listes Markdown
✅ OBLIGATOIRE: <balise>contenu</balise>

=== EXEMPLE ===
Demande: "explique les promises"

<context>
Question JavaScript sur les Promises et programmation asynchrone.
</context>

<instructions>
Expliquer les Promises: concept, syntaxe async/await, exemples pratiques.
</instructions>

<output_format>
Explication concise avec exemples de code fonctionnels.
</output_format>

=== FIN ===

⚠️ RÈGLE: XML seulement, commence par <context>, même langue."""


SYSTEM_PROMPT_GPT_5_1 = """Tu réécris des demandes en prompts Markdown optimisés pour GPT-5.1.

⚠️ CONTEXTE: Outil de DÉVELOPPEMENT LOGICIEL. Les demandes concernent du CODE/programmation.
- "scanner" = analyser du CODE SOURCE (pas OCR physique)
- "projet" = projet de développement (git, fichiers code)

=== FORCES DE GPT-5.1 ===
- Extrêmement steerable (suit les instructions avec précision)
- 45% moins d'hallucinations que GPT-4
- Contexte 272K tokens

=== RÈGLES GPT-5.1 ===
- Instructions EXPLICITES et NON AMBIGUËS
- Éviter les contradictions
- Format de sortie PRÉCIS

=== EXEMPLE ===
Demande: "créé un dashboard"

Ta réponse:
## Contexte
Application web nécessitant un tableau de bord d'administration pour visualiser les métriques.

## Objectif
Créer un dashboard responsive avec KPIs, graphiques interactifs et liste d'activités.

## Exigences
- Cartes KPIs avec statistiques clés
- Graphiques interactifs (line/bar charts)
- Liste des activités récentes paginée
- Design responsive mobile-first
- Composants réutilisables

## Contraintes
- Performance: lazy loading des données
- Accessibilité WCAG 2.1 niveau AA

## Format de sortie attendu
Composants React avec:
1. Structure des fichiers
2. Code commenté
3. Styles Tailwind
=== FIN ===

RÈGLES ABSOLUES:
- Réponds UNIQUEMENT avec le Markdown structuré
- PAS d'intro "Voici le prompt..."
- PAS d'explication après
- Sections: Contexte, Objectif, Exigences, Contraintes, Format de sortie
- MÊME LANGUE que l'utilisateur"""


SYSTEM_PROMPT_GPT_5_1_MINI = """Contexte: Outil de DÉVELOPPEMENT LOGICIEL (code/programmation).
Tu réécris en prompts Markdown courts pour GPT-5.1 Mini.

=== EXEMPLE ===
Demande: "trie une liste"

Ta réponse:
## Objectif
Trier une liste en Python avec les méthodes natives.

## Exigences
- Montrer sorted() pour copie triée
- Montrer .sort() pour tri in-place
- Exemples avec listes de nombres et strings

## Format de sortie
Code Python commenté, concis.
=== FIN ===

RÈGLES: Markdown court. Pas d'intro. Même langue."""


SYSTEM_PROMPT_GPT_5_PRO = """Tu réécris des demandes complexes en prompts Markdown détaillés pour GPT-5 Pro.

⚠️ CONTEXTE: Outil de DÉVELOPPEMENT LOGICIEL. Les demandes concernent du CODE/programmation.
- "scanner" = analyser du CODE SOURCE (pas OCR)
- "projet" = projet de développement (git, fichiers)

=== FORCES DE GPT-5 PRO ===
- Raisonnement très approfondi (jusqu'à 10+ minutes)
- Idéal: sciences, maths, recherche, problèmes complexes

=== ASTUCE ===
Ajouter "Réfléchis en profondeur à ce problème" déclenche le mode raisonnement.

=== EXEMPLE ===
Demande: "optimise ma requête SQL lente"

Ta réponse:
## Définition du problème
Requête SQL avec problèmes de performance sévères nécessitant une analyse approfondie et systématique.

## Contexte
- Base de données relationnelle (PostgreSQL/MySQL)
- Tables volumineuses avec jointures multiples potentielles
- Temps d'exécution actuel inacceptable pour la production

## Analyse requise
Réfléchis en profondeur à ce problème:
1. Analyser le plan d'exécution (EXPLAIN ANALYZE)
2. Identifier les goulots d'étranglement (full table scans, nested loops inefficaces)
3. Évaluer la cardinalité des jointures
4. Vérifier les index existants vs manquants
5. Considérer la dénormalisation si bénéfique

## Contraintes
- Ne pas casser la logique métier existante
- Maintenir la compatibilité avec l'ORM si utilisé

## Format de sortie attendu
1. Diagnostic détaillé avec métriques avant/après
2. Requête optimisée avec justifications ligne par ligne
3. Scripts CREATE INDEX recommandés
4. Estimation du gain de performance attendu
=== FIN ===

RÈGLES:
- Markdown détaillé pour problèmes complexes
- Inclure "Réfléchis en profondeur" pour deep reasoning
- Pas d'intro, pas d'explication après
- Même langue"""


SYSTEM_PROMPT_GEMINI_3_PRO = """⚠️ FORMAT OBLIGATOIRE: XML UNIQUEMENT - PAS DE MARKDOWN ⚠️

Tu transformes des demandes en prompts XML optimisés pour Gemini 3 Pro.

⚠️ CONTEXTE: Outil de DÉVELOPPEMENT LOGICIEL. Les demandes concernent du CODE/programmation.
- "scanner" = analyser du CODE SOURCE (pas OCR physique)
- "projet" = projet de développement (git, fichiers code)

RÈGLE CRITIQUE: Ta réponse DOIT être UNIQUEMENT des balises XML.
❌ INTERDIT: #, ##, **, -, *, ```, Markdown
✅ OBLIGATOIRE: <balise>contenu</balise>

=== BALISES XML À UTILISER ===
<objective> - Objectif principal
<context> - Contexte (Gemini excelle sur documents longs)
<analysis_tasks> - Tâches d'analyse
<output_format> - Format de sortie

=== EXEMPLE CORRECT ===

Demande: "analyse ce document"

<objective>
Analyser le document fourni pour extraire les informations clés et produire une synthèse actionnable.
</objective>

<context>
Document à analyser en profondeur.
Gemini 3 Pro peut traiter des documents très longs (jusqu'à 750K mots).
Utiliser le contexte étendu pour une analyse complète.
</context>

<analysis_tasks>
1. Identifier les thèmes principaux et secondaires
2. Extraire les données chiffrées et faits importants
3. Repérer les arguments clés et conclusions
4. Détecter les incohérences ou points d'attention
</analysis_tasks>

<output_format>
Résumé exécutif (5-10 lignes)
Points clés numérotés
Données/chiffres importants
Recommandations ou points d'action
</output_format>

=== FIN ===

⚠️ RAPPEL: JAMAIS de Markdown. Commence par <objective>. Même langue."""


SYSTEM_PROMPT_GEMINI_3_FLASH = """⚠️ XML UNIQUEMENT - PAS DE MARKDOWN ⚠️

Contexte: Outil de DÉVELOPPEMENT LOGICIEL. Demandes = CODE/programmation.

Réécris en XML court et efficace pour Gemini 3 Flash.

❌ INTERDIT: #, ##, **, -, Markdown
✅ OBLIGATOIRE: <balise>contenu</balise>

=== EXEMPLE ===
Demande: "traduis en anglais"

<context>
Traduction français vers anglais demandée.
</context>

<task>
Traduire le texte en préservant le sens, le ton et les nuances.
</task>

<output_format>
Texte traduit en anglais, fidèle à l'original.
</output_format>

=== FIN ===

⚠️ RÈGLE: XML seulement, commence par <context>, même langue."""


SYSTEM_PROMPT_UNIVERSAL = """⚠️ FORMAT OBLIGATOIRE: XML UNIQUEMENT - PAS DE MARKDOWN ⚠️

Tu transformes des demandes utilisateur en prompts XML structurés.

⚠️ CONTEXTE IMPORTANT: Tu opères dans un outil de DÉVELOPPEMENT LOGICIEL (PromptForge).
Les demandes concernent TOUJOURS du code, de la programmation, des projets informatiques.
- "scanner" = analyser/parcourir du CODE SOURCE (PAS de l'OCR physique)
- "projet" = projet de DÉVELOPPEMENT (repo git, fichiers code)
- "analyse" = analyse de CODE ou d'architecture logicielle

RÈGLE CRITIQUE: Ta réponse DOIT être UNIQUEMENT des balises XML.
❌ INTERDIT: #, ##, ###, **, *, -, ```, titres Markdown, listes avec tirets/astérisques
✅ OBLIGATOIRE: <balise>contenu</balise>

=== BALISES XML À UTILISER ===
<context> - Contexte du projet/de la demande
<instructions> - Ce que le modèle doit faire (liste numérotée OK à l'intérieur)
<output_format> - Format de sortie attendu
<constraints> - Contraintes optionnelles

=== EXEMPLE CORRECT ===

Demande: "aide moi avec mon projet flutter"

<context>
Projet Flutter nécessitant assistance technique.
Type: Application mobile cross-platform.
</context>

<instructions>
1. Analyser les besoins spécifiques du projet
2. Proposer des solutions adaptées à Flutter
3. Fournir du code Dart fonctionnel
4. Respecter les bonnes pratiques Flutter/Dart
</instructions>

<output_format>
Réponse structurée avec:
Code Dart commenté
Explications des choix techniques
Suggestions d'amélioration
</output_format>

=== FIN EXEMPLE ===

⚠️ RAPPEL FINAL:
- JAMAIS de Markdown (pas de #, ##, **, -, *)
- UNIQUEMENT des balises XML <...>...</...>
- Commence DIRECTEMENT par <context>
- Utilise la MÊME LANGUE que l'utilisateur
- Pas de texte avant ou après le XML"""


# ============================================
# Modificateurs de style
# ============================================

STYLE_MODIFIERS = {
    PromptStyle.CONCIS: """
## Style: CONCIS
- Réponses directes et courtes
- Pas de détails superflus
- Focus sur l'essentiel""",
    
    PromptStyle.DETAILLE: """
## Style: DÉTAILLÉ
- Explications complètes
- Couvre tous les aspects
- Inclut le raisonnement""",
    
    PromptStyle.TECHNIQUE: """
## Style: TECHNIQUE
- Terminologie précise
- Détails d'implémentation
- Best practices incluses""",
    
    PromptStyle.CREATIF: """
## Style: CRÉATIF
- Place à l'interprétation
- Encourage l'originalité
- Focus sur l'intention"""
}


# ============================================
# Fonctions utilitaires
# ============================================

SYSTEM_PROMPTS = {
    TargetModel.CLAUDE_OPUS_4_5: SYSTEM_PROMPT_CLAUDE_OPUS,
    TargetModel.CLAUDE_SONNET_4_5: SYSTEM_PROMPT_CLAUDE_SONNET,
    TargetModel.CLAUDE_HAIKU_4_5: SYSTEM_PROMPT_CLAUDE_HAIKU,
    TargetModel.GPT_5_1: SYSTEM_PROMPT_GPT_5_1,
    TargetModel.GPT_5_1_MINI: SYSTEM_PROMPT_GPT_5_1_MINI,
    TargetModel.GPT_5_PRO: SYSTEM_PROMPT_GPT_5_PRO,
    TargetModel.GEMINI_3_PRO: SYSTEM_PROMPT_GEMINI_3_PRO,
    TargetModel.GEMINI_3_FLASH: SYSTEM_PROMPT_GEMINI_3_FLASH,
    TargetModel.UNIVERSAL: SYSTEM_PROMPT_UNIVERSAL,
}


def get_system_prompt(target: TargetModel) -> str:
    """Retourne le system prompt pour le modèle cible avec règle anti-bullshit."""
    base_prompt = SYSTEM_PROMPTS.get(target, SYSTEM_PROMPT_UNIVERSAL)
    # Ajouter la règle anti-bullshit à TOUS les prompts
    return base_prompt + NO_BULLSHIT_RULE


def get_style_modifier(style: PromptStyle) -> str:
    """Retourne le modificateur de style."""
    return STYLE_MODIFIERS.get(style, "")


def build_reformat_prompt(
    raw_prompt: str,
    project_context: str,
    profile: ReformatProfile
) -> tuple[str, str]:
    """Construit le prompt pour le reformatage - version simplifiée."""
    system_prompt = get_system_prompt(profile.target_model)
    style_modifier = get_style_modifier(profile.style)
    if style_modifier:
        system_prompt += "\n" + style_modifier
    
    # User prompt SIMPLE et DIRECT
    if project_context.strip():
        user_prompt = f"""CONTEXTE PROJET:
{project_context}

DEMANDE À REFORMATER:
{raw_prompt}

Réécris cette demande en prompt structuré. Intègre les infos du contexte projet."""
    else:
        user_prompt = f"""DEMANDE À REFORMATER:
{raw_prompt}

Réécris cette demande en prompt structuré."""
    
    return system_prompt, user_prompt


def get_model_optimization_tips(target: TargetModel) -> str:
    """Retourne des conseils d'optimisation spécifiques au modèle cible."""
    tips = {
        TargetModel.CLAUDE_OPUS_4_5: """
Forces à exploiter:
- Excelle sur les tâches complexes et longues (agents, architecture, code avancé)
- Comprend très bien les balises XML structurées
- Gère des contextes très longs (200K tokens)
- Peut utiliser le mode "thinking" pour réflexion approfondie

Optimisations:
→ Inclure un contexte COMPLET et détaillé
→ Ajouter une section <thinking_approach> pour tâches complexes
→ Utiliser <quality_criteria> pour l'auto-évaluation
→ Être explicite sur les nuances et cas particuliers""",

        TargetModel.CLAUDE_SONNET_4_5: """
Forces à exploiter:
- Excellent équilibre performance/coût
- Très bon pour le code et les agents au quotidien
- Mode hybride: rapide OU raisonnement étendu

Optimisations:
→ Contexte essentiel mais concis
→ Instructions claires et directes
→ Bien structurer avec <requirements> et <constraints>""",

        TargetModel.CLAUDE_HAIKU_4_5: """
Forces à exploiter:
- Ultra-rapide et économique
- Idéal pour tâches simples et volume élevé

Optimisations:
→ Prompt TRÈS COURT (moins c'est mieux)
→ Seulement 2-3 sections XML essentielles
→ Instructions directes, pas de fioritures""",

        TargetModel.GPT_5_1: """
Forces à exploiter:
- Extrêmement steerable (suit les instructions avec précision chirurgicale)
- 45% moins d'hallucinations que GPT-4
- Contexte 272K tokens

Optimisations:
→ Instructions EXPLICITES et non ambiguës
→ Éviter les contradictions dans les instructions
→ Format de sortie PRÉCIS (GPT-5.1 le suivra exactement)
→ Sections claires: Contexte, Objectif, Exigences, Contraintes""",

        TargetModel.GPT_5_1_MINI: """
Forces à exploiter:
- Rapide et très économique
- Steerable comme GPT-5.1
- Bon pour tâches simples à moyennes

Optimisations:
→ Prompt CONCIS
→ Instructions directes
→ Éviter le sur-prompting""",

        TargetModel.GPT_5_PRO: """
Forces à exploiter:
- Raisonnement très approfondi (jusqu'à 10+ min de réflexion)
- Idéal: sciences, maths, recherche, problèmes complexes

Optimisations:
→ Ajouter "Réfléchis en profondeur à ce problème" pour deep reasoning
→ Section "Définition du problème" très détaillée
→ Hypothèses et contraintes explicites
→ Contexte technique complet""",

        TargetModel.GEMINI_3_PRO: """
Forces à exploiter:
- Contexte ÉNORME de 1M tokens
- Excellent pour documents très longs
- Multimodal avancé (texte, image, audio, vidéo)

Optimisations:
→ Inclure TOUT le contexte pertinent (il gère)
→ Section <objective> pour l'objectif principal
→ Idéal pour analyse de documents entiers""",

        TargetModel.GEMINI_3_FLASH: """
Forces à exploiter:
- Très rapide comme Haiku
- Contexte 1M tokens comme Pro

Optimisations:
→ Prompt court mais contexte peut être long
→ Instructions directes""",

        TargetModel.UNIVERSAL: """
Compatibilité maximale avec tous les LLMs:
- Structure XML claire et standard
- Instructions explicites et non ambiguës
- Niveau de détail modéré
- Format de sortie bien défini"""
    }
    
    return tips.get(target, tips[TargetModel.UNIVERSAL])


# ============================================
# Profils prédéfinis
# ============================================

PRESET_PROFILES = {
    # Claude (Anthropic)
    "claude_opus_4.5": ReformatProfile(
        target_model=TargetModel.CLAUDE_OPUS_4_5,
        style=PromptStyle.DETAILLE,
        include_examples=True,
        pricing=MODEL_PRICING[TargetModel.CLAUDE_OPUS_4_5]
    ),
    "claude_sonnet_4.5": ReformatProfile(
        target_model=TargetModel.CLAUDE_SONNET_4_5,
        style=PromptStyle.TECHNIQUE,
        include_examples=True,
        pricing=MODEL_PRICING[TargetModel.CLAUDE_SONNET_4_5]
    ),
    "claude_haiku_4.5": ReformatProfile(
        target_model=TargetModel.CLAUDE_HAIKU_4_5,
        style=PromptStyle.CONCIS,
        include_examples=False,
        pricing=MODEL_PRICING[TargetModel.CLAUDE_HAIKU_4_5]
    ),
    
    # GPT (OpenAI)
    "gpt_5.1": ReformatProfile(
        target_model=TargetModel.GPT_5_1,
        style=PromptStyle.DETAILLE,
        include_examples=True,
        pricing=MODEL_PRICING[TargetModel.GPT_5_1]
    ),
    "gpt_5.1_mini": ReformatProfile(
        target_model=TargetModel.GPT_5_1_MINI,
        style=PromptStyle.CONCIS,
        include_examples=False,
        pricing=MODEL_PRICING[TargetModel.GPT_5_1_MINI]
    ),
    "gpt_5_pro": ReformatProfile(
        target_model=TargetModel.GPT_5_PRO,
        style=PromptStyle.DETAILLE,
        include_examples=True,
        pricing=MODEL_PRICING[TargetModel.GPT_5_PRO]
    ),
    
    # Gemini (Google)
    "gemini_3_pro": ReformatProfile(
        target_model=TargetModel.GEMINI_3_PRO,
        style=PromptStyle.DETAILLE,
        include_examples=True,
        pricing=MODEL_PRICING[TargetModel.GEMINI_3_PRO]
    ),
    "gemini_3_flash": ReformatProfile(
        target_model=TargetModel.GEMINI_3_FLASH,
        style=PromptStyle.CONCIS,
        include_examples=False,
        pricing=MODEL_PRICING[TargetModel.GEMINI_3_FLASH]
    ),
    
    # Universel
    "universel": ReformatProfile(
        target_model=TargetModel.UNIVERSAL,
        style=PromptStyle.DETAILLE,
        include_examples=True,
        pricing=MODEL_PRICING[TargetModel.UNIVERSAL]
    ),
}


def get_profile(name: str) -> ReformatProfile:
    """Récupère un profil prédéfini."""
    return PRESET_PROFILES.get(name, PRESET_PROFILES["universel"])


def list_profiles() -> list[str]:
    """Liste les noms des profils disponibles."""
    return list(PRESET_PROFILES.keys())


def get_pricing(model: TargetModel) -> ModelPricing:
    """Récupère le pricing d'un modèle."""
    return MODEL_PRICING.get(model, MODEL_PRICING[TargetModel.UNIVERSAL])


# ============================================
# Comparaison des modèles
# ============================================

def compare_models(input_tokens: int = 1000, output_tokens: int = 500) -> list[dict]:
    """
    Compare les modèles par prix et caractéristiques.
    
    Args:
        input_tokens: Nombre de tokens en entrée pour le calcul
        output_tokens: Nombre de tokens en sortie pour le calcul
    
    Returns:
        Liste triée par coût (moins cher en premier)
    """
    comparisons = []
    
    for model, pricing in MODEL_PRICING.items():
        cost = pricing.estimate_cost(input_tokens, output_tokens)
        comparisons.append({
            "model": model.value,
            "cost": cost,
            "cost_display": f"${cost:.4f}",
            "input_price": f"${pricing.input_price}/M",
            "output_price": f"${pricing.output_price}/M",
            "context": f"{pricing.context_window // 1000}K",
            "tier": _get_model_tier(model),
        })
    
    return sorted(comparisons, key=lambda x: x["cost"])


def _get_model_tier(model: TargetModel) -> str:
    """Retourne le tier de performance du modèle."""
    premium = [TargetModel.CLAUDE_OPUS_4_5, TargetModel.GPT_5_PRO, TargetModel.GPT_5_1]
    mid = [TargetModel.CLAUDE_SONNET_4_5, TargetModel.GEMINI_3_PRO]
    
    if model in premium:
        return "🔥 Premium"
    elif model in mid:
        return "⚡ Performant"
    else:
        return "💰 Économique"


def get_recommendation(task_type: str) -> dict:
    """
    Recommande un modèle selon le type de tâche.
    
    Args:
        task_type: "code", "chat", "analysis", "creative", "budget"
    
    Returns:
        Dictionnaire avec recommandation et alternatives
    """
    recommendations = {
        "code": {
            "best": "claude_opus_4.5",
            "balanced": "claude_sonnet_4.5",
            "budget": "gpt_5.1_mini",
            "reason": "Opus 4.5 excelle en code complexe, Sonnet pour le quotidien"
        },
        "chat": {
            "best": "gpt_5.1",
            "balanced": "gemini_3_flash",
            "budget": "claude_haiku_4.5",
            "reason": "GPT-5.1 est plus naturel, Flash/Haiku pour le volume"
        },
        "analysis": {
            "best": "gemini_3_pro",
            "balanced": "claude_sonnet_4.5",
            "budget": "gpt_5.1_mini",
            "reason": "Gemini 3 Pro avec 1M tokens pour les gros documents"
        },
        "creative": {
            "best": "gpt_5.1",
            "balanced": "claude_sonnet_4.5",
            "budget": "gemini_3_flash",
            "reason": "GPT-5.1 moins sycophantique, plus créatif"
        },
        "budget": {
            "best": "gpt_5.1_mini",
            "balanced": "claude_haiku_4.5",
            "budget": "gemini_3_flash",
            "reason": "GPT-5.1 Mini offre le meilleur rapport qualité/prix"
        },
    }
    
    return recommendations.get(task_type, recommendations["budget"])


def format_comparison_table() -> str:
    """Génère un tableau de comparaison formaté."""
    comparisons = compare_models()
    
    lines = [
        "┌──────────────────────┬───────────────┬───────────────┬──────────┬─────────────┐",
        "│ Modèle               │ Input/M       │ Output/M      │ Contexte │ Tier        │",
        "├──────────────────────┼───────────────┼───────────────┼──────────┼─────────────┤",
    ]
    
    for c in comparisons:
        model = c["model"][:20].ljust(20)
        input_p = c["input_price"].ljust(13)
        output_p = c["output_price"].ljust(13)
        context = c["context"].ljust(8)
        tier = c["tier"].ljust(11)
        lines.append(f"│ {model} │ {input_p} │ {output_p} │ {context} │ {tier} │")
    
    lines.append("└──────────────────────┴───────────────┴───────────────┴──────────┴─────────────┘")
    
    return "\n".join(lines)
