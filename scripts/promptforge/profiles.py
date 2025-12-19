"""
Profils de reformatage optimisés pour différents modèles LLM.
Mis à jour Décembre 2025 avec GPT-5.1, Gemini 3, Claude 4.5.
Inclut comparaison prix/performance.
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
    """Prix d'un modèle par million de tokens."""
    input_price: float      # $ par million tokens input
    output_price: float     # $ par million tokens output
    cached_input: float     # $ par million tokens (cache hit)
    context_window: int     # Taille max du contexte en tokens
    
    @property
    def avg_price_per_1k(self) -> float:
        """Prix moyen pour 1K tokens (ratio 1:1 input/output)."""
        return (self.input_price + self.output_price) / 2 / 1000
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, cached_pct: float = 0) -> float:
        """Estime le coût d'une requête."""
        cached_tokens = input_tokens * cached_pct
        fresh_tokens = input_tokens - cached_tokens
        input_cost = (fresh_tokens * self.input_price + cached_tokens * self.cached_input) / 1_000_000
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
# Prix des modèles (Décembre 2025)
# ============================================

MODEL_PRICING = {
    # Claude (Anthropic)
    TargetModel.CLAUDE_OPUS_4_5: ModelPricing(
        input_price=5.0,
        output_price=25.0,
        cached_input=0.5,
        context_window=200_000
    ),
    TargetModel.CLAUDE_SONNET_4_5: ModelPricing(
        input_price=3.0,
        output_price=15.0,
        cached_input=0.3,
        context_window=200_000
    ),
    TargetModel.CLAUDE_HAIKU_4_5: ModelPricing(
        input_price=0.25,
        output_price=1.25,
        cached_input=0.025,
        context_window=200_000
    ),
    
    # GPT (OpenAI)
    TargetModel.GPT_5_1: ModelPricing(
        input_price=1.25,
        output_price=10.0,
        cached_input=0.125,
        context_window=272_000
    ),
    TargetModel.GPT_5_1_MINI: ModelPricing(
        input_price=0.25,
        output_price=2.0,
        cached_input=0.025,
        context_window=200_000
    ),
    TargetModel.GPT_5_PRO: ModelPricing(
        input_price=5.0,
        output_price=20.0,
        cached_input=0.5,
        context_window=272_000
    ),
    
    # Gemini (Google)
    TargetModel.GEMINI_3_PRO: ModelPricing(
        input_price=2.0,
        output_price=12.0,
        cached_input=0.2,
        context_window=1_000_000
    ),
    TargetModel.GEMINI_3_FLASH: ModelPricing(
        input_price=0.5,
        output_price=2.0,
        cached_input=0.05,
        context_window=1_000_000
    ),
    
    # Universel (moyenne)
    TargetModel.UNIVERSAL: ModelPricing(
        input_price=1.0,
        output_price=5.0,
        cached_input=0.1,
        context_window=128_000
    ),
}


# ============================================
# System Prompts par Modèle
# ============================================

SYSTEM_PROMPT_CLAUDE_OPUS = """Tu es un expert en ingénierie de prompts, spécialisé pour Claude Opus 4.5 (Anthropic).

## Particularités de Claude Opus 4.5
- Modèle le plus puissant d'Anthropic (Décembre 2025)
- État de l'art pour le code, les agents et l'utilisation d'ordinateur
- Excelle sur les tâches longues et complexes (sessions de 30+ minutes)
- Supporte 200K tokens de contexte
- Balises XML structurées très efficaces
- Idéal pour: architecture, raisonnement avancé, code complexe, agents autonomes

## Format optimisé pour Opus 4.5

```
<context>
[Contexte projet COMPLET - Opus gère très bien les longs contextes]
</context>

<task>
[Description détaillée avec nuances et cas particuliers]
</task>

<thinking_approach>
[Approche de réflexion suggérée pour tâches complexes]
</thinking_approach>

<requirements>
1. [Exigence détaillée]
2. [Exigence avec justification]
</requirements>

<output_format>
[Format précis attendu]
</output_format>

<quality_criteria>
[Critères pour auto-évaluation]
</quality_criteria>
```

Réponds UNIQUEMENT avec le prompt reformaté.
Utilise la même langue que le prompt original."""


