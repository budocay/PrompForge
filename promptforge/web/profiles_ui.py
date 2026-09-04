"""
Profile selection UI helpers for PromptForge web interface.

Aucun tarif ni aucune fenetre de contexte n'est ecrit en dur dans ce module.
Ces valeurs sont composees au rendu depuis `promptforge.profiles.MODEL_PRICING`,
seule source du domaine, qui porte desormais l'URL de la source et la date de
verification de chaque entree (F-022, DEC-004, DEC-005, DEC-009).

Motif : avant F-022, trois tarifs et une fenetre de contexte divergeaient entre
le domaine et l'affichage, et un libelle avait ete corrige a la main sans que la
source le soit. Une valeur affichee ne se recopie plus, elle se compose.

IMPORTANT: Tous les profils utilisent le format XML dans les libelles ci-dessous.
La verification de cette affirmation profil par profil releve de F-029.
"""

from ..profiles import MODEL_PRICING, PRESET_PROFILES, TargetModel

# Description courte de chaque profil, SANS tarif ni fenetre de contexte :
# ces deux valeurs sont ajoutees au rendu par `get_profile_label()`.
# Les cles doivent rester alignees sur celles de `PRESET_PROFILES`
# (verrou : tests/test_game_changer.py::TestProfilesUiDomainParity).
PROFILE_DESCRIPTIONS = {
    # Claude (Anthropic) - XML natif
    "claude_opus_4.5": "🟣 Claude Opus 4.5 — Code/Agents complexes [XML]",
    "claude_sonnet_4.5": "🟣 Claude Sonnet 4.5 — Best coding model [XML]",
    "claude_haiku_4.5": "🟣 Claude Haiku 4.5 — Rapide [XML]",

    # GPT (OpenAI) - XML recommandé depuis 2025!
    "gpt_5.1": "🟢 GPT-5.1 — Flagship steerable [XML]",
    "gpt_5.1_mini": "🟢 GPT-5.1 Mini — Économique [XML]",
    "gpt_5_pro": "🟢 GPT-5/o3 — Deep reasoning [XML]",

    # Gemini (Google) - XML/tags
    "gemini_3_pro": "🔵 Gemini 3 Pro — Documents longs [XML]",
    "gemini_3_flash": "🔵 Gemini 2.5 Flash — Rapide [XML]",

    # Universal
    "universel": "⚪ Universel — Compatible tous modèles [XML]",
}


# Contenu statique du panneau de detail : ni tarif, ni fenetre de contexte.
# Ces deux lignes sont ajoutees au rendu depuis MODEL_PRICING.
PROFILE_DETAILS = {
    "claude_opus_4.5": {
        "title": "**🟣 Claude Opus 4.5** — Format: XML natif (Nov 2025)",
        "bullets": [
            "Meilleur pour: Code complexe, agents, architecture, tâches long-horizon",
            "SWE-bench Multilingual: Leader sur 7/8 langages",
            'Paramètre "effort" (low/medium/high) pour contrôler tokens',
            "Balises: <task>, <context>, <thinking>, <instructions>, <constraints>, <output_format>",
        ],
    },
    "claude_sonnet_4.5": {
        "title": "**🟣 Claude Sonnet 4.5** — Format: XML natif (Sep 2025)",
        "bullets": [
            "Meilleur pour: Coding au quotidien, best coding model",
            "SWE-bench Verified: 72.7% (state-of-the-art)",
            "OSWorld computer use: 61.4% (leader)",
            "Balises: <task>, <context>, <instructions>, <constraints>, <output_format>",
        ],
    },
    "claude_haiku_4.5": {
        "title": "**🟣 Claude Haiku 4.5** — Format: XML natif",
        "bullets": [
            "Meilleur pour: Tâches rapides, volume élevé",
            "Performance proche de Sonnet 4 à prix réduit",
            "Ultra-rapide, prompt court recommandé",
            "Balises: <task>, <context>, <instructions>, <output_format>",
        ],
    },
    "gpt_5.1": {
        "title": "**🟢 GPT-5.1** — Format: XML (recommandé par OpenAI!)",
        "bullets": [
            "Meilleur pour: Usage général, steerable",
            "-45% hallucinations vs GPT-4",
            "Instruction following chirurgical",
            "Balises: <task>, <context>, <instructions>, <constraints>, <output_format>",
        ],
    },
    "gpt_5.1_mini": {
        "title": "**🟢 GPT-5.1 Mini** — Format: XML",
        "bullets": [
            "Meilleur pour: Budget, volume élevé",
            "Rapide et très économique",
            "Aussi steerable que GPT-5.1",
            "Balises courtes: <task>, <context>, <instructions>, <output_format>",
        ],
    },
    "gpt_5_pro": {
        "title": "**🟢 GPT-5 / o3** — Format: XML avec <thinking>",
        "bullets": [
            "Meilleur pour: Raisonnement complexe, math, architecture",
            "Deep thinking pour problèmes multi-étapes",
            "Modèle de reasoning (série o)",
            "Balises: <task>, <context>, <thinking>, <instructions>, <constraints>, <output_format>",
        ],
    },
    "gemini_3_pro": {
        "title": "**🔵 Gemini 3 Pro** — Format: XML/tags (Preview)",
        "bullets": [
            "Meilleur pour: Documents longs, codebases entières, vibe-coding",
            "Le plus puissant de Google pour multimodal",
            "Balises: <task>, <context>, <instructions>, <constraints>, <output_format>",
        ],
    },
    "gemini_3_flash": {
        "title": "**🔵 Gemini 2.5 Flash** — Format: XML/tags",
        "bullets": [
            "Meilleur pour: Tâches rapides avec grand contexte",
            "Hybrid reasoning avec thinking budgets",
            "Balises courtes: <task>, <context>, <instructions>, <output_format>",
        ],
    },
    "universel": {
        "title": "**⚪ Universel** — Format: XML standard",
        "bullets": [
            "Compatible avec tous les LLM modernes (Claude, GPT, Gemini, Mistral, Llama)",
            "Balises universelles: <task>, <context>, <instructions>, <constraints>, <output_format>",
            "Idéal si vous ne savez pas encore quel modèle utiliser",
            "Fonctionne partout!",
        ],
    },
}


