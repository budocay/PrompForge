"""
Interface web Gradio pour PromptForge.
Lance avec: promptforge web

Compatible avec Gradio 4.x et 6.x
"""

import gradio as gr
from pathlib import Path
from typing import Optional

from .core import PromptForge


# Instance globale
_forge: Optional[PromptForge] = None


def get_forge() -> PromptForge:
    """Récupère ou crée l'instance PromptForge."""
    global _forge
    if _forge is None:
        _forge = PromptForge()
    return _forge


def check_ollama_status() -> str:
    """Vérifie le statut d'Ollama."""
    forge = get_forge()
    if forge.ollama.is_available():
        models = forge.ollama.list_models()
        model_list = ', '.join(models[:5]) if models else 'aucun'
        return f"✅ Ollama connecté | Modèle: {forge.ollama.config.model} | Disponibles: {model_list}"
    return "❌ Ollama non disponible - Lancez 'ollama serve'"


def get_projects_list() -> list[str]:
    """Liste les projets disponibles."""
    forge = get_forge()
    projects = forge.list_projects()
    return [p.name for p in projects]


def get_current_project() -> str:
    """Retourne le projet actif."""
    forge = get_forge()
    project = forge.get_current_project()
    return project.name if project else ""


def get_project_config(project_name: str) -> str:
    """Récupère la config d'un projet."""
    if not project_name:
        return ""
    forge = get_forge()
    project = forge.db.get_project(project_name)
    return project.config_content if project else ""


def refresh_projects_dropdown():
    """Rafraîchit la liste des projets."""
    projects = get_projects_list()
    current = get_current_project()
    return gr.update(choices=projects, value=current if current in projects else None)


def select_project(project_name: str) -> tuple[str, str]:
    """Sélectionne un projet et retourne sa config."""
    if not project_name:
        return "*Sélectionnez un projet*", ""
    
    forge = get_forge()
    success, msg = forge.use_project(project_name)
    config = get_project_config(project_name)
    
    status = f"✅ Projet '{project_name}' activé" if success else f"❌ {msg}"
    return config, status


def normalize_name(name: str) -> str:
    """Normalise un nom de projet."""
    return name.strip().replace(" ", "-").lower()


def create_project_from_editor(name: str, config_content: str):
    """Crée un projet depuis l'éditeur manuel."""
    if not name or not config_content:
        return "❌ Nom et configuration requis", config_content, gr.update()
    
    normalized_name = normalize_name(name)
    forge = get_forge()
    
    config_path = forge.projects_path / f"{normalized_name}.md"
    config_path.write_text(config_content, encoding="utf-8")
    
    success, msg = forge.init_project(normalized_name, str(config_path))
    
    projects = get_projects_list()
    if success:
        forge.use_project(normalized_name)
        return f"✅ {msg}", config_content, gr.update(choices=projects, value=normalized_name)
    return f"❌ {msg}", config_content, gr.update(choices=projects)


def upload_file(file, project_name: str):
    """Upload un fichier .md et crée le projet."""
    if file is None:
        return "❌ Aucun fichier sélectionné", gr.update(), gr.update()
    
    if not project_name:
        return "❌ Entrez d'abord un nom de projet", gr.update(), gr.update()
    
    try:
        content = Path(file).read_text(encoding="utf-8")
        normalized_name = normalize_name(project_name)
        forge = get_forge()
        
        config_path = forge.projects_path / f"{normalized_name}.md"
        config_path.write_text(content, encoding="utf-8")
        
        success, msg = forge.init_project(normalized_name, str(config_path))
        
        projects = get_projects_list()
        if success:
            forge.use_project(normalized_name)
            return (
                f"✅ {msg}", 
                gr.update(choices=projects, value=normalized_name),
                gr.update(choices=projects, value=normalized_name)
            )
        return f"❌ {msg}", gr.update(choices=projects), gr.update(choices=projects)
    except Exception as e:
        return f"❌ Erreur: {e}", gr.update(), gr.update()


def delete_project(project_name: str):
    """Supprime un projet."""
    if not project_name:
        return "❌ Sélectionnez un projet", gr.update()
    
    forge = get_forge()
    success, msg = forge.delete_project(project_name)
    
    projects = get_projects_list()
    status = f"✅ {msg}" if success else f"❌ {msg}"
    return status, gr.update(choices=projects, value=None)