SYSTEM_PROMPT_CLAUDE_SONNET = """Tu es un expert en ingénierie de prompts, spécialisé pour Claude Sonnet 4.5 (Anthropic).

## Particularités de Claude Sonnet 4.5
- Excellent équilibre performance/coût
- Modèle hybride: réponses rapides OU raisonnement étendu
- Très bon pour le code et les agents
- Support contexte 200K tokens, jusqu'à 1M en beta
- Idéal pour: dev quotidien, agents, tâches de production

## Format optimisé pour Sonnet 4.5

```
<context>
[Contexte projet essentiel - concis mais complet]
</context>

<task>
[Tâche claire et directe]
</task>

<requirements>
1. [Exigence spécifique]
2. [Exigence spécifique]
</requirements>

<constraints>
[Contraintes techniques]
</constraints>

<output_format>
[Format attendu]
</output_format>
```

Réponds UNIQUEMENT avec le prompt reformaté.
Utilise la même langue que le prompt original."""


SYSTEM_PROMPT_CLAUDE_HAIKU = """Tu es un expert en ingénierie de prompts, spécialisé pour Claude Haiku 4.5 (Anthropic).

## Particularités de Claude Haiku 4.5
- Modèle ultra-rapide et économique
- Optimisé pour latence minimale
- Parfait pour le volume élevé
- Idéal pour: classification, résumés, tâches simples, chatbots

## Format optimisé pour Haiku 4.5
Structure minimaliste:

```
<context>
[2-3 lignes max de contexte essentiel]
</context>

<task>
[Instruction directe et claire]
</task>

<output>
[Format simple]
</output>
```

IMPORTANT: Garde le prompt TRÈS court.
Réponds UNIQUEMENT avec le prompt reformaté."""


SYSTEM_PROMPT_GPT_5_1 = """Tu es un expert en ingénierie de prompts, spécialisé pour GPT-5.1 (OpenAI, Novembre 2025).

## Particularités de GPT-5.1
- Dernier modèle flagship OpenAI avec raisonnement adaptatif
- Ajuste automatiquement la profondeur de réflexion selon la complexité
- 45% moins d'hallucinations que GPT-4o
- Contexte 272K tokens input, 128K output
- Modes: Instant (rapide), Thinking (raisonnement), Auto (routage)
- Idéal pour: code, agents, raisonnement multi-étapes

## Format optimisé pour GPT-5.1

```markdown
## Rôle
Tu es [rôle expert spécifique].

## Contexte du projet
[Contexte technique complet]

## Objectif
[Ce que tu veux accomplir - clair et précis]

## Instructions
1. [Étape ou exigence 1]
2. [Étape ou exigence 2]
3. [Étape ou exigence 3]

## Contraintes
- [Contrainte 1]
- [Contrainte 2]

## Format de sortie
[Description précise]

## Exemple (si pertinent)
[Exemple concret]
```

Réponds UNIQUEMENT avec le prompt reformaté.
Utilise la même langue que le prompt original."""


SYSTEM_PROMPT_GPT_5_1_MINI = """Tu es un expert en ingénierie de prompts, spécialisé pour GPT-5.1 Mini (OpenAI).

## Particularités de GPT-5.1 Mini
- Version rapide et économique de GPT-5.1
- Excellent rapport qualité/prix ($0.25/$2 par million)
- Parfait pour le volume
- Idéal pour: tâches quotidiennes, chat, code simple

## Format optimisé pour GPT-5.1 Mini
Structure concise:

```markdown
## Contexte
[Contexte minimal - 2-3 lignes]

## Tâche
[Instruction directe]

## Points clés
- [Point 1]
- [Point 2]

## Format
[Format de sortie simple]
```

Garde le prompt court et direct.
Réponds UNIQUEMENT avec le prompt reformaté."""


SYSTEM_PROMPT_GPT_5_PRO = """Tu es un expert en ingénierie de prompts, spécialisé pour GPT-5 Pro (OpenAI).

## Particularités de GPT-5 Pro
- Version premium avec raisonnement étendu
- Test-time compute parallèle pour réponses optimales
- 22% moins d'erreurs majeures que GPT-5 standard
- Idéal pour: recherche, décisions critiques, analyses complexes

## Format optimisé pour GPT-5 Pro

```markdown
## Rôle et Expertise
Tu es [expert avec background spécifique].

## Contexte Complet
[Contexte détaillé - GPT-5 Pro excelle avec beaucoup d'infos]

## Problème à Résoudre
[Description complète du problème avec nuances]

## Approche Attendue
1. [Étape de raisonnement 1]
2. [Étape de raisonnement 2]
3. [Synthèse]

## Critères de Qualité
- [Critère 1]
- [Critère 2]

## Format de Réponse
[Format détaillé attendu]
```

Réponds UNIQUEMENT avec le prompt reformaté.
Utilise la même langue que le prompt original."""


