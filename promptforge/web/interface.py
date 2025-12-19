"""
Main Gradio interface for PromptForge.
This module creates and launches the web UI.
"""

import gradio as gr
from pathlib import Path
from datetime import datetime
import re

from .assets import LOGO_SVG, FAVICON_B64, CUSTOM_CSS, SANS_PROJET, PROJECT_GENERATOR_PROMPT
from .ollama_helpers import (
    get_forge, set_base_path, check_ollama_status,
    get_ollama_models, get_current_ollama_model, change_ollama_model
)
from .project_helpers import (
    get_projects_list, get_current_project, get_project_config,
    refresh_projects_dropdown, select_project, create_project_from_editor,
    upload_file, delete_project, load_project_to_editor, get_history_display
)
from .analysis import compare_prompts, detect_task_type, detect_domain
from .recommendations import generate_recommendation, get_comparison_table, calculate_costs
from .profiles_ui import get_profile_choices, get_profile_label, get_profile_info
from .scanner_helpers import scan_directory_for_ui, save_scanned_config, get_default_scan_path, scan_uploaded_zip
from .template_helpers import get_template_choices, get_template_content, TEMPLATE_INFO
from ..logging_config import get_logger

logger = get_logger(__name__)

# Re-export for backward compatibility
__all__ = ["create_interface", "launch_web", "set_base_path", "get_forge"]


def format_prompt(raw_prompt: str, project_name: str, profile_name: str) -> tuple[str, str, str, str]:
    """
    Format a prompt with selected profile and generate recommendation + analysis.
    """
    if not raw_prompt.strip():
        return "", "❌ Entrez un prompt", "*Aucune recommandation*", "*Aucune analyse*"

    forge = get_forge()

    if not forge.ollama.is_available():
        return "", "❌ Ollama non disponible. Lancez 'ollama serve'", "*Aucune recommandation*", "*Aucune analyse*"

    ollama_model = forge.ollama.config.model
    logger.info(f"Formatting prompt with model: {ollama_model}, profile: {profile_name}")

    # ==========================================================================
    # MODE WITHOUT PROJECT
    # ==========================================================================
    if not project_name or project_name == SANS_PROJET:
        from ..providers import format_prompt_with_ollama

        result = format_prompt_with_ollama(
            raw_prompt=raw_prompt,
            project_context="",
            provider=forge.ollama,
            profile_name=profile_name if profile_name else None,
            return_conversion_info=True
        )

        formatted, was_converted = result if result else (None, False)

        if not formatted:
            logger.error("Formatting failed")
            return "", "❌ Erreur lors du reformatage", "*Aucune recommandation*", "*Aucune analyse*"

        profile_label = get_profile_label(profile_name) if profile_name else "Standard"

        # Detect domain on RAW prompt (not formatted with XML)
        task_type = detect_task_type(raw_prompt)
        domain = detect_domain(raw_prompt)
        recommendation = generate_recommendation(formatted, task_type, ollama_model, domain_override=domain)

        improvement_analysis = compare_prompts(raw_prompt, formatted)

        conversion_msg = ""
        if was_converted:
            conversion_msg = "\n\n🔄 **Post-traitement appliqué** : Markdown → XML\n💡 *Pour un meilleur suivi, utilisez qwen3:14b ou supérieur.*"

        status = f"✅ Reformaté avec {profile_label} (sans projet)\n📝 Mode consultation{conversion_msg}"
        logger.info(f"Formatted without project, converted={was_converted}")
        return formatted, status, recommendation, improvement_analysis

    # ==========================================================================
    # MODE WITH PROJECT
    # ==========================================================================
    project = forge.db.get_project(project_name)
    if not project:
        return "", f"❌ Projet '{project_name}' introuvable", "*Aucune recommandation*", "*Aucune analyse*"

    context_preview = project.config_content[:200].replace('\n', ' ') if project.config_content else "(vide)"
    context_length = len(project.config_content) if project.config_content else 0

    from ..providers import format_prompt_with_ollama

    result = format_prompt_with_ollama(
        raw_prompt=raw_prompt,
        project_context=project.config_content or "",
        provider=forge.ollama,
        profile_name=profile_name if profile_name else None,
        return_conversion_info=True
    )

    formatted, was_converted = result if result else (None, False)

    if formatted:
        profile_label = get_profile_label(profile_name) if profile_name else "Standard"

        # Save to history
        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        slug = re.sub(r'[^a-z0-9]+', '-', raw_prompt[:50].lower()).strip('-')
        filename = f"{timestamp}_{project_name}_{slug}.md"

        history_path = forge.history_path / filename
        history_path.parent.mkdir(exist_ok=True)

        with open(history_path, 'w', encoding='utf-8') as f:
            f.write(f"# Prompt History - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## Projet\n**Nom:** {project_name}\n\n---\n\n")
            f.write(f"## Prompt Original (brut)\n```\n{raw_prompt}\n```\n\n---\n\n")
            f.write(f"## Prompt Reformaté\n{formatted}\n")

        forge.db.add_history(
            project_id=project.id,
            raw_prompt=raw_prompt,
            formatted_prompt=formatted,
            file_path=str(history_path)
        )

        task_type = detect_task_type(raw_prompt + " " + formatted)
        recommendation = generate_recommendation(formatted, task_type, ollama_model)

        improvement_analysis = compare_prompts(raw_prompt, formatted)

        conversion_msg = ""
        if was_converted:
            conversion_msg = "\n\n🔄 **Post-traitement appliqué** : Markdown → XML"

        status = f"✅ Reformaté avec {profile_label}\n📁 {history_path.name}\n📋 **Contexte projet:** {context_length} caractères\n> _{context_preview}..._{conversion_msg}"

        logger.info(f"Formatted with project {project_name}, saved to {filename}")
        return formatted, status, recommendation, improvement_analysis

    logger.error("Formatting returned None")
    return "", "❌ Erreur lors du reformatage", "*Erreur*", "*Aucune analyse*"