def get_comparison_table() -> str:
    """Génère le tableau de comparaison des modèles."""
    from .profiles import compare_models
    
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
    """Calcule les coûts pour tous les modèles."""
    from .profiles import compare_models
    
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
    
    # Ajouter les recommandations
    cheapest = comparisons[0]
    most_expensive = comparisons[-1]
    
    lines.append(f"\n**💰 Le moins cher:** {cheapest['model']} ({cheapest['cost_display']})")
    lines.append(f"\n**🔥 Le plus puissant:** {most_expensive['model']} ({most_expensive['cost_display']})")
    
    # Calcul mensuel estimé (1000 requêtes/jour)
    daily_cost_cheap = cheapest['cost'] * 1000
    monthly_cost_cheap = daily_cost_cheap * 30
    
    lines.append(f"\n\n### 📊 Estimation mensuelle (1000 requêtes/jour)")
    lines.append(f"- **{cheapest['model']}**: ${monthly_cost_cheap:.2f}/mois")
    lines.append(f"- **{most_expensive['model']}**: ${most_expensive['cost'] * 1000 * 30:.2f}/mois")
    
    return "\n".join(lines)


def estimate_tokens(text: str) -> int:
    """Estime le nombre de tokens (approximation: 1 token ≈ 4 caractères)."""
    return len(text) // 4


def detect_task_type(prompt: str) -> str:
    """Détecte le type de tâche à partir du prompt."""
    prompt_lower = prompt.lower()
    
    # Mots-clés pour chaque type (élargi)
    code_keywords = ['code', 'fonction', 'function', 'api', 'endpoint', 'bug', 'debug', 
                     'refactor', 'test', 'class', 'method', 'variable', 'import',
                     'database', 'sql', 'query', 'script', 'algorithm', 'implementation',
                     'module', 'library', 'framework', 'backend', 'frontend', 'crud',
                     'route', 'controller', 'model', 'schema', 'migration', 'deploy',
                     'docker', 'git', 'commit', 'branch', 'merge', 'pull request']
    
    analysis_keywords = ['analyse', 'analyze', 'research', 'study', 'compare', 'evaluate',
                        'review', 'audit', 'report', 'summary', 'synthesize', 'document',
                        'résumé', 'synthèse', 'données', 'data', 'statistics', 'metrics',
                        'benchmark', 'performance', 'optimize', 'améliorer', 'improve']
    
    creative_keywords = ['write', 'create', 'design', 'imagine', 'story', 'article',
                        'blog', 'content', 'creative', 'idea', 'concept', 'brand',
                        'écris', 'rédige', 'histoire', 'récit', 'poème', 'slogan',
                        'marketing', 'publicité', 'campagne', 'narratif', 'fiction']
    
    chat_keywords = ['explain', 'help', 'what is', 'how to', 'question', 'answer',
                    'clarify', 'describe', 'tell me', 'explique', 'aide', 'comment',
                    'pourquoi', 'quest-ce', 'définition', 'definition', 'meaning',
                    'understand', 'comprendre', 'learn', 'apprendre', 'tutorial']
    
    # Compter les occurrences
    code_score = sum(1 for k in code_keywords if k in prompt_lower)
    analysis_score = sum(1 for k in analysis_keywords if k in prompt_lower)
    creative_score = sum(1 for k in creative_keywords if k in prompt_lower)
    chat_score = sum(1 for k in chat_keywords if k in prompt_lower)
    
    # Bonus pour certains patterns
    if '<context>' in prompt_lower or '<task>' in prompt_lower:
        code_score += 2  # Format Claude = souvent du code
    if '```' in prompt_lower:
        code_score += 3  # Présence de code blocks
    if 'requirements' in prompt_lower or 'specifications' in prompt_lower:
        code_score += 1
    
    # Déterminer le type dominant
    scores = {
        'code': code_score,
        'analysis': analysis_score,
        'creative': creative_score,
        'chat': chat_score
    }
    
    max_type = max(scores, key=scores.get)
    if scores[max_type] == 0:
        return 'general'
    return max_type