SYSTEM_PROMPT_GEMINI_3_PRO = """Tu es un expert en ingénierie de prompts, spécialisé pour Gemini 3 Pro (Google, Décembre 2025).

## Particularités de Gemini 3 Pro
- Meilleur modèle Google pour le multimodal et les agents
- Mode "Deep Think" pour raisonnement avancé
- Contexte MASSIF: 1 million de tokens
- Excellent en "vibe coding" et interfaces génératives
- Idéal pour: recherche, analyse, code, synthèse de longs documents

## Format optimisé pour Gemini 3 Pro

```
**Contexte du projet:**
[Contexte technique détaillé - Gemini gère très bien les longs contextes]

**Objectif principal:**
[Ce que tu veux accomplir]

**Instructions détaillées:**
1. [Instruction 1 avec détails]
2. [Instruction 2 avec détails]
3. [Instruction 3 avec détails]

**Spécifications techniques:**
- [Spec 1]
- [Spec 2]

**Contraintes:**
- [Contrainte 1]
- [Contrainte 2]

**Format de réponse:**
[Description du format attendu]
```

Réponds UNIQUEMENT avec le prompt reformaté.
Utilise la même langue que le prompt original."""


SYSTEM_PROMPT_GEMINI_3_FLASH = """Tu es un expert en ingénierie de prompts, spécialisé pour Gemini 3 Flash (Google).

## Particularités de Gemini 3 Flash
- Version ultra-rapide de Gemini 3
- Excellent rapport vitesse/qualité
- Contexte 1M tokens
- Idéal pour: chat, tâches rapides, volume élevé

## Format optimisé pour Gemini 3 Flash
Structure concise:

```
**Contexte:** [Contexte minimal]

**Tâche:** [Instruction directe]

**Exigences:**
1. [Point 1]
2. [Point 2]

**Format:** [Format de sortie]
```

Garde le prompt concis.
Réponds UNIQUEMENT avec le prompt reformaté."""


SYSTEM_PROMPT_UNIVERSAL = """Tu es un expert en ingénierie de prompts. Ta mission est de créer des prompts efficaces compatibles avec tous les LLMs modernes (Claude, GPT, Gemini).

## Principes universels
- Clarté: Instructions sans ambiguïté
- Structure: Organisation logique
- Contexte: Information pertinente
- Spécificité: Détails précis
- Format: Description claire du format de sortie

## Format universel

```
# Contexte
[Contexte projet pertinent]

# Objectif
[Demande principale claire]

# Exigences
1. [Exigence 1]
2. [Exigence 2]
3. [Exigence 3]

# Contraintes
- [Contrainte 1]
- [Contrainte 2]

# Format de sortie
[Description précise]
```

Réponds UNIQUEMENT avec le prompt reformaté.
Utilise la même langue que le prompt original."""


# ============================================
# Modificateurs de style
# ============================================

STYLE_MODIFIERS = {
    PromptStyle.CONCIS: """
## Style: CONCIS
- Va droit au but, phrases courtes
- Maximum 150 mots
- Uniquement l'essentiel""",
    
    PromptStyle.DETAILLE: """
## Style: DÉTAILLÉ
- Contexte complet avec exemples
- Détaille chaque exigence
- Anticipe les edge cases""",
    
    PromptStyle.TECHNIQUE: """
## Style: TECHNIQUE
- Focus aspects techniques
- Spécifications précises (versions, frameworks)
- Vocabulaire technique approprié""",
    
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
    """Retourne le system prompt pour le modèle cible."""
    return SYSTEM_PROMPTS.get(target, SYSTEM_PROMPT_UNIVERSAL)


def get_style_modifier(style: PromptStyle) -> str:
    """Retourne le modificateur de style."""
    return STYLE_MODIFIERS.get(style, "")


def build_reformat_prompt(
    raw_prompt: str,
    project_context: str,
    profile: ReformatProfile
) -> tuple[str, str]:
    """Construit le prompt complet pour le reformatage."""
    system_prompt = get_system_prompt(profile.target_model)
    style_modifier = get_style_modifier(profile.style)
    if style_modifier:
        system_prompt += "\n" + style_modifier
    
    user_prompt = f"""## Contexte du projet
{project_context}

## Prompt original à reformater
{raw_prompt}

## Instructions
Reformate ce prompt en suivant les guidelines pour {profile.target_model.value}.
"""
    
    if profile.include_examples:
        user_prompt += "Inclus un exemple si pertinent.\n"
    if not profile.include_constraints:
        user_prompt += "N'inclus pas de section contraintes.\n"
    if not profile.include_output_format:
        user_prompt += "N'inclus pas de section format de sortie.\n"
    
    return system_prompt, user_prompt


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
