"""
Model recommendations and benchmarks for PromptForge web interface.
Generates recommendations based on domain detection and model capabilities.
"""

from ..tokens import estimate_tokens
from ..profiles import MODEL_PRICING, TargetModel, compare_models
from .analysis import detect_domain, detect_task_type

# =============================================================================
# BENCHMARK SOURCES (December 2025)
# =============================================================================
BENCHMARK_SOURCES = {
    'anthropic': {
        'url': 'https://www.anthropic.com/news/claude-opus-4-5',
        'name': 'Anthropic - Claude Opus 4.5 Announcement (Nov 2025)',
    },
    'openai': {
        'url': 'https://openai.com/index/introducing-gpt-5/',
        'name': 'OpenAI - Introducing GPT-5 (Aug 2025)',
    },
    'google': {
        'url': 'https://blog.google/products/gemini/gemini-3/',
        'name': 'Google - Gemini 3 Announcement (Nov 2025)',
    },
    'swe_bench': {
        'url': 'https://www.swebench.com/',
        'name': 'SWE-bench Verified - Real-world Software Engineering',
    },
    'gpqa_diamond': {
        'url': 'https://arxiv.org/abs/2311.12022',
        'name': 'GPQA Diamond - Graduate-level Science Questions',
    },
    'healthbench_hard': {
        'url': 'https://arxiv.org/abs/2505.08775',
        'name': 'HealthBench Hard - Medical AI Evaluation',
    },
    'aime_2025': {
        'url': 'https://artofproblemsolving.com/wiki/index.php/AIME',
        'name': 'AIME 2025 - American Invitational Mathematics Exam',
    },
    'image_generation': {
        'url': 'https://skywork.ai/blog/comparison/',
        'name': 'AI Image Generation Comparison 2025',
    },
    'midjourney': {
        'url': 'https://docs.midjourney.com/',
        'name': 'Midjourney V7',
        'source_review': 'https://www.tomsguide.com/ai/midjourney-version-7',
    },
    'flux': {
        'url': 'https://bfl.ai/',
        'name': 'FLUX.2 (Black Forest Labs)',
        'source_review': 'https://venturebeat.com/ai/black-forest-labs-launches-flux-2/',
    },
    'ideogram': {
        'url': 'https://ideogram.ai/',
        'name': 'Ideogram 3.0',
        'source_review': 'https://tech-now.io/en/blogs/ideogram-3-0-review-2025/',
    },
}

# Ollama models info for local reformatting
OLLAMA_MODELS_INFO = {
    # Premium (20GB+ VRAM)
    'qwen3:32b': {'size': '32B', 'reformat_score': 98, 'tier': 'premium', 'note': 'Excellent suivi XML'},
    'qwen3:30b-a3b': {'size': '30B MoE', 'reformat_score': 97, 'tier': 'premium', 'note': 'MoE optimal'},
    'deepseek-r1:32b': {'size': '32B', 'reformat_score': 97, 'tier': 'premium', 'note': 'Excellent raisonnement'},
    'llama3.1:70b': {'size': '70B', 'reformat_score': 99, 'tier': 'premium', 'note': 'Parfait'},

    # Optimal (12GB+ VRAM)
    'qwen3:14b': {'size': '14B', 'reformat_score': 92, 'tier': 'optimal', 'note': 'Recommandé pour qualité XML'},
    'qwen2.5:14b': {'size': '14B', 'reformat_score': 90, 'tier': 'optimal', 'note': 'Stable et fiable'},
    'deepseek-r1:14b': {'size': '14B', 'reformat_score': 91, 'tier': 'optimal', 'note': 'Bon raisonnement'},

    # Light (8GB VRAM)
    'qwen3:8b': {'size': '8B', 'reformat_score': 85, 'tier': 'recommended', 'note': 'RECOMMANDÉ - Meilleur raisonnement ⭐'},
    'llama3.1:8b': {'size': '8B', 'reformat_score': 88, 'tier': 'light', 'note': 'Bon format natif'},
    'mistral:7b': {'size': '7B', 'reformat_score': 80, 'tier': 'light', 'note': 'Alternative légère'},

    # CPU (4-8GB RAM)
    'phi4-mini': {'size': '3.8B', 'reformat_score': 75, 'tier': 'cpu', 'note': 'Microsoft - excellent sur CPU'},
    'phi3:mini': {'size': '3.8B', 'reformat_score': 72, 'tier': 'cpu', 'note': 'Microsoft - léger'},
    'gemma3n:e4b': {'size': '4B', 'reformat_score': 70, 'tier': 'cpu', 'note': 'Google - edge/mobile'},
    'qwen3:4b': {'size': '4B', 'reformat_score': 68, 'tier': 'cpu', 'note': 'Qwen - suivi XML limité'},
}