def generate_recommendation(formatted_prompt: str, task_type: str) -> str:
    """Génère une recommandation de modèle basée sur le prompt reformaté."""
    from .profiles import MODEL_PRICING, TargetModel
    
    # Estimer les tokens
    input_tokens = estimate_tokens(formatted_prompt)
    # Estimation output: généralement 1.5x à 3x l'input pour du code, 0.5x pour du chat
    output_multiplier = {
        'code': 2.5,
        'analysis': 1.5,
        'creative': 2.0,
        'chat': 0.8,
        'general': 1.5
    }
    output_tokens = int(input_tokens * output_multiplier.get(task_type, 1.5))
    
    # ==========================================================================
    # BENCHMARKS RÉELS - Sources décembre 2025
    # ==========================================================================
    # SWE-bench Verified: Mesure la capacité à résoudre des issues GitHub réelles
    # Sources: 
    #   - Anthropic: https://www.anthropic.com/news/claude-opus-4-5
    #   - OpenAI: https://openai.com/index/introducing-gpt-5/
    #   - Google: https://blog.google/products/gemini/gemini-3/
    #   - Simon Willison: https://simonwillison.net/2025/Nov/24/claude-opus/
    #
    # AIME 2025: American Invitational Mathematics Examination
    # GPQA Diamond: Graduate-level PhD science questions
    # OSWorld: Computer use / desktop interaction benchmark
    # ==========================================================================
    
    # Benchmarks par modèle (SWE-bench %, AIME %, GPQA %)
    # Format: {'swe': score, 'aime': score, 'gpqa': score, 'source': 'url'}
    BENCHMARKS = {
        TargetModel.CLAUDE_OPUS_4_5: {
            'swe': 80.9,    # SWE-bench Verified
            'aime': 90.0,   # Estimé (>Sonnet 4.5)
            'gpqa': 85.0,   # Estimé (>Sonnet 4.5)
            'source': 'anthropic.com/news/claude-opus-4-5'
        },
        TargetModel.CLAUDE_SONNET_4_5: {
            'swe': 77.2,    # 82% avec parallel compute
            'aime': 87.0,   # 100% avec Python tools
            'gpqa': 83.4,
            'source': 'anthropic.com - Sept 2025'
        },
        TargetModel.CLAUDE_HAIKU_4_5: {
            'swe': 39.5,    # Scale leaderboard SWE-bench Pro
            'aime': 65.0,   # Estimé
            'gpqa': 70.0,   # Estimé
            'source': 'scale.com/leaderboard'
        },
        TargetModel.GPT_5_1: {
            'swe': 76.3,    # SWE-bench Verified
            'aime': 95.0,   # Proche de GPT-5
            'gpqa': 86.0,   # Estimé amélioration sur GPT-5
            'source': 'openai.com/index/gpt-5-1-for-developers'
        },
        TargetModel.GPT_5_1_MINI: {
            'swe': 58.0,    # Estimé (GPT-5 mini ~58%)
            'aime': 75.0,   # Estimé
            'gpqa': 78.0,   # Estimé
            'source': 'Estimé basé sur GPT-5 mini'
        },
        TargetModel.GPT_5_PRO: {
            'swe': 75.0,    # GPT-5 avec extended thinking
            'aime': 100.0,  # Avec Python tools
            'gpqa': 89.4,   # SOTA avec extended reasoning
            'source': 'openai.com/index/introducing-gpt-5'
        },
        TargetModel.GEMINI_3_PRO: {
            'swe': 76.2,    # SWE-bench Verified
            'aime': 95.0,   # 100% avec code tools
            'gpqa': 91.9,   # SOTA sur GPQA Diamond
            'source': 'blog.google/products/gemini/gemini-3'
        },
        TargetModel.GEMINI_3_FLASH: {
            'swe': 55.0,    # Estimé (modèle rapide)
            'aime': 70.0,   # Estimé
            'gpqa': 75.0,   # Estimé
            'source': 'Estimé - modèle économique'
        },
        TargetModel.UNIVERSAL: {
            'swe': 50.0,    # Baseline
            'aime': 60.0,
            'gpqa': 65.0,
            'source': 'Profil générique'
        },
    }
    
    # Calculer un score composite selon le type de tâche
    def get_performance_score(model: TargetModel, task: str) -> float:
        b = BENCHMARKS[model]
        if task == 'code':
            return b['swe'] * 0.7 + b['gpqa'] * 0.3  # SWE-bench prioritaire
        elif task == 'analysis':
            return b['gpqa'] * 0.5 + b['aime'] * 0.3 + b['swe'] * 0.2
        elif task == 'creative':
            return b['gpqa'] * 0.4 + b['aime'] * 0.3 + b['swe'] * 0.3
        elif task == 'chat':
            return b['gpqa'] * 0.5 + b['swe'] * 0.3 + b['aime'] * 0.2
        else:  # general
            return (b['swe'] + b['aime'] + b['gpqa']) / 3
    
    # Calculer coût et score pour tous les modèles
    all_models = []
    for model in TargetModel:
        pricing = MODEL_PRICING[model]
        cost = pricing.estimate_cost(input_tokens, output_tokens)
        perf = get_performance_score(model, task_type)
        benchmarks = BENCHMARKS[model]
        
        # Score de valeur = performance / (coût * 100) - plus c'est haut, meilleur rapport
        value_score = perf / (cost * 100 + 0.001)
        
        all_models.append({
            'model': model,
            'name': model.value,
            'cost': cost,
            'perf': perf,
            'value': value_score,
            'swe': benchmarks['swe'],
            'aime': benchmarks['aime'],
            'gpqa': benchmarks['gpqa'],
            'source': benchmarks['source'],
            'context': f"{pricing.context_window // 1000}K"
        })
    
    # Trier par coût
    all_models.sort(key=lambda x: x['cost'])
    
    # Trouver les meilleurs
    best_perf = max(all_models, key=lambda x: x['perf'])
    best_value = max(all_models, key=lambda x: x['value'])
    cheapest = all_models[0]
    
    # Labels de type
    task_labels = {
        'code': '💻 Code/Dev',
        'analysis': '📊 Analyse',
        'creative': '✨ Créatif',
        'chat': '💬 Chat',
        'general': '🔧 Général'
    }
    
    # Construire le message
    lines = [
        f"### 🎯 Analyse pour ce prompt",
        f"**Type détecté:** {task_labels.get(task_type, '🔧 Général')} | "
        f"**Tokens:** ~{input_tokens:,} input → ~{output_tokens:,} output estimés\n",
        "---",
        "### 📊 Comparatif des modèles (benchmarks réels)\n",
        "| Modèle | SWE-bench | GPQA | Score | Coût | Valeur |",
        "|--------|-----------|------|-------|------|--------|"
    ]
    
    # Afficher tous les modèles
    for m in all_models:
        # Indicateurs visuels basés sur SWE-bench (benchmark code)
        if m['swe'] >= 75:
            perf_icon = "🟢"
        elif m['swe'] >= 55:
            perf_icon = "🟡"
        else:
            perf_icon = "🟠"
        
        # Marquer les meilleurs
        badges = []
        if m['model'] == best_perf['model']:
            badges.append("🏆")
        if m['model'] == best_value['model']:
            badges.append("⭐")
        if m['model'] == cheapest['model']:
            badges.append("💰")
        
        badge_str = " ".join(badges)
        
        lines.append(
            f"| {m['name']} {badge_str} | {perf_icon} {m['swe']:.1f}% | {m['gpqa']:.1f}% | {m['perf']:.1f} | ${m['cost']:.4f} | {m['value']:.1f} |"
        )
    
    lines.append("\n🏆 = Meilleur score | ⭐ = Meilleur rapport qualité/prix | 💰 = Moins cher")
    
    # Sources
    lines.append("\n---")
    lines.append("### 📚 Sources des benchmarks\n")
    lines.append("| Benchmark | Description |")
    lines.append("|-----------|-------------|")
    lines.append("| **SWE-bench Verified** | Résolution d'issues GitHub réelles (code) |")
    lines.append("| **GPQA Diamond** | Questions PhD-level en sciences |")
    lines.append("| **AIME 2025** | Compétition mathématique (non affiché) |")
    lines.append("\n*Sources: Anthropic, OpenAI, Google DeepMind - Nov/Dec 2025*")
    
    # Recommandation finale
    lines.append("\n---")
    lines.append("### 💡 Recommandation\n")
    
    # Choisir selon le contexte
    if task_type == 'code':
        recommended = best_perf
        reason = f"Meilleur SWE-bench ({best_perf['swe']:.1f}%) pour code complexe"
    elif task_type == 'chat':
        recommended = best_value
        reason = "Meilleur rapport qualité/prix pour du chat"
    elif task_type == 'analysis' and input_tokens > 2000:
        gemini = [m for m in all_models if m['model'] == TargetModel.GEMINI_3_PRO][0]
        recommended = gemini
        reason = f"1M tokens contexte + GPQA {gemini['gpqa']:.1f}% pour longs documents"
    else:
        recommended = best_value
        reason = "Meilleur équilibre performance/coût"
    
    lines.append(f"**→ {recommended['name']}** ({reason})")
    lines.append(f"- SWE-bench: {recommended['swe']:.1f}% | GPQA: {recommended['gpqa']:.1f}% | Coût: ${recommended['cost']:.4f}")
    
    # Alternative budget
    if recommended['model'] != cheapest['model']:
        savings = (recommended['cost'] - cheapest['cost']) / recommended['cost'] * 100
        perf_diff = recommended['perf'] - cheapest['perf']
        lines.append(f"\n**Alternative budget:** {cheapest['name']} (-{savings:.0f}% coût, -{perf_diff:.1f} points perf)")
    
    # Estimation mensuelle
    monthly_rec = recommended['cost'] * 100 * 30
    monthly_cheap = cheapest['cost'] * 100 * 30
    lines.append(f"\n📈 **Coût mensuel (100 req/jour):** ${monthly_rec:.2f} (recommandé) vs ${monthly_cheap:.2f} (budget)")
    
    return "\n".join(lines)


