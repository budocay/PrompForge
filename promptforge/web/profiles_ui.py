"""
Profile selection UI helpers for PromptForge web interface.
Version 2.0 - Décembre 2025

IMPORTANT: Tous les profils utilisent maintenant le format XML !
- Claude: XML natif (entraîné avec XML)
- GPT-5/5.1: XML recommandé (OpenAI Cookbook 2025)
- Gemini 3: XML/tags recommandés
- Mistral: XML supporté
"""

# Profile descriptions for the UI (December 2025 - XML Universal - UPDATED PRICING)
PROFILE_DESCRIPTIONS = {
    # Claude (Anthropic) - XML natif
    "claude_opus_4.5": "🟣 Claude Opus 4.5 — Code/Agents complexes [XML] ($5/$25)",
    "claude_sonnet_4.5": "🟣 Claude Sonnet 4.5 — Best coding model [XML] ($3/$15)",
    "claude_haiku_4.5": "🟣 Claude Haiku 4.5 — Rapide [XML] ($1/$5)",  # CORRIGÉ

    # GPT (OpenAI) - XML recommandé depuis 2025!
    "gpt_5.1": "🟢 GPT-5.1 — Flagship steerable [XML] ($1.25/$10)",
    "gpt_5.1_mini": "🟢 GPT-5.1 Mini — Économique [XML] ($0.25/$2)",
    "gpt_5_pro": "🟢 GPT-5/o3 — Deep reasoning [XML] ($2/$8)",  # CORRIGÉ

    # Gemini (Google) - XML/tags
    "gemini_3_pro": "🔵 Gemini 3 Pro — 1M tokens! [XML] ($2/$12)",
    "gemini_3_flash": "🔵 Gemini 2.5 Flash — Rapide 1M [XML] ($0.30/$2.50)",  # CORRIGÉ

    # Universal
    "universel": "⚪ Universel — Compatible tous modèles [XML]",
}


def get_profile_choices() -> list[str]:
    """Return list of profiles for dropdown."""
    return list(PROFILE_DESCRIPTIONS.keys())


def get_profile_label(profile_name: str) -> str:
    """Return label for a profile."""
    return PROFILE_DESCRIPTIONS.get(profile_name, profile_name)


def get_profile_info(profile_name: str) -> str:
    """Return detailed info about a profile."""
    profile_info = {
        "claude_opus_4.5": """**🟣 Claude Opus 4.5** — Format: XML natif (Nov 2025)
- Meilleur pour: Code complexe, agents, architecture, tâches long-horizon
- SWE-bench Multilingual: Leader sur 7/8 langages
- Paramètre "effort" (low/medium/high) pour contrôler tokens
- Balises: <task>, <context>, <thinking>, <instructions>, <constraints>, <output_format>
- Contexte: 200K tokens
- Prix: $5/M input, $25/M output""",

        "claude_sonnet_4.5": """**🟣 Claude Sonnet 4.5** — Format: XML natif (Sep 2025)
- Meilleur pour: Coding au quotidien, best coding model
- SWE-bench Verified: 72.7% (state-of-the-art)
- OSWorld computer use: 61.4% (leader)
- Balises: <task>, <context>, <instructions>, <constraints>, <output_format>
- Contexte: 200K (standard) ou 1M tokens (beta)
- Prix: $3/M input, $15/M output""",

        "claude_haiku_4.5": """**🟣 Claude Haiku 4.5** — Format: XML natif
- Meilleur pour: Tâches rapides, volume élevé
- Performance proche de Sonnet 4 à prix réduit
- Ultra-rapide, prompt court recommandé
- Balises: <task>, <context>, <instructions>, <output_format>
- Contexte: 200K tokens
- Prix: $1/M input, $5/M output""",

        "gpt_5.1": """**🟢 GPT-5.1** — Format: XML (recommandé par OpenAI!)
- Meilleur pour: Usage général, steerable
- -45% hallucinations vs GPT-4
- Instruction following chirurgical
- Balises: <task>, <context>, <instructions>, <constraints>, <output_format>
- Contexte: 272K tokens
- Prix: $1.25/M input, $10/M output""",

        "gpt_5.1_mini": """**🟢 GPT-5.1 Mini** — Format: XML
- Meilleur pour: Budget, volume élevé
- Rapide et très économique
- Aussi steerable que GPT-5.1
- Balises courtes: <task>, <context>, <instructions>, <output_format>
- Contexte: 200K tokens
- Prix: $0.25/M input, $2/M output""",

        "gpt_5_pro": """**🟢 GPT-5 / o3** — Format: XML avec <thinking>
- Meilleur pour: Raisonnement complexe, math, architecture
- Deep thinking pour problèmes multi-étapes
- Modèle de reasoning (série o)
- Balises: <task>, <context>, <thinking>, <instructions>, <constraints>, <output_format>
- Contexte: 200K tokens
- Prix: ~$2/M input, ~$8/M output""",

        "gemini_3_pro": """**🔵 Gemini 3 Pro** — Format: XML/tags (Preview)
- Meilleur pour: Documents longs, codebases entières, vibe-coding
- Le plus puissant de Google pour multimodal
- Contexte: 1M tokens! (750K mots)
- Balises: <task>, <context>, <instructions>, <constraints>, <output_format>
- Prix: $2/M input, $12/M output (≤200K), $4/$18 (>200K)""",

        "gemini_3_flash": """**🔵 Gemini 2.5 Flash** — Format: XML/tags
- Meilleur pour: Tâches rapides avec grand contexte
- Hybrid reasoning avec thinking budgets
- Contexte: 1M tokens
- Balises courtes: <task>, <context>, <instructions>, <output_format>
- Prix: $0.30/M input, $2.50/M output""",

        "universel": """**⚪ Universel** — Format: XML standard
- Compatible avec tous les LLM modernes (Claude, GPT, Gemini, Mistral, Llama)
- Balises universelles: <task>, <context>, <instructions>, <constraints>, <output_format>
- Idéal si vous ne savez pas encore quel modèle utiliser
- Fonctionne partout!"""
    }

    return profile_info.get(profile_name, f"**{profile_name}**\nProfil de reformatage XML standard.")