# Domain expertise scores by model
DOMAIN_EXPERTISE = {
    TargetModel.CLAUDE_OPUS_4_5: {
        'code': (98, "SWE-bench 80.9% (leader)"),
        'legal': (92, "ASL-3 safety + 200K contexte"),
        'finance': (90, "ASL-3 safety filters"),
        'medical': (75, "Prudent, HealthBench < GPT-5"),
        'creative': (82, "Style structuré"),
        'research': (88, "200K contexte"),
        'data': (85, "Analyse structurée"),
        'math': (85, "AIME ~85%"),
        'image': (60, "Prompts seulement"),
        'document': (92, "200K tokens"),
        'general': (88, "Polyvalent"),
        # Nouveaux domaines métiers
        'seo': (85, "Analyse structurée, recommandations précises"),
        'marketing': (82, "Campagnes bien structurées"),
        'hr': (88, "Fiches de poste professionnelles"),
        'sales': (80, "Emails et pitchs structurés"),
        'product': (92, "PRD et specs excellentes"),
        'support': (85, "Réponses empathiques et complètes"),
    },
    TargetModel.CLAUDE_SONNET_4_5: {
        'code': (95, "SWE-bench 77.2%"),
        'legal': (88, "200K contexte"),
        'finance': (86, "Bon ratio Q/P"),
        'medical': (72, "Correct"),
        'creative': (80, "Style structuré"),
        'research': (85, "30h+ autonomie"),
        'data': (82, "Solide"),
        'math': (83, "AIME 87%"),
        'image': (58, "Prompts seulement"),
        'document': (88, "200K tokens"),
        'general': (85, "Meilleur Q/P Claude"),
        # Nouveaux domaines métiers
        'seo': (82, "Bon équilibre qualité/coût"),
        'marketing': (80, "Recommandé pour volume"),
        'hr': (85, "Bon pour recrutement"),
        'sales': (78, "Scripts et emails"),
        'product': (88, "Bon pour specs"),
        'support': (82, "Réponses rapides"),
    },
    TargetModel.CLAUDE_HAIKU_4_5: {
        'code': (70, "Prototypage rapide"),
        'legal': (65, "Résumés basiques"),
        'finance': (63, "Simple"),
        'medical': (55, "Non recommandé"),
        'creative': (68, "Basique"),
        'research': (60, "Superficielle"),
        'data': (65, "Extraction"),
        'math': (62, "Calculs simples"),
        'image': (50, "Basique"),
        'document': (65, "Courts uniquement"),
        'general': (68, "Ultra-rapide"),
        # Nouveaux domaines métiers
        'seo': (65, "Tâches simples uniquement"),
        'marketing': (68, "Volume élevé, qualité basique"),
        'hr': (62, "Templates simples"),
        'sales': (65, "Emails courts"),
        'product': (60, "User stories simples"),
        'support': (72, "Réponses rapides FAQ"),
    },
    TargetModel.GPT_5_1: {
        'code': (92, "SWE-bench 76.3%"),
        'legal': (85, "Bon"),
        'finance': (88, "-45% hallucinations"),
        'medical': (95, "HealthBench 46.2% SOTA"),
        'creative': (94, "Ton naturel"),
        'research': (90, "Deep Research"),
        'data': (88, "Multimodal"),
        'math': (96, "AIME 94.6%"),
        'image': (95, "DALL-E 3 intégré!"),
        'document': (82, "128K tokens"),
        'general': (93, "Polyvalent"),
        # Nouveaux domaines métiers
        'seo': (90, "Excellent pour keyword research"),
        'marketing': (94, "Top pour copywriting et ads"),
        'hr': (85, "Fiches de poste engageantes"),
        'sales': (92, "Excellent pour pitch et objections"),
        'product': (88, "Bon pour PRD"),
        'support': (90, "Ton naturel et empathique"),
    },
    TargetModel.GPT_5_1_MINI: {
        'code': (75, "Simple"),
        'legal': (68, "Basique"),
        'finance': (70, "Simple"),
        'medical': (72, "Questions simples"),
        'creative': (76, "Standard"),
        'research': (70, "Rapide"),
        'data': (72, "Simples"),
        'math': (78, "Intermédiaires"),
        'image': (70, "DALL-E disponible"),
        'document': (70, "Courts"),
        'general': (75, "Excellent Q/P"),
        # Nouveaux domaines métiers
        'seo': (72, "Basique"),
        'marketing': (78, "Bon rapport Q/P"),
        'hr': (70, "Templates basiques"),
        'sales': (75, "Emails simples"),
        'product': (70, "User stories"),
        'support': (78, "Réponses courtes"),
    },
    TargetModel.GPT_5_PRO: {
        'code': (90, "Extended thinking"),
        'legal': (88, "Raisonnement approfondi"),
        'finance': (92, "Modélisation complexe"),
        'medical': (96, "HealthBench SOTA++"),
        'creative': (85, "Créatif mais lent"),
        'research': (93, "Deep research"),
        'data': (90, "Multi-étapes"),
        'math': (100, "AIME 100% (tools)"),
        'image': (90, "DALL-E 3++"),
        'document': (85, "128K approfondi"),
        'general': (91, "Premium"),
        # Nouveaux domaines métiers
        'seo': (88, "Analyse approfondie"),
        'marketing': (85, "Stratégies complexes"),
        'hr': (90, "Process RH complets"),
        'sales': (88, "Négociations complexes"),
        'product': (92, "Roadmaps et stratégie"),
        'support': (85, "Cas complexes"),
    },
    TargetModel.GEMINI_3_PRO: {
        'code': (88, "SWE-bench 76.2%"),
        'legal': (92, "1M tokens!"),
        'finance': (85, "1M contexte"),
        'medical': (78, "Bon"),
        'creative': (83, "Interfaces créatives"),
        'research': (96, "GPQA 91.9% leader!"),
        'data': (94, "1M tokens"),
        'math': (95, "AIME 95-100%"),
        'image': (75, "Imagen 3 via API"),
        'document': (98, "🏆 1M tokens!"),
        'general': (89, "Long contexte"),
        # Nouveaux domaines métiers
        'seo': (85, "Analyse de grands sites"),
        'marketing': (82, "Analyse de campagnes"),
        'hr': (80, "Bon"),
        'sales': (78, "Standard"),
        'product': (85, "Contexte produit long"),
        'support': (80, "KB volumineuse"),
    },
    TargetModel.GEMINI_3_FLASH: {
        'code': (68, "Prototypage"),
        'legal': (65, "1M ctx"),
        'finance': (63, "Basique"),
        'medical': (58, "Non recommandé"),
        'creative': (72, "Rapide"),
        'research': (70, "Grand ctx"),
        'data': (75, "1M tokens"),
        'math': (70, "Basiques"),
        'image': (65, "Imagen via API"),
        'document': (85, "1M rapide"),
        'general': (70, "Économique"),
        # Nouveaux domaines métiers
        'seo': (68, "Tâches rapides"),
        'marketing': (70, "Volume"),
        'hr': (65, "Basique"),
        'sales': (65, "Emails courts"),
        'product': (68, "User stories simples"),
        'support': (72, "FAQ rapides"),
    },
    TargetModel.UNIVERSAL: {
        'code': (60, "Compatible tous"),
        'legal': (55, "Basique"),
        'finance': (55, "Basique"),
        'medical': (50, "Non recommandé"),
        'creative': (60, "Standard"),
        'research': (55, "Standard"),
        'data': (55, "Standard"),
        'math': (55, "Standard"),
        'image': (40, "Utiliser outils dédiés"),
        'document': (55, "Dépend du LLM"),
        'general': (58, "Fallback"),
        # Nouveaux domaines métiers
        'seo': (55, "Basique"),
        'marketing': (58, "Standard"),
        'hr': (55, "Standard"),
        'sales': (55, "Standard"),
        'product': (55, "Standard"),
        'support': (58, "Standard"),
    },
}