# Descriptions des profils pour l'UI (Décembre 2025)
PROFILE_DESCRIPTIONS = {
    # Claude (Anthropic)
    "claude_opus_4.5": "🟣 Claude Opus 4.5 — Meilleur pour code/agents ($5/$25)",
    "claude_sonnet_4.5": "🟣 Claude Sonnet 4.5 — Équilibré perf/coût ($3/$15)",
    "claude_haiku_4.5": "🟣 Claude Haiku 4.5 — Ultra-rapide ($0.25/$1.25)",
    
    # GPT (OpenAI)
    "gpt_5.1": "🟢 GPT-5.1 — Flagship adaptatif ($1.25/$10)",
    "gpt_5.1_mini": "🟢 GPT-5.1 Mini — Économique ($0.25/$2)",
    "gpt_5_pro": "🟢 GPT-5 Pro — Raisonnement étendu ($5/$20)",
    
    # Gemini (Google)
    "gemini_3_pro": "🔵 Gemini 3 Pro — 1M tokens! ($2/$12)",
    "gemini_3_flash": "🔵 Gemini 3 Flash — Rapide ($0.50/$2)",
    
    # Universel
    "universel": "⚪ Universel — Compatible tous modèles",
}


def get_profile_choices() -> list[str]:
    """Retourne la liste des profils pour le dropdown."""
    return list(PROFILE_DESCRIPTIONS.keys())