def create_interface() -> gr.Blocks:
    """Create the Gradio interface."""

    favicon_head = f'<link rel="icon" type="image/svg+xml" href="{FAVICON_B64}">'

    with gr.Blocks(title="PromptForge", css=CUSTOM_CSS, head=favicon_head) as interface:

        # Header with SVG logo
        gr.HTML(f'''
        <div class="logo-header">
            {LOGO_SVG}
            <div>
                <h1>Prompt<span style="color: #ff6b35;">Forge</span></h1>
                <p style="margin: 0; color: #888; font-size: 0.9em;">Reformateur intelligent de prompts avec contexte projet</p>
            </div>
        </div>
        ''')

        # Ollama status + model selector
        with gr.Row():
            with gr.Column(scale=3):
                ollama_status = gr.Markdown(check_ollama_status())
            with gr.Column(scale=2):
                with gr.Row():
                    ollama_model_select = gr.Dropdown(
                        label="🤖 Modèle Ollama",
                        choices=get_ollama_models(),
                        value=get_current_ollama_model(),
                        interactive=True,
                        scale=2
                    )
                    refresh_btn = gr.Button("🔄", scale=0, min_width=50)

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

                        profile_info = gr.Markdown("**⚪ Universel** : Format compatible avec tous les LLMs modernes.")

                        raw_prompt = gr.Textbox(
                            label="✏️ Ton prompt brut",
                            placeholder="Ex: crée une route pour gérer les utilisateurs...",
                            lines=6
                        )
                        format_btn = gr.Button("🚀 Reformater", variant="primary")
                        format_status = gr.Markdown("")

                    with gr.Column():
                        formatted_prompt = gr.Textbox(
                            label="📤 Prompt reformaté (Ctrl+C pour copier)",
                            lines=15,
                            interactive=True
                        )

                with gr.Accordion("🎯 Recommandation modèle", open=True):
                    recommendation_output = gr.Markdown(
                        value="*Lance un reformatage pour voir la recommandation...*"
                    )

                with gr.Accordion("📈 Analyse d'amélioration", open=True):
                    improvement_output = gr.Markdown(
                        value="*Lance un reformatage pour voir l'analyse comparative...*"
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
                                label="Glisser-déposer",
                                file_types=[".md", ".txt"],
                                type="filepath"
                            )
                            upload_btn = gr.Button("📤 Charger le fichier", variant="primary")

                        with gr.Tab("✏️ Écrire manuellement"):
                            config_editor = gr.Textbox(
                                label="Configuration (Markdown)",
                                lines=12,
                                placeholder="# Mon Projet\n\n## Stack\n- Python 3.12\n..."
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
                        project_preview = gr.Markdown("*Sélectionnez un projet*")

            # === TAB 3: Scanner ===
            with gr.Tab("🔍 Scanner"):
                gr.Markdown("""### 🔍 Scanner automatique de projet
Naviguez vers votre projet et scannez-le pour générer une configuration.""")

                with gr.Row():
                    with gr.Column():
                        scan_path = gr.Textbox(
                            label="📁 Chemin du projet",
                            value=get_default_scan_path(),
                            placeholder="/hostfs/mon-projet"
                        )

                        gr.Markdown("#### 📂 Navigateur")
                        folder_list = gr.Dropdown(
                            label="Dossiers",
                            choices=[],
                            interactive=True,
                            allow_custom_value=False
                        )
                        with gr.Row():
                            nav_enter_btn = gr.Button("📂 Ouvrir", variant="primary")
                            nav_parent_btn = gr.Button("⬆️ Parent")
                            nav_refresh_btn = gr.Button("🔄")

                        gr.Markdown("---")
                        scan_project_name = gr.Textbox(
                            label="📝 Nom du projet",
                            placeholder="mon-projet"
                        )
                        scan_description = gr.Textbox(
                            label="📄 Description (optionnel)",
                            placeholder="Laissez vide pour extraire du README",
                            lines=2
                        )
                        scan_depth = gr.Slider(
                            label="🔢 Profondeur du scan",
                            minimum=1,
                            maximum=5,
                            value=3,
                            step=1
                        )

                        with gr.Row():
                            scan_btn = gr.Button("🔍 Scanner ce dossier", variant="primary")
                            save_scan_btn = gr.Button("💾 Sauvegarder", variant="secondary")

                        scan_status = gr.Markdown("")

                    with gr.Column():
                        gr.Markdown("#### 📊 Résumé du scan")
                        scan_summary = gr.Markdown(
                            value="*Naviguez vers un projet et cliquez Scanner...*"
                        )

                with gr.Accordion("📄 Configuration générée (modifiable)", open=True):
                    scan_config_output = gr.Textbox(
                        label="Configuration Markdown",
                        lines=20,
                        interactive=True,
                        placeholder="La configuration générée apparaîtra ici après le scan..."
                    )

            # === TAB 4: Templates Métiers (AMÉLIORÉ) ===
            with gr.Tab("👔 Templates Métiers"):
                gr.Markdown("""## 👔 Créez votre profil métier

**Deux options pour vous :**
- 🚀 **Assistant guidé** : Répondez à quelques questions, on génère votre config !
- 📄 **Templates manuels** : Copiez un template et personnalisez-le vous-même
                """)
                
                with gr.Tabs():
                    # === Sous-tab 1: Assistant Guidé (NOUVEAU) ===
                    with gr.Tab("🚀 Assistant Guidé"):
                        from .onboarding import ONBOARDING_FLOWS, generate_context_from_answers, QuestionType
                        
                        gr.Markdown("""
### 🚀 Créez votre profil en 5 minutes !

Répondez aux questions et PromptForge génère automatiquement votre fichier de contexte.
**C'est la méthode recommandée pour les débutants !**
                        """)
                        
                        # État
                        wizard_answers = gr.State({})
                        wizard_step = gr.State(0)
                        wizard_profession = gr.State("")
                        
                        # === Sélection du métier ===
                        with gr.Group() as wizard_start_group:
                            profession_choices_wizard = [(flow["name"], key) for key, flow in ONBOARDING_FLOWS.items()]
                            
                            wizard_profession_dropdown = gr.Dropdown(
                                label="🎯 Choisissez votre métier",
                                choices=[name for name, _ in profession_choices_wizard],
                                value=None,
                                interactive=True
                            )
                            
                            wizard_welcome_msg = gr.Markdown("")
                            wizard_start_btn = gr.Button("▶️ Démarrer l'assistant", variant="primary", visible=False, size="lg")
                        
                        # === Questions (simplifié - 5 questions max par étape) ===
                        with gr.Group(visible=False) as wizard_questions_group:
                            wizard_progress = gr.Markdown("**Étape 1/5**")
                            wizard_step_title = gr.Markdown("### 📝 Questions")
                            
                            # Questions génériques
                            wq_text_1 = gr.Textbox(label="Q1", visible=False, interactive=True)
                            wq_text_2 = gr.Textbox(label="Q2", visible=False, interactive=True)
                            wq_textarea = gr.Textbox(label="QTA", visible=False, lines=4, interactive=True)
                            wq_select_1 = gr.Dropdown(label="QS1", visible=False, interactive=True)
                            wq_select_2 = gr.Dropdown(label="QS2", visible=False, interactive=True)
                            wq_multiselect = gr.Dropdown(label="QMS", visible=False, multiselect=True, interactive=True)
                            wq_number = gr.Number(label="QN", visible=False, interactive=True)
                            wq_slider = gr.Slider(label="QSL", visible=False, minimum=0, maximum=100, interactive=True)
                            
                            with gr.Row():
                                wizard_prev_btn = gr.Button("⬅️ Précédent", variant="secondary")
                                wizard_next_btn = gr.Button("Suivant ➡️", variant="primary")
                        
                        # === Résultat ===
                        with gr.Group(visible=False) as wizard_result_group:
                            gr.Markdown("### ✅ Votre profil est prêt !")
                            
                            wizard_result = gr.Textbox(
                                label="Votre configuration générée",
                                lines=20,
                                interactive=False
                            )
                            
                            with gr.Row():
                                wizard_project_name = gr.Textbox(
                                    label="Nom du projet",
                                    placeholder="ex: mon-projet-seo",
                                    scale=2
                                )
                                wizard_save_btn = gr.Button("💾 Sauvegarder", variant="primary", scale=1)
                            
                            wizard_save_status = gr.Markdown("")
                            wizard_restart_btn = gr.Button("🔄 Recommencer", variant="secondary")
                        
                        # === Event handlers pour le wizard ===
                        def on_wizard_profession_select(profession_name):
                            if not profession_name:
                                return "", gr.update(visible=False)
                            
                            for key, flow in ONBOARDING_FLOWS.items():
                                if flow["name"] == profession_name:
                                    welcome = f"**{flow['welcome']}**\n\n📋 {len(flow['steps'])} étapes rapides"
                                    return welcome, gr.update(visible=True)
                            return "", gr.update(visible=False)
                        
                        def start_wizard_flow(profession_name):
                            """Démarre le wizard."""
                            profession_key = None
                            for key, flow in ONBOARDING_FLOWS.items():
                                if flow["name"] == profession_name:
                                    profession_key = key
                                    break
                            
                            if not profession_key:
                                return [gr.update() for _ in range(15)]
                            
                            return render_wizard_step(profession_key, 0, {})
                        
                        def render_wizard_step(profession_key, step_idx, answers):
                            """Rend une étape du wizard."""
                            flow = ONBOARDING_FLOWS.get(profession_key)
                            if not flow or step_idx >= len(flow["steps"]):
                                return [gr.update() for _ in range(15)]
                            
                            step = flow["steps"][step_idx]
                            total = len(flow["steps"])
                            
                            # Progress
                            progress = f"**Étape {step_idx + 1}/{total}** - {step.title}"
                            title = f"### {step.icon} {step.title}\n{step.description}"
                            
                            # Questions (on a 8 composants max)
                            q_updates = [gr.update(visible=False) for _ in range(8)]
                            
                            text_i, select_i, multi_i = 0, 0, 0
                            
                            for q in step.questions[:6]:  # Max 6 questions
                                val = answers.get(q.id, q.default or "")
                                
                                if q.question_type == QuestionType.TEXT:
                                    if text_i < 2:
                                        q_updates[text_i] = gr.update(
                                            visible=True, label=q.label, 
                                            placeholder=q.placeholder, value=val,
                                            info=q.help_text
                                        )
                                        text_i += 1
                                elif q.question_type == QuestionType.TEXTAREA:
                                    q_updates[2] = gr.update(
                                        visible=True, label=q.label,
                                        placeholder=q.placeholder, value=val,
                                        info=q.help_text
                                    )
                                elif q.question_type == QuestionType.SELECT:
                                    if select_i < 2:
                                        q_updates[3 + select_i] = gr.update(
                                            visible=True, label=q.label,
                                            choices=q.options,
                                            value=val if val in q.options else None,
                                            info=q.help_text
                                        )
                                        select_i += 1
                                elif q.question_type == QuestionType.MULTISELECT:
                                    q_updates[5] = gr.update(
                                        visible=True, label=q.label,
                                        choices=q.options,
                                        value=val if isinstance(val, list) else [],
                                        info=q.help_text
                                    )
                                elif q.question_type == QuestionType.NUMBER:
                                    q_updates[6] = gr.update(
                                        visible=True, label=q.label,
                                        value=int(val) if val else 0,
                                        info=q.help_text
                                    )
                                elif q.question_type == QuestionType.SLIDER:
                                    q_updates[7] = gr.update(
                                        visible=True, label=q.label,
                                        minimum=q.min_value, maximum=q.max_value,
                                        value=int(val) if val else int((q.min_value + q.max_value) / 2),
                                        info=q.help_text
                                    )
                            
                            return [
                                gr.update(visible=False),  # wizard_start_group
                                gr.update(visible=True),   # wizard_questions_group
                                gr.update(visible=False),  # wizard_result_group
                                progress, title,
                                *q_updates,
                                step_idx, profession_key, answers
                            ]
                        
                        def wizard_next(profession_key, step_idx, answers, 
                                       q1, q2, qta, qs1, qs2, qms, qn, qsl):
                            """Passe à l'étape suivante."""
                            flow = ONBOARDING_FLOWS.get(profession_key)
                            if not flow:
                                return [gr.update() for _ in range(16)]
                            
                            # Sauvegarder les réponses
                            step = flow["steps"][step_idx]
                            q_values = [q1, q2, qta, qs1, qs2, qms, qn, qsl]
                            text_i, select_i = 0, 0
                            
                            for q in step.questions[:6]:
                                if q.question_type == QuestionType.TEXT and text_i < 2:
                                    answers[q.id] = q_values[text_i]
                                    text_i += 1
                                elif q.question_type == QuestionType.TEXTAREA:
                                    answers[q.id] = q_values[2]
                                elif q.question_type == QuestionType.SELECT and select_i < 2:
                                    answers[q.id] = q_values[3 + select_i]
                                    select_i += 1
                                elif q.question_type == QuestionType.MULTISELECT:
                                    answers[q.id] = q_values[5]
                                elif q.question_type == QuestionType.NUMBER:
                                    answers[q.id] = q_values[6]
                                elif q.question_type == QuestionType.SLIDER:
                                    answers[q.id] = q_values[7]
                            
                            next_step = step_idx + 1
                            
                            # Dernière étape -> résultat
                            if next_step >= len(flow["steps"]):
                                result = generate_context_from_answers(profession_key, answers)
                                return [
                                    gr.update(visible=False),  # start
                                    gr.update(visible=False),  # questions
                                    gr.update(visible=True),   # result
                                    "", "",  # progress, title
                                    *[gr.update(visible=False) for _ in range(8)],
                                    step_idx, profession_key, answers,
                                    result  # wizard_result
                                ]
                            
                            # Sinon étape suivante
                            base = render_wizard_step(profession_key, next_step, answers)
                            return base + [""]
                        
                        def wizard_prev(profession_key, step_idx, answers):
                            """Retourne à l'étape précédente."""
                            if step_idx <= 0:
                                return [
                                    gr.update(visible=True),   # start
                                    gr.update(visible=False),  # questions
                                    gr.update(visible=False),  # result
                                    "", "",
                                    *[gr.update(visible=False) for _ in range(8)],
                                    0, "", {},
                                    ""
                                ]
                            return render_wizard_step(profession_key, step_idx - 1, answers) + [""]
                        
                        def wizard_restart():
                            return [
                                gr.update(visible=True),
                                gr.update(visible=False),
                                gr.update(visible=False),
                                "", "",
                                *[gr.update(visible=False) for _ in range(8)],
                                0, "", {},
                                "",
                                gr.update(value=None),  # dropdown
                                "",  # welcome
                                gr.update(visible=False)  # start btn
                            ]
                        
                        def save_wizard_project(content, name):
                            if not name or not content:
                                return "❌ Nom et contenu requis"
                            try:
                                from .project_helpers import create_project_from_editor
                                result = create_project_from_editor(content, name)
                                if "✅" in result:
                                    return f"✅ Projet '{name}' créé ! Allez dans 📁 Projets pour le sélectionner."
                                return result
                            except Exception as e:
                                return f"❌ Erreur: {e}"
                        
                        # Connecter les événements
                        wizard_profession_dropdown.change(
                            fn=on_wizard_profession_select,
                            inputs=[wizard_profession_dropdown],
                            outputs=[wizard_welcome_msg, wizard_start_btn]
                        )
                        
                        wizard_outputs = [
                            wizard_start_group, wizard_questions_group, wizard_result_group,
                            wizard_progress, wizard_step_title,
                            wq_text_1, wq_text_2, wq_textarea, wq_select_1, wq_select_2,
                            wq_multiselect, wq_number, wq_slider,
                            wizard_step, wizard_profession, wizard_answers
                        ]
                        
                        wizard_start_btn.click(
                            fn=start_wizard_flow,
                            inputs=[wizard_profession_dropdown],
                            outputs=wizard_outputs
                        )
                        
                        wizard_next_btn.click(
                            fn=wizard_next,
                            inputs=[wizard_profession, wizard_step, wizard_answers,
                                   wq_text_1, wq_text_2, wq_textarea, wq_select_1, wq_select_2,
                                   wq_multiselect, wq_number, wq_slider],
                            outputs=wizard_outputs + [wizard_result]
                        )
                        
                        wizard_prev_btn.click(
                            fn=wizard_prev,
                            inputs=[wizard_profession, wizard_step, wizard_answers],
                            outputs=wizard_outputs + [wizard_result]
                        )
                        
                        wizard_restart_btn.click(
                            fn=wizard_restart,
                            outputs=wizard_outputs + [wizard_result, wizard_profession_dropdown, 
                                                      wizard_welcome_msg, wizard_start_btn]
                        )
                        
                        wizard_save_btn.click(
                            fn=save_wizard_project,
                            inputs=[wizard_result, wizard_project_name],
                            outputs=[wizard_save_status]
                        )
                    
                    # === Sous-tab 2: Templates Manuels ===
                    with gr.Tab("📄 Templates Manuels"):
                        gr.Markdown("""
### 📄 Templates à copier-coller

Pour les utilisateurs avancés : copiez un template et personnalisez-le vous-même.
                        """)
                        
                        with gr.Row():
                            template_dropdown = gr.Dropdown(
                                label="Choisir un métier",
                                choices=[info['name'] for info in TEMPLATE_INFO.values()],
                                value=None,
                                interactive=True
                            )
                            load_template_btn = gr.Button("📄 Charger", variant="primary")
                        
                        template_preview = gr.Textbox(
                            label="Template (copier dans Projets > Écrire manuellement)",
                            lines=20,
                            interactive=False,
                            placeholder="Sélectionnez un métier..."
                        )
                        
                        gr.Markdown("""
| Métier | Description |
|--------|-------------|
| 🔍 SEO Specialist | Mots-clés, audits, optimisation |
| 📢 Marketing Digital | Campagnes, ads, copywriting |
| ⚙️ Dev Backend | API, architecture, bases de données |
| 🎯 Product Manager | PRD, specs, roadmap |
| 💼 Commercial | Prospection, pitch, négociation |
| 👥 RH / Recruteur | Fiches de poste, sourcing |
| 📊 Data Analyst | SQL, dashboards, analytics |
| 🎧 Support Client | Tickets, FAQ, satisfaction |
                        """)
                        
                        def load_template_by_name(template_name):
                            if not template_name:
                                return "Sélectionnez un métier..."
                            for key, info in TEMPLATE_INFO.items():
                                if info['name'] == template_name:
                                    content = get_template_content(key)
                                    return content if content else f"❌ Template '{key}' non trouvé"
                            return "❌ Template non trouvé"
                        
                        load_template_btn.click(
                            fn=load_template_by_name,
                            inputs=[template_dropdown],
                            outputs=[template_preview]
                        )
                        
                        template_dropdown.change(
                            fn=load_template_by_name,
                            inputs=[template_dropdown],
                            outputs=[template_preview]
                        )

            # === TAB 5: Historique ===
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

            # === TAB 5: Générer config ===
            with gr.Tab("🎯 Générer config"):
                gr.Markdown("""### 🎯 Générer une configuration projet

**Comment ça marche :**
1. Copie le prompt ci-dessous
2. Colle-le dans **Claude, ChatGPT, Gemini, ou ton LLM préféré**
3. Réponds aux questions posées par l'IA
4. Copie la configuration Markdown générée
5. Colle-la dans l'onglet **Projets** pour créer ton projet

---""")

                config_prompt = gr.Textbox(
                    label="📋 Prompt à copier",
                    value="""Je veux créer un fichier de configuration ULTIME pour mon projet.
Ce fichier permettra à n'importe quel LLM (Claude, GPT, Gemini) de comprendre parfaitement mon projet et de m'aider efficacement dès le premier message, sans allers-retours inutiles.

Pose-moi ces questions UNE PAR UNE et attends ma réponse avant de passer à la suivante, scan le projet pour tout ce qui est technique afin de gagner du temps :

---

## 🎯 PARTIE 1 : Identité et Vision

1. **Nom du projet** - Nom court et identifiable

2. **Elevator pitch** - Explique le projet comme si tu avais 30 secondes (problème résolu, pour qui, comment)

3. **Type de projet** - API REST, GraphQL, webapp fullstack, CLI, librairie, mobile, desktop, monorepo, microservices ?

4. **Stade du projet** - POC, MVP, production, legacy en refacto ?

---

## 🛠️ PARTIE 2 : Stack Technique

5. **Langages et versions EXACTES** - Ex: Python 3.12.1, Node 20.x, TypeScript 5.3

6. **Frameworks avec versions** - Backend (FastAPI 0.109, Django 5.0...), Frontend (React 18, Vue 3...), ORM (SQLAlchemy 2.0, Prisma 5...)

7. **Base de données** - Type (PostgreSQL 16, MongoDB 7...), hébergement (local, RDS, Supabase...), ORM/driver utilisé

8. **Dépendances CRITIQUES** - Les 5-10 packages essentiels dont le projet ne peut pas se passer (avec versions)

9. **Outils de dev** - Package manager (pip, pnpm, poetry...), task runner (make, npm scripts...), autres outils

---

## 🏗️ PARTIE 3 : Architecture

10. **Structure des dossiers** - Montre l'arborescence RÉELLE avec le rôle de chaque dossier important

11. **Pattern d'architecture global** - Clean Architecture, Hexagonal, MVC, CQRS, Event-Driven... et POURQUOI ce choix ?

12. **Patterns de code utilisés** - Repository, Factory, Strategy, Dependency Injection... avec exemples de où ils sont utilisés

13. **Flux de données** - Comment les données circulent ? (Request → Controller → Service → Repository → DB → Response)

14. **Modèles de données PRINCIPAUX** - Les 5-10 entités/modèles clés avec leurs relations (User hasMany Posts, etc.)

---

## 📏 PARTIE 4 : Conventions (CRUCIAL pour la cohérence)

15. **Conventions de nommage** -
    - Variables/fonctions : camelCase, snake_case ?
    - Classes : PascalCase ?
    - Fichiers : kebab-case, snake_case ?
    - Constantes : UPPER_SNAKE ?
    - Préfixes/suffixes : IInterface, useHook, *Service, *Repository ?

16. **Formatter et Linter** - Outils (black, prettier, ruff, eslint...) + config importante (line length, règles custom)

17. **Style de code préféré** -
    - Fonctions courtes vs longues ?
    - Early return ou nested if ?
    - Commentaires abondants ou code auto-documenté ?
    - Gestion d'erreurs : exceptions, Result type, error codes ?

18. **Exemples de BON code** - Copie-colle 1-2 fonctions/classes qui représentent le style idéal du projet

19. **Exemples de MAUVAIS code** - Ce que tu ne veux PAS voir (anti-patterns spécifiques)

---

## 🧪 PARTIE 5 : Tests et Qualité

20. **Frameworks de test** - pytest, Jest, Vitest, Playwright... avec plugins importants

21. **Organisation des tests** - Structure des dossiers, convention de nommage (test_*, *.spec.ts)

22. **Stratégie de test** -
    - Unit tests : quoi mocker, quoi tester vraiment ?
    - Integration tests : avec vraie DB ou mocks ?
    - E2E : quels scénarios critiques ?

23. **Couverture attendue** - Minimum requis ? Fichiers exclus ?

24. **CI/CD** - GitHub Actions, GitLab CI... ? Quels checks bloquants ? (lint, tests, build)

---

## 🔐 PARTIE 6 : Sécurité et Infrastructure

25. **Authentification** - JWT, sessions, OAuth, API keys ? Où sont stockés les tokens ?

26. **Autorisation** - RBAC, ABAC, permissions custom ? Comment vérifier les droits ?

27. **Variables d'environnement** - Liste des variables .env CRITIQUES (sans les valeurs sensibles)

28. **Secrets et données sensibles** - Comment sont-ils gérés ? (Vault, AWS Secrets, .env.local)

29. **Docker** - Dockerfile(s), docker-compose, services auxiliaires (redis, minio...)

30. **Déploiement** - Environnements (dev, staging, prod), hébergeur, process de déploiement

---

## 💼 PARTIE 7 : Règles Métier (TRÈS IMPORTANT)

31. **Glossaire métier** - Les termes spécifiques au domaine et leur définition EXACTE
    (Ex: "Workspace" = espace de travail contenant plusieurs "Projects", un "Member" peut avoir plusieurs "Roles"...)

32. **Règles business INVIOLABLES** - Les invariants qui ne doivent JAMAIS être cassés
    (Ex: "Un user ne peut pas supprimer son propre compte admin", "Un paiement validé ne peut pas être annulé")

33. **Workflows critiques** - Les flux utilisateur principaux étape par étape
    (Ex: Inscription → Vérification email → Création workspace → Invitation membres)

34. **Cas limites connus** - Les edge cases identifiés et comment les gérer

35. **Ce qui a déjà cassé** - Bugs importants du passé et leur cause (pour ne pas les reproduire)

---

## ⚠️ PARTIE 8 : Pièges et Erreurs à Éviter

36. **Dépendances cachées** - "Si tu modifies X, pense à Y" / "Ce fichier est importé partout, attention"

37. **Code legacy à ne pas toucher** - Parties du code fragiles ou en cours de refacto

38. **Erreurs fréquentes des nouveaux** - Ce que les devs font souvent mal au début

39. **Performance gotchas** - Requêtes N+1, boucles coûteuses, fichiers lourds à éviter

40. **Sécurité gotchas** - Injections possibles, endpoints sensibles, données à ne jamais logger

---

## 🎨 PARTIE 9 : Préférences de Communication

41. **Niveau de détail souhaité** - Réponses concises ou explications détaillées ?

42. **Format de code préféré** - Code complet prêt à copier, ou diffs/snippets ?

43. **Proactivité** - Dois-je suggérer des améliorations ou juste répondre à la question ?

44. **Langue** - Français, anglais, mix ? Code comments dans quelle langue ?

---

## 🔮 PARTIE 10 : Contexte et Futur

45. **APIs et services externes** - Liste des intégrations tierces (Stripe, AWS S3, SendGrid...)

46. **Décisions techniques controversées** - Choix qui pourraient sembler bizarres et leur justification

47. **Dette technique connue** - Ce qui devrait être refactoré mais ne l'est pas encore

48. **Prochaines fonctionnalités** - Features prévues qui pourraient impacter l'architecture

---

## 📝 FORMAT DE SORTIE ATTENDU

Une fois TOUTES les réponses collectées, génère un fichier Markdown avec cette structure :

```markdown
# [Nom du Projet]

> [Elevator pitch]

## 📋 Quick Reference
[Tableau résumé : stack, DB, déploiement, liens utiles]

## 🏗️ Architecture
[Diagramme ASCII du flux de données + explication]

## 📁 Structure du Projet
[Arborescence avec descriptions]

## 🗃️ Modèles de Données
[Tableau des entités et relations]

## 📏 Conventions de Code
[Règles de nommage, exemples]

## ✅ Exemples de Bon Code
[Snippets représentatifs]

## ⚠️ À ÉVITER ABSOLUMENT
[Anti-patterns, erreurs communes, pièges]

## 💼 Glossaire Métier
[Termes et définitions]

## 🔒 Règles Business Inviolables
[Liste des invariants]

## 🧪 Tests
[Organisation, conventions, commandes]

## 🚀 Commandes Utiles
[dev, test, build, deploy...]

## 🔗 Dépendances Critiques
[Tableau avec versions et rôle]

## 📚 Ressources
[Docs, liens, contacts]
```

Ce format permettra à n'importe quel LLM de :
- Générer du code COHÉRENT avec l'existant dès le premier essai
- Utiliser le bon vocabulaire métier
- Éviter les pièges connus
- Respecter les conventions sans qu'on lui rappelle
- Proposer des solutions adaptées au contexte""",
                    lines=35,
                    interactive=False
                )

                gr.Button("📋 Copier le prompt", variant="primary")

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
                """)

            # === TAB 6: Aide ===
            with gr.Tab("❓ Aide"):
                gr.Markdown("""
## Guide rapide

### 1. Créer un projet
- Onglet **Projets** → Entre nom + config → **Sauvegarder**

### 2. Reformater
- Sélectionne projet → Entre prompt → **Reformater** → Copie le résultat !

### 3. Profils
- **Claude** : Optimisé pour les modèles Claude (XML strict)
- **GPT** : Optimisé pour GPT-4/5 (Markdown)
- **Gemini** : Optimisé pour Gemini (XML)
- **Universel** : Compatible tous modèles

### 4. Sans projet
- Utilise "🔧 Sans projet" pour reformater sans contexte

### 5. Modèle Ollama
- Recommandé : qwen3:8b (équilibre) ou qwen3:14b (qualité)
- CPU : phi4-mini

## Raccourcis
- `Ctrl+C` : Copier le prompt reformaté
- `Ctrl+V` : Coller dans le champ de saisie

## Troubleshooting
- **Ollama non disponible** : Lancez `ollama serve`
- **Modèle non trouvé** : `ollama pull qwen3:8b`
- **Lenteur** : Utilisez un modèle plus petit (phi4-mini)
                """)

        # === EVENT HANDLERS ===

        # Ollama model selection
        ollama_model_select.change(
            fn=change_ollama_model,
            inputs=[ollama_model_select],
            outputs=[ollama_status]
        )

        def refresh_ollama():
            models = get_ollama_models()
            current = get_current_ollama_model()
            status = check_ollama_status()
            return gr.update(choices=models, value=current), status

        refresh_btn.click(
            fn=refresh_ollama,
            outputs=[ollama_model_select, ollama_status]
        )

        # Project selection
        project_select.change(
            fn=select_project,
            inputs=[project_select],
            outputs=[project_config_display, format_status]
        )

        # Profile info update
        def update_profile_info(profile_name):
            return get_profile_info(profile_name)

        profile_select.change(
            fn=update_profile_info,
            inputs=[profile_select],
            outputs=[profile_info]
        )

        # Format button
        format_btn.click(
            fn=format_prompt,
            inputs=[raw_prompt, project_select, profile_select],
            outputs=[formatted_prompt, format_status, recommendation_output, improvement_output]
        )

        # Project management
        save_btn.click(
            fn=create_project_from_editor,
            inputs=[new_project_name, config_editor],
            outputs=[project_status, config_editor, project_select]
        )

        upload_btn.click(
            fn=upload_file,
            inputs=[config_file, new_project_name],
            outputs=[project_status, project_select, projects_list_dropdown]
        )

        delete_btn.click(
            fn=delete_project,
            inputs=[projects_list_dropdown],
            outputs=[project_status, projects_list_dropdown]
        )

        load_btn.click(
            fn=load_project_to_editor,
            inputs=[projects_list_dropdown],
            outputs=[new_project_name, config_editor]
        )

        projects_list_dropdown.change(
            fn=get_project_config,
            inputs=[projects_list_dropdown],
            outputs=[project_preview]
        )

        # History
        def refresh_history(filter_val, limit):
            return get_history_display(filter_val, limit)

        refresh_history_btn.click(
            fn=refresh_history,
            inputs=[history_filter, history_limit],
            outputs=[history_display]
        )

        history_filter.change(
            fn=refresh_history,
            inputs=[history_filter, history_limit],
            outputs=[history_display]
        )

        history_limit.change(
            fn=refresh_history,
            inputs=[history_filter, history_limit],
            outputs=[history_display]
        )

        # Scanner - Folder navigator
        def list_folders(path_str):
            """List folders in the given path."""
            try:
                path = Path(path_str) if path_str else Path(get_default_scan_path())
                if not path.exists():
                    return gr.update(choices=["❌ Chemin invalide"])
                folders = sorted([f"📁 {d.name}" for d in path.iterdir() if d.is_dir() and not d.name.startswith('.')])
                return gr.update(choices=folders if folders else ["(vide)"])
            except Exception as e:
                return gr.update(choices=[f"❌ {e}"])

        def enter_folder(current_path, selected):
            """Enter selected folder."""
            if not selected or selected.startswith("❌") or selected == "(vide)":
                return gr.update(), gr.update(), gr.update()
            folder_name = selected.replace("📁 ", "")
            new_path = str(Path(current_path) / folder_name)
            suggested_name = folder_name.lower().replace(" ", "-").replace("_", "-")
            return new_path, suggested_name, list_folders(new_path)

        def go_parent(current_path):
            """Go to parent folder."""
            parent = Path(current_path).parent
            name = parent.name.lower().replace(" ", "-").replace("_", "-") if parent.name else ""
            return str(parent), name, list_folders(str(parent))

        def refresh_folders(current_path):
            """Refresh folder list."""
            return list_folders(current_path)

        def on_path_change(new_path):
            """Update when path changes."""
            name = Path(new_path).name.lower().replace(" ", "-").replace("_", "-") if new_path else ""
            return name, list_folders(new_path)

        # Initialize folder list on load
        interface.load(fn=lambda: list_folders(get_default_scan_path()), outputs=[folder_list])

        nav_enter_btn.click(fn=enter_folder, inputs=[scan_path, folder_list], outputs=[scan_path, scan_project_name, folder_list])
        nav_parent_btn.click(fn=go_parent, inputs=[scan_path], outputs=[scan_path, scan_project_name, folder_list])
        nav_refresh_btn.click(fn=refresh_folders, inputs=[scan_path], outputs=[folder_list])
        scan_path.submit(fn=on_path_change, inputs=[scan_path], outputs=[scan_project_name, folder_list])

        scan_btn.click(
            fn=scan_directory_for_ui,
            inputs=[scan_path, scan_project_name, scan_description, scan_depth],
            outputs=[scan_status, scan_summary, scan_config_output]
        )

        save_scan_btn.click(
            fn=save_scanned_config,
            inputs=[scan_project_name, scan_config_output],
            outputs=[scan_status, project_select, projects_list_dropdown]
        )

        # Cost calculator
        calc_btn.click(
            fn=calculate_costs,
            inputs=[input_tokens, output_tokens],
            outputs=[cost_result]
        )

    logger.info("Gradio interface created")
    return interface


def launch_web(
    host: str = "0.0.0.0",
    port: int = 7860,
    share: bool = False,
    base_path: str = None
):
    """
    Launch the web interface.

    Args:
        host: Host to bind to (default 0.0.0.0)
        port: Port to run on (default 7860)
        share: Create public link via Gradio
        base_path: Optional base path for data
    """
    if base_path:
        set_base_path(base_path)

    logger.info(f"Launching web interface on {host}:{port}")

    interface = create_interface()
    interface.launch(
        server_port=port,
        share=share,
        server_name=host
    )