def get_pricing_for_profile(profile_name: str):
    """Retourne le `ModelPricing` du profil, ou None si le profil est inconnu.

    Passe par `PRESET_PROFILES` et non par `get_profile()`, dont le repli muet
    sur « universel » servirait le tarif d'un autre modèle sans le dire
    (D-029, corrigé par F-029).
    """
    profile = PRESET_PROFILES.get(profile_name)
    if profile is None:
        return None
    return profile.pricing or MODEL_PRICING.get(profile.target_model)


def _shows_pricing(profile_name: str) -> bool:
    """Le profil universel ne désigne aucun modèle réel : pas de tarif affiché.

    Son entrée de `MODEL_PRICING` est une moyenne synthétique (D-032) ;
    l'afficher reviendrait à annoncer le tarif d'un modèle qui n'existe pas.
    """
    profile = PRESET_PROFILES.get(profile_name)
    return profile is not None and profile.target_model is not TargetModel.UNIVERSAL


def _money(value: float) -> str:
    """Formate un montant sans zéro décimal inutile : 5.0 -> '5', 1.25 -> '1.25'."""
    return f"{value:g}"


def format_price_short(pricing) -> str:
    """Tarif compact « $5/$25 » composé depuis le domaine. Vide si inconnu."""
    if pricing is None:
        return ""
    return f"${_money(pricing.input_price)}/${_money(pricing.output_price)}"


def format_context_window(pricing) -> str:
    """Fenêtre de contexte lisible (« 200K », « 1M ») composée depuis le domaine."""
    if pricing is None:
        return ""
    window = pricing.context_window
    if window >= 1_000_000 and window % 1_000_000 == 0:
        return f"{window // 1_000_000}M"
    return f"{window // 1_000}K"


def format_pricing_source(pricing) -> str:
    """Mention de provenance du tarif, telle que portée par le domaine.

    Une source vide n'est pas masquée : elle est signalée comme non vérifiée
    (D-032, résorption prévue par F-028).
    """
    if pricing is None:
        return ""
    if not pricing.source_url:
        return "⚠️ Tarif non confirmé par une source officielle"
    if pricing.verified_on:
        return f"Source: {pricing.source_url} (vérifié le {pricing.verified_on})"
    return f"Source: {pricing.source_url}"


def get_profile_choices() -> list[str]:
    """Return list of profiles for dropdown."""
    return list(PROFILE_DESCRIPTIONS.keys())


def get_profile_label(profile_name: str) -> str:
    """Return label for a profile, tarif composé depuis MODEL_PRICING."""
    description = PROFILE_DESCRIPTIONS.get(profile_name)
    if description is None:
        return profile_name
    if not _shows_pricing(profile_name):
        return description
    price = format_price_short(get_pricing_for_profile(profile_name))
    return f"{description} ({price})" if price else description


def get_profile_info(profile_name: str) -> str:
    """Return detailed info about a profile.

    Le tarif, la fenêtre de contexte et la provenance sont lus dans
    MODEL_PRICING au moment du rendu : aucune copie n'est conservée ici.
    """
    details = PROFILE_DETAILS.get(profile_name)
    if details is None:
        return f"**{profile_name}**\nProfil de reformatage XML standard."

    lines = [details["title"]]
    lines.extend(f"- {bullet}" for bullet in details["bullets"])

    pricing = get_pricing_for_profile(profile_name)
    if pricing is not None and _shows_pricing(profile_name):
        lines.append(f"- Contexte: {format_context_window(pricing)} tokens")
        lines.append(
            f"- Prix: ${_money(pricing.input_price)}/M input, "
            f"${_money(pricing.output_price)}/M output"
        )
        lines.append(f"- {format_pricing_source(pricing)}")

    return "\n".join(lines)