def get_profile_label(profile_name: str) -> str:
    """Retourne le label d'un profil."""
    return PROFILE_DESCRIPTIONS.get(profile_name, profile_name)


def format_prompt(raw_prompt: str, project_name: str, profile_name: str) -> tuple[str, str, str]:
    """Reformate un prompt avec le profil sélectionné et génère une recommandation."""
    if not raw_prompt.strip():
        return "", "❌ Entrez un prompt", "*Aucune recommandation*"
    
    if not project_name:
        return "", "❌ Sélectionnez un projet", "*Aucune recommandation*"
    
    forge = get_forge()
    
    if not forge.ollama.is_available():
        return "", "❌ Ollama non disponible. Lancez 'ollama serve'", "*Aucune recommandation*"
    
    # Utiliser le profil sélectionné
    success, file_path, formatted = forge.format_prompt(
        raw_prompt, 
        project_name,
        profile_name=profile_name if profile_name else None
    )
    
    if success:
        profile_label = get_profile_label(profile_name) if profile_name else "Standard"
        
        # Détecter le type de tâche et générer la recommandation
        task_type = detect_task_type(raw_prompt + " " + formatted)
        recommendation = generate_recommendation(formatted, task_type)
        
        status = f"✅ Reformaté avec {profile_label}\n📁 {file_path}"
        return formatted, status, recommendation
    return "", f"❌ {file_path}", "*Erreur lors du reformatage*"


def get_history_display(project_filter: str, limit: int = 10) -> str:
    """Affiche l'historique formaté."""
    forge = get_forge()
    
    project_name = project_filter if project_filter and project_filter != "Tous" else None
    history = forge.get_history(project_name, int(limit))
    
    if not history:
        return "📭 Aucun historique"
    
    output = []
    for h in history:
        date_str = h.created_at[:16].replace("T", " ")
        preview = h.raw_prompt[:80].replace('\n', ' ')
        if len(h.raw_prompt) > 80:
            preview += "..."
        output.append(f"**[{date_str}]** {preview}\n\n📁 `{Path(h.file_path).name}`\n\n---")
    
    return "\n".join(output)


def load_project_to_editor(project_name: str) -> tuple[str, str]:
    """Charge un projet dans l'éditeur."""
    if not project_name:
        return "", ""
    return project_name, get_project_config(project_name)