DOMAIN_LABELS = {
    'code': '💻 Code/Dev',
    'legal': '⚖️ Juridique',
    'medical': '🏥 Médical/Santé',
    'finance': '💹 Finance',
    'creative': '✨ Créatif',
    'research': '🔬 Recherche',
    'data': '📊 Data/Analytics',
    'math': '🔢 Mathématiques',
    'image': '🎨 Génération d\'Images',
    'document': '📄 Analyse de Documents',
    'general': '🔧 Général',
    'analysis': '📊 Analyse',
    'chat': '💬 Chat',
    # Nouveaux domaines métiers
    'seo': '🔍 SEO/Référencement',
    'marketing': '📢 Marketing Digital',
    'hr': '👥 RH/Recrutement',
    'sales': '💼 Commercial/Ventes',
    'product': '🎯 Product Management',
    'support': '🎧 Support Client',
}


def get_ollama_model_info(ollama_model: str) -> dict:
    """Get info about an Ollama model for reformatting."""
    if not ollama_model:
        return None

    model_lower = ollama_model.lower()

    # Exact match
    if model_lower in OLLAMA_MODELS_INFO:
        info = OLLAMA_MODELS_INFO[model_lower].copy()
        info['name'] = ollama_model
        return info

    # Partial match
    sorted_keys = sorted(OLLAMA_MODELS_INFO.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in model_lower or model_lower.split(':')[0] == key.split(':')[0]:
            info = OLLAMA_MODELS_INFO[key].copy()
            info['name'] = ollama_model
            return info

    # Estimate from name
    import re
    size_match = re.search(r'(\d+)b', model_lower)
    if size_match:
        size = int(size_match.group(1))
        if size >= 30:
            score, tier, note = 95, 'premium', 'Grand modèle'
        elif size >= 7:
            score, tier, note = 85, 'optimal', 'Taille idéale'
        else:
            score, tier, note = 70, 'minimal', 'Petit modèle'
    else:
        size = 0
        score, tier, note = 75, 'unknown', 'Non référencé'

    return {
        'name': ollama_model,
        'size': f"{size}B" if size else '?',
        'reformat_score': score,
        'tier': tier,
        'note': note
    }


def generate_recommendation(
    formatted_prompt: str,
    task_type: str,
    ollama_model: str = None,
    domain_override: str = None
) -> str:
    """
    Generate model recommendation based on domain detection.

    Args:
        formatted_prompt: The reformatted prompt
        task_type: Detected task type
        ollama_model: Ollama model used for reformatting
        domain_override: Force specific domain

    Returns:
        Markdown recommendation text
    """
    # Estimate tokens
    input_tokens = estimate_tokens(formatted_prompt)
    output_multiplier = {
        'code': 2.5, 'legal': 1.5, 'medical': 1.2, 'finance': 1.5,
        'creative': 2.0, 'research': 1.5, 'data': 1.5, 'math': 1.0,
        'analysis': 1.5, 'chat': 0.8, 'general': 1.5,
        'image': 0.5, 'document': 2.0,
    }
    output_tokens = int(input_tokens * output_multiplier.get(task_type, 1.5))

    # Detect domain
    domain = domain_override if domain_override else detect_domain(formatted_prompt)
    domain_display = DOMAIN_LABELS.get(domain, '🔧 Général')

    # Get Ollama model info
    ollama_info = get_ollama_model_info(ollama_model)

    # Calculate scores for all models
    all_models = []
    for model in TargetModel:
        pricing = MODEL_PRICING[model]
        cost = pricing.estimate_cost(input_tokens, output_tokens)

        expertise = DOMAIN_EXPERTISE[model]
        score, reason = expertise.get(domain, expertise['general'])

        value_score = score / (cost * 100 + 0.001)

        all_models.append({
            'model': model,
            'name': model.value,
            'cost': cost,
            'score': score,
            'reason': reason,
            'value': value_score,
            'context': f"{pricing.context_window // 1000}K"
        })

    all_models.sort(key=lambda x: x['score'], reverse=True)

    # Build recommendation
    lines = [
        f"### 🎯 Analyse pour ce prompt",
        f"**Domaine détecté:** {domain_display} | "
        f"**Tokens:** ~{input_tokens:,} input → ~{output_tokens:,} output\n",
    ]

    # Ollama section
    if ollama_info:
        lines.append("---")
        lines.append("### 🔧 Modèle de reformatage (local)\n")

        score = ollama_info['reformat_score']
        if score >= 85:
            score_icon, verdict = "🟢", "Excellent"
        elif score >= 70:
            score_icon, verdict = "🟡", "Suffisant"
        else:
            score_icon, verdict = "🟠", "Limite"

        tier_labels = {
            'premium': '🔥 Premium',
            'optimal': '✅ Optimal',
            'recommended': '⭐ Recommandé',
            'light': '💡 Léger',
            'cpu': '🖥️ CPU',
            'minimal': '⚠️ Minimal',
            'unknown': '❓ Inconnu'
        }

        lines.append(f"| Modèle | Taille | Pertinence | Tier | Coût |")
        lines.append(f"|--------|--------|------------|------|------|")
        lines.append(f"| **{ollama_info['name']}** | {ollama_info['size']} | {score_icon} {score}% ({verdict}) | {tier_labels.get(ollama_info['tier'], '❓')} | **$0** |")
        lines.append(f"\n📝 *{ollama_info['note']}*")

        cloud_cost = input_tokens * 0.000003 + output_tokens * 0.000015
        lines.append(f"\n💰 **Économie vs Cloud:** ${cloud_cost * 1000:.2f} économisés sur 1000 reformatages")

    # Cloud models section
    lines.append("\n---")
    lines.append(f"### 🏆 Modèle recommandé pour EXÉCUTER ce prompt ({domain_display})\n")
    lines.append("| # | Modèle | Pertinence | Coût | Valeur | Pourquoi |")
    lines.append("|---|--------|------------|------|--------|----------|")

    for i, m in enumerate(all_models[:5], 1):
        if m['score'] >= 90:
            score_icon = "🟢"
        elif m['score'] >= 75:
            score_icon = "🟡"
        else:
            score_icon = "🟠"

        badge = " 👑" if i == 1 else ""
        reason_short = m['reason'][:40] + "..." if len(m['reason']) > 40 else m['reason']

        lines.append(
            f"| {i} | **{m['name']}**{badge} | {score_icon} {m['score']}% | ${m['cost']:.4f} | {m['value']:.0f} | {reason_short} |"
        )

    best_value = max(all_models, key=lambda x: x['value'])
    best_domain = all_models[0]

    lines.append(f"\n👑 = Meilleur pour {domain_display}")

    # Sources
    lines.append("\n---")
    lines.append("### 📚 Sources\n")
    lines.append(f"- [Anthropic]({BENCHMARK_SOURCES['anthropic']['url']})")
    lines.append(f"- [OpenAI]({BENCHMARK_SOURCES['openai']['url']})")
    lines.append(f"- [Google]({BENCHMARK_SOURCES['google']['url']})")

    # Image generation section
    if domain == 'image':
        lines.append("\n---")
        lines.append("### 🎨 Outils de Génération d'Images 2025\n")
        lines.append("| Outil | Meilleur pour | Prix |")
        lines.append("|-------|---------------|------|")
        lines.append("| **Midjourney V7** | Art, concept | $10-60/mois |")
        lines.append("| **DALL-E 3** | Marketing, texte | ChatGPT+ |")
        lines.append("| **Flux.2** | Photoréalisme | Gratuit-$0.05 |")
        lines.append("| **Ideogram 3** | Logos, typo | Freemium |")

    # Final recommendation
    lines.append("\n---")
    lines.append("### 💡 Recommandation\n")

    if ollama_info:
        lines.append(f"1. ✅ **Reformatage:** {ollama_info['name']} (gratuit)")
        lines.append(f"2. 🚀 **Exécution:** {best_domain['name']} ({best_domain['score']}%)")
    else:
        lines.append(f"🥇 **Recommandé:** {best_domain['name']} ({best_domain['score']}%)")

    if best_value['model'] != best_domain['model']:
        lines.append(f"💰 **Meilleur Q/P:** {best_value['name']} (${best_value['cost']:.4f})")

    # Domain tips
    domain_tips = {
        'code': "💡 Pour du code complexe, Opus 4.5 vaut le coup.",
        'legal': "💡 Gemini 3 Pro peut analyser des dossiers complets (1M tokens).",
        'medical': "💡 GPT-5 a le moins d'hallucinations (-45%).",
        'finance': "💡 Claude a des safety filters ASL-3.",
        'research': "💡 Gemini 3 Pro (GPQA 91.9%) excelle en PhD-level.",
        'math': "💡 GPT-5 Pro atteint 100% sur AIME 2025.",
        'image': "🎨 GPT-5 avec DALL-E intégré génère directement.",
        'document': "📄 Gemini 3 Pro (1M tokens) > Claude (200K) > GPT (128K).",
        'general': "💡 GPT-5.1 offre le meilleur équilibre.",
    }
    lines.append(f"\n{domain_tips.get(domain, domain_tips['general'])}")

    return "\n".join(lines)


def get_comparison_table() -> str:
    """Generate model comparison table."""
    comparisons = compare_models(1000, 500)

    lines = [
        "| Modèle | Input/M | Output/M | Contexte | Tier | Coût 1K+500 |",
        "|--------|---------|----------|----------|------|-------------|"
    ]

    for c in comparisons:
        lines.append(
            f"| {c['model']} | {c['input_price']} | {c['output_price']} | "
            f"{c['context']} | {c['tier']} | {c['cost_display']} |"
        )

    return "\n".join(lines)


def calculate_costs(input_tokens: int, output_tokens: int) -> str:
    """Calculate costs for all models."""
    if not input_tokens or not output_tokens:
        return "⚠️ Entre le nombre de tokens"

    comparisons = compare_models(int(input_tokens), int(output_tokens))

    lines = [
        f"### 💵 Coût estimé pour {int(input_tokens):,} input + {int(output_tokens):,} output tokens\n",
        "| Modèle | Coût | Tier |",
        "|--------|------|------|"
    ]

    for c in comparisons:
        lines.append(f"| {c['model']} | **{c['cost_display']}** | {c['tier']} |")

    cheapest = comparisons[0]
    most_expensive = comparisons[-1]

    lines.append(f"\n**💰 Le moins cher:** {cheapest['model']} ({cheapest['cost_display']})")
    lines.append(f"\n**🔥 Le plus puissant:** {most_expensive['model']} ({most_expensive['cost_display']})")

    return "\n".join(lines)