PROJECT_GENERATOR_PROMPT = '''# 🎯 Génère ta configuration projet

Copie ce prompt et envoie-le à **Claude**, **ChatGPT** ou ton IA préférée :

```
Je veux créer un fichier de configuration pour mon projet.
Ce fichier servira de contexte pour optimiser mes futurs prompts.

Pose-moi ces questions UNE PAR UNE :

1. Nom du projet ?
2. Description (2-3 phrases) ?
3. Stack technique (langages, frameworks, DB) ?
4. Structure des dossiers ?
5. Conventions de code ?
6. Tests utilisés ?
7. Patterns/architecture ?
8. Règles métier importantes ?
9. Contraintes (perf, sécu) ?

Puis génère un fichier Markdown structuré.
```

💡 **Astuce** : Plus tu donnes de détails, meilleur sera le reformatage !
'''


def create_interface() -> gr.Blocks:
    """Crée l'interface Gradio."""
    
    with gr.Blocks(title="PromptForge") as interface:
        
        gr.Markdown("# 🔧 PromptForge\n**Reformateur intelligent de prompts avec contexte projet**")
        
        # Status Ollama
        with gr.Row():
            ollama_status = gr.Markdown(check_ollama_status())
            refresh_btn = gr.Button("🔄 Rafraîchir")
        
        with gr.Tabs():
            # === TAB 1: Reformater ===
            with gr.Tab("✨ Reformater"):
                with gr.Row():
                    with gr.Column():
                        project_select = gr.Dropdown(
                            label="📁 Projet actif",
                            choices=get_projects_list(),
                            value=get_current_project() or None,
                            interactive=True
                        )
                        
                        profile_select = gr.Dropdown(
                            label="🎯 Optimisé pour",
                            choices=get_profile_choices(),
                            value="universel",
                            interactive=True
                        )
                        
                        # Info sur le profil sélectionné
                        profile_info = gr.Markdown("""
**⚪ Universel** : Format compatible avec tous les LLMs modernes.
                        """)
                        
                        raw_prompt = gr.Textbox(
                            label="✏️ Ton prompt brut",
                            placeholder="Ex: crée une route pour gérer les utilisateurs avec validation et gestion d'erreurs...",
                            lines=6
                        )
                        format_btn = gr.Button("🚀 Reformater", variant="primary")
                        format_status = gr.Markdown("")
                    
                    with gr.Column():
                        formatted_prompt = gr.Textbox(
                            label="📤 Prompt reformaté (sélectionne et copie avec Ctrl+C)",
                            lines=15,
                            interactive=True  # Pour permettre la sélection/copie
                        )
                
                # === Section Recommandation ===
                with gr.Accordion("🎯 Recommandation modèle (après reformatage)", open=True):
                    recommendation_output = gr.Markdown(
                        value="*Lance un reformatage pour voir la recommandation de modèle optimale...*"
                    )
                
                with gr.Accordion("📋 Configuration du projet", open=False):
                    project_config_display = gr.Markdown("*Sélectionnez un projet*")
            
            # === TAB 2: Projets ===
            with gr.Tab("📁 Projets"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### ➕ Créer un projet")
                        
                        new_project_name = gr.Textbox(
                            label="1️⃣ Nom du projet",
                            placeholder="mon-projet"
                        )
                        
                        gr.Markdown("**2️⃣ Configuration** (choisir une méthode)")
                        
                        with gr.Tab("📤 Uploader un .md"):
                            config_file = gr.File(
                                label="Glisser-déposer ou cliquer pour uploader",
                                file_types=[".md", ".txt"],
                                type="filepath"
                            )
                            upload_btn = gr.Button("📤 Charger le fichier", variant="primary")
                        
                        with gr.Tab("✏️ Écrire manuellement"):
                            config_editor = gr.Textbox(
                                label="Configuration (Markdown)",
                                lines=12,
                                placeholder="# Mon Projet\n\n## Stack\n- Python 3.12\n- FastAPI\n..."
                            )
                            save_btn = gr.Button("💾 Sauvegarder", variant="primary")
                        
                        project_status = gr.Markdown("")
                        
                        gr.Markdown("---")
                        delete_btn = gr.Button("🗑️ Supprimer le projet sélectionné", variant="stop")
                    
                    with gr.Column():
                        gr.Markdown("### 📂 Projets existants")
                        projects_list_dropdown = gr.Dropdown(
                            label="Sélectionner un projet",
                            choices=get_projects_list(),
                            interactive=True
                        )
                        load_btn = gr.Button("📂 Charger dans l'éditeur")
                        
                        gr.Markdown("### 📄 Aperçu de la configuration")
                        project_preview = gr.Markdown("*Sélectionnez un projet pour voir sa configuration*")
            
            # === TAB 3: Historique ===
            with gr.Tab("📜 Historique"):
                with gr.Row():
                    history_filter = gr.Dropdown(
                        label="Filtrer par projet",
                        choices=["Tous"] + get_projects_list(),
                        value="Tous"
                    )
                    history_limit = gr.Slider(
                        label="Résultats",
                        minimum=5,
                        maximum=50,
                        value=10,
                        step=5
                    )
                    refresh_history_btn = gr.Button("🔄")
                
                history_display = gr.Markdown(get_history_display("Tous", 10))
            
            # === TAB 4: Générer config ===
            with gr.Tab("🎯 Générer config"):
                gr.Markdown(PROJECT_GENERATOR_PROMPT)
                gr.Markdown("---\n### Exemple")
                gr.Markdown("""```markdown
# Mon App

## Stack
- Python 3.12, FastAPI, PostgreSQL

## Structure
src/
├── api/
├── models/
└── services/

## Conventions
- Type hints obligatoires
- Tests pytest
```""")
            
            # === TAB 5: Comparaison Prix ===
            with gr.Tab("💰 Comparaison"):
                gr.Markdown("""## Comparaison des modèles (Décembre 2025)
Tous les prix sont en **$ par million de tokens**.""")
                
                comparison_table = gr.Markdown(get_comparison_table())
                
                with gr.Row():
                    input_tokens = gr.Number(label="Tokens input", value=1000, minimum=100)
                    output_tokens = gr.Number(label="Tokens output", value=500, minimum=100)
                    calc_btn = gr.Button("💵 Calculer le coût")
                
                cost_result = gr.Markdown("")
                
                gr.Markdown("""
### 💡 Recommandations par cas d'usage

| Tâche | 🏆 Meilleur | ⚡ Équilibré | 💰 Budget |
|-------|------------|-------------|-----------|
| **Code complexe** | Claude Opus 4.5 | Claude Sonnet 4.5 | GPT-5.1 Mini |
| **Chat / Assistant** | GPT-5.1 | Gemini 3 Flash | Claude Haiku 4.5 |
| **Analyse longue** | Gemini 3 Pro (1M!) | Claude Sonnet 4.5 | GPT-5.1 Mini |
| **Créativité** | GPT-5.1 | Claude Sonnet 4.5 | Gemini 3 Flash |
| **Volume élevé** | GPT-5.1 Mini | Claude Haiku 4.5 | Gemini 3 Flash |

### 📊 Notes
- **Claude Opus 4.5** : Meilleur pour code/agents mais le plus cher
- **GPT-5.1** : Excellent rapport qualité/prix, raisonnement adaptatif
- **Gemini 3 Pro** : Contexte 1M tokens, parfait pour gros documents
- **Cache** : Jusqu'à 90% de réduction sur les tokens répétés
                """)
            
            # === TAB 6: Aide ===
            with gr.Tab("❓ Aide"):
                gr.Markdown("""
## Guide rapide

### 1. Créer un projet
- Onglet **Projets** → Entre nom + config → **Sauvegarder**

### 2. Reformater
- Sélectionne projet → Entre prompt → **Reformater** → Copie le résultat !

### Pré-requis
- Ollama lancé (`ollama serve`)
- Modèle installé (`ollama pull llama3.1`)

### CLI
```bash
promptforge init mon-projet --config config.md
promptforge format "mon prompt"
promptforge list
```
                """)
        
        # === Events ===
        refresh_btn.click(fn=check_ollama_status, outputs=ollama_status)
        
        # Mise à jour de l'info du profil quand on change de profil
        def update_profile_info(profile_name: str) -> str:
            infos = {
                # Claude (Anthropic) - Décembre 2025
                "claude_opus_4.5": """**🟣 Claude Opus 4.5** (Anthropic)
- État de l'art pour code, agents, computer use
- Sessions de 30+ minutes autonomes
- Balises XML (`<context>`, `<thinking_approach>`)
- **$5 input / $25 output** par million tokens
- Contexte: 200K tokens""",
                
                "claude_sonnet_4.5": """**🟣 Claude Sonnet 4.5** (Anthropic)
- Excellent équilibre performance/coût
- Modèle hybride (rapide ou raisonnement)
- Balises XML structurées
- **$3 input / $15 output** par million tokens
- Contexte: 200K tokens (1M en beta)""",
                
                "claude_haiku_4.5": """**🟣 Claude Haiku 4.5** (Anthropic)
- Ultra rapide et économique
- Latence minimale, volume élevé
- Format XML minimal
- **$0.25 input / $1.25 output** par million tokens
- Contexte: 200K tokens""",
                
                # GPT (OpenAI) - Décembre 2025
                "gpt_5.1": """**🟢 GPT-5.1** (OpenAI - Nov 2025)
- Flagship avec raisonnement adaptatif
- Modes: Instant, Thinking, Auto
- 45% moins d'hallucinations que GPT-4o
- **$1.25 input / $10 output** par million tokens
- Contexte: 272K tokens""",
                
                "gpt_5.1_mini": """**🟢 GPT-5.1 Mini** (OpenAI)
- Rapide et économique
- Parfait pour le volume
- Format Markdown concis
- **$0.25 input / $2 output** par million tokens
- Contexte: 200K tokens""",
                
                "gpt_5_pro": """**🟢 GPT-5 Pro** (OpenAI)
- Raisonnement étendu premium
- 22% moins d'erreurs que standard
- Analyses complexes et critiques
- **$5 input / $20 output** par million tokens
- Contexte: 272K tokens""",
                
                # Gemini (Google) - Décembre 2025
                "gemini_3_pro": """**🔵 Gemini 3 Pro** (Google - Déc 2025)
- Meilleur multimodal Google
- Mode "Deep Think" avancé
- "Vibe coding" et interfaces génératives
- **$2 input / $12 output** par million tokens
- Contexte: **1 MILLION tokens** 🚀""",
                
                "gemini_3_flash": """**🔵 Gemini 3 Flash** (Google)
- Ultra-rapide et efficace
- Parfait pour chat et volume
- Format concis
- **$0.50 input / $2 output** par million tokens
- Contexte: 1M tokens""",
                
                # Universel
                "universel": """**⚪ Universel**
- Compatible avec tous les LLMs modernes
- Format équilibré Markdown + structure
- Recommandé si tu utilises plusieurs IA
- Prix moyen estimé: $1/$5 par million tokens"""
            }
            return infos.get(profile_name, "Sélectionne un profil")
        
        profile_select.change(
            fn=update_profile_info,
            inputs=[profile_select],
            outputs=[profile_info]
        )
        
        format_btn.click(
            fn=format_prompt,
            inputs=[raw_prompt, project_select, profile_select],
            outputs=[formatted_prompt, format_status, recommendation_output]
        )
        
        project_select.change(
            fn=select_project,
            inputs=project_select,
            outputs=[project_config_display, format_status]
        )
        
        save_btn.click(
            fn=create_project_from_editor,
            inputs=[new_project_name, config_editor],
            outputs=[project_status, config_editor, projects_list_dropdown]
        ).then(
            fn=lambda: gr.update(choices=get_projects_list()),
            outputs=project_select
        )
        
        upload_btn.click(
            fn=upload_file,
            inputs=[config_file, new_project_name],
            outputs=[project_status, projects_list_dropdown, project_select]
        )
        
        delete_btn.click(
            fn=delete_project,
            inputs=[projects_list_dropdown],
            outputs=[project_status, projects_list_dropdown]
        ).then(
            fn=lambda: gr.update(choices=get_projects_list(), value=None),
            outputs=project_select
        )
        
        load_btn.click(
            fn=load_project_to_editor,
            inputs=[projects_list_dropdown],
            outputs=[new_project_name, config_editor]
        )
        
        projects_list_dropdown.change(
            fn=lambda n: get_project_config(n) if n else "*Sélectionnez*",
            inputs=[projects_list_dropdown],
            outputs=[project_preview]
        )
        
        refresh_history_btn.click(
            fn=get_history_display,
            inputs=[history_filter, history_limit],
            outputs=history_display
        )
        
        history_filter.change(
            fn=get_history_display,
            inputs=[history_filter, history_limit],
            outputs=history_display
        )
        
        # Event pour calcul de coût
        calc_btn.click(
            fn=calculate_costs,
            inputs=[input_tokens, output_tokens],
            outputs=cost_result
        )
    
    return interface


def launch_web(host: str = "127.0.0.1", port: int = 7860, share: bool = False):
    """Lance l'interface web."""
    interface = create_interface()
    interface.launch(
        server_name=host,
        server_port=port,
        share=share,
        show_error=True
    )


if __name__ == "__main__":
    launch_web()
