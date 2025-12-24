"""
PromptForge Interface v4
========================

Interface principale:
- ✨ Reformater (Ollama)
- 📁 Projets (CRUD)
- 🔍 Scanner automatique
- 👔 Templates Métiers
- 📜 Historique
- 🎯 Générer config
- 💰 Comparaison + Calculateur
- ❓ Aide
"""

import gradio as gr
from pathlib import Path
from datetime import datetime
import json
import os

# Imports internes
from .assets import CSS_V4, LOGO_SVG_LARGE
from .ollama_helpers import (
    get_forge, set_base_path, check_ollama_status,
    get_ollama_models, get_current_ollama_model, change_ollama_model
)
from .project_helpers import (
    get_projects_list, get_current_project, get_project_config,
    refresh_projects_dropdown, select_project, create_project_from_editor,
    upload_file, delete_project, load_project_to_editor, get_history_display,
    SANS_PROJET
)
from .scanner_helpers import (
    get_default_scan_path, scan_directory_for_ui, format_scan_summary,
    scan_uploaded_zip, save_scanned_config, is_valid_project, get_folder_info,
    browse_for_folder, generate_config_with_llm
)
from .template_helpers import get_template_choices, get_template_content
from .profiles_ui import get_profile_choices, get_profile_info
from .onboarding import ONBOARDING_FLOWS, generate_context_from_answers, QuestionType
from .analysis import compare_prompts
from .recommendations import generate_recommendation, get_comparison_table, calculate_costs

from ..logging_config import get_logger
from ..security import format_cve_alert, SecurityContext

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════

# Prompt pour générer une config
CONFIG_GENERATOR_PROMPT = """Je veux créer un fichier de configuration ULTIME pour mon projet.
Ce fichier permettra à n'importe quel LLM (Claude, GPT, Gemini) de comprendre parfaitement mon projet et de m'aider efficacement dès le premier message, sans allers-retours inutiles.

Pose-moi ces questions UNE PAR UNE et attends ma réponse avant de passer à la suivante :

## 🎯 PARTIE 1 : Identité et Vision
1. **Nom du projet** - Nom court et identifiable
2. **Elevator pitch** - Explique le projet en 30 secondes
3. **Type de projet** - API REST, webapp, CLI, librairie, mobile ?
4. **Stade** - POC, MVP, production, legacy ?

## 🛠️ PARTIE 2 : Stack Technique  
5. **Langages et versions** - Ex: Python 3.12, Node 20.x
6. **Frameworks** - Backend, Frontend, ORM
7. **Base de données** - Type et hébergement
8. **Dépendances critiques** - Les 5-10 packages essentiels

## 🏗️ PARTIE 3 : Architecture
9. **Structure des dossiers** - Arborescence réelle
10. **Pattern d'architecture** - Clean, Hexagonal, MVC ?
11. **Patterns de code** - Repository, Factory, DI ?

## 📏 PARTIE 4 : Conventions
12. **Style de code** - Naming, formatters, linters
13. **Git workflow** - Branches, commits
14. **Tests** - Types et coverage attendu

## ⚠️ PARTIE 5 : Points d'attention
15. **Règles métier critiques** - Ce qu'il ne faut JAMAIS oublier
16. **Erreurs courantes** - Ce qu'il faut éviter
17. **Points de vigilance** - Sécurité, performance

Génère ensuite un fichier Markdown structuré avec toutes ces informations."""


def load_template_by_name(template_name: str) -> str:
    """Charge le contenu d'un template par son nom."""
    if not template_name:
        return "*Sélectionne un template pour voir son contenu*"
    
    # Trouver la clé correspondant au nom
    for name, key in get_template_choices():
        if name == template_name:
            content = get_template_content(key)
            return content if content else f"*Template '{template_name}' non trouvé*"
    
    return f"*Template '{template_name}' non trouvé*"


# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS HELPER
# ═══════════════════════════════════════════════════════════════════════════

def format_prompt_with_ollama(raw_prompt: str, project_name: str, profile: str, check_cves: bool = False):
    """Reformate un prompt via Ollama avec le contexte projet et analyse de sécurité."""
    forge = get_forge()

    if not raw_prompt or not raw_prompt.strip():
        return "", "⚠️ Entre un prompt à reformater", "", "", "", ""

    try:
        # Utiliser le bon nom de projet
        # "" = explicitement sans projet (ne pas utiliser le projet actif)
        # None = non spécifié (utiliserait le projet actif - cas CLI)
        if project_name and project_name != SANS_PROJET:
            proj_name = project_name
        else:
            proj_name = ""  # Explicitement sans projet

        # Reformater via Ollama (retourne tuple: success, message, formatted, security_context)
        success, message, formatted, security_ctx = forge.format_prompt(
            raw_prompt.strip(),
            project_name=proj_name,
            profile_name=profile,
            check_security=True,
            check_cves=check_cves
        )

        if not success or not formatted:
            return "", f"❌ {message}", "", "", "", ""

        # Calculer les stats
        before_len = len(raw_prompt)
        after_len = len(formatted)
        ratio = after_len / before_len if before_len > 0 else 0

        # Build security info for stats
        security_info = ""
        if security_ctx and security_ctx.is_dev:
            level_emoji = {"standard": "🟢", "elevated": "🟡", "critical": "🔴"}.get(security_ctx.security_level, "⚪")
            langs = ", ".join(security_ctx.languages[:3]) if security_ctx.languages else "N/A"
            security_info = f"""
    <div class="pf-stat-chip">
        <span class="pf-stat-chip-label">Sécurité:</span>
        <span class="pf-stat-chip-value">{level_emoji} {security_ctx.security_level}</span>
    </div>
    <div class="pf-stat-chip">
        <span class="pf-stat-chip-label">Langages:</span>
        <span class="pf-stat-chip-value">{langs}</span>
    </div>"""
            if security_ctx.cves:
                cve_count = len(security_ctx.cves)
                critical = sum(1 for c in security_ctx.cves if c.severity == "CRITICAL")
                high = sum(1 for c in security_ctx.cves if c.severity == "HIGH")
                security_info += f"""
    <div class="pf-stat-chip" style="background: #fee2e2; border-color: #ef4444;">
        <span class="pf-stat-chip-label">CVEs:</span>
        <span class="pf-stat-chip-value" style="color: #dc2626;">{cve_count} ({critical}C/{high}H)</span>
    </div>"""

        stats = f"""
<div class="pf-stats-bar">
    <div class="pf-stat-chip">
        <span class="pf-stat-chip-label">Avant:</span>
        <span class="pf-stat-chip-value">{before_len}</span>
    </div>
    <div class="pf-stat-chip">
        <span class="pf-stat-chip-label">Après:</span>
        <span class="pf-stat-chip-value">{after_len}</span>
    </div>
    <div class="pf-stat-chip">
        <span class="pf-stat-chip-label">Enrichissement:</span>
        <span class="pf-stat-chip-value">×{ratio:.0f}</span>
    </div>{security_info}
</div>
"""

        status = "✅ Prompt enrichi avec succès!"
        if security_ctx and security_ctx.cves:
            status += f" ⚠️ {len(security_ctx.cves)} CVE(s) détectée(s)!"

        # Analyse et recommandation
        analysis = compare_prompts(raw_prompt, formatted)
        recommendation = generate_recommendation(formatted, profile, get_current_ollama_model())

        # Format CVE alerts if any
        cve_alert = ""
        if security_ctx and security_ctx.cves:
            cve_alert = format_cve_alert(security_ctx.cves)

        return formatted, status, stats, analysis, recommendation, cve_alert

    except Exception as e:
        logger.error(f"Erreur reformatage: {e}")
        return "", f"❌ Erreur: {str(e)}", "", "", "", ""


# ═══════════════════════════════════════════════════════════════════════════
# INTERFACE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════

def create_interface() -> gr.Blocks:
    """Crée l'interface Gradio v4 complète."""

    with gr.Blocks(title="PromptForge", fill_width=True) as interface:
        
        # ═══════════════════════════════════════════════════════════════
        # CSS INJECTION
        # ═══════════════════════════════════════════════════════════════
        gr.HTML(f'<style>{CSS_V4}</style>')
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════════════════════════════
        gr.HTML(f'''
        <div class="pf-header">
            <div class="pf-header-logo">
                {LOGO_SVG_LARGE}
                <h1>Prompt<span style="color: var(--primary);">Forge</span></h1>
            </div>
            <p class="pf-header-tagline">
                Reformateur intelligent de prompts avec contexte projet
            </p>
        </div>
        ''')
        
        # ═══════════════════════════════════════════════════════════════
        # BARRE OLLAMA
        # ═══════════════════════════════════════════════════════════════
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
                        allow_custom_value=True,
                        scale=3
                    )
                    refresh_ollama_btn = gr.Button("🔄", variant="secondary", scale=0, min_width=60)

        # ═══════════════════════════════════════════════════════════════
        # TABS PRINCIPAUX
        # ═══════════════════════════════════════════════════════════════
        with gr.Tabs() as main_tabs:
            
            # ═══════════════════════════════════════════════════════════
            # TAB 1: REFORMATER
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("✨ Reformater", id="tab-reformat"):
                gr.Markdown("## ✨ Reformater un prompt")
                gr.Markdown("Entre ton prompt brut et récupère une version enrichie avec le contexte de ton projet.")
                
                with gr.Row():
                    # Colonne gauche: Configuration + Input
                    with gr.Column(scale=1):
                        gr.Markdown("### 📝 Configuration")
                        
                        project_select = gr.Dropdown(
                            label="📁 Projet actif",
                            choices=get_projects_list(),
                            value=get_current_project() or None,
                            interactive=True,
                            allow_custom_value=True,
                            info="Sélectionne ton projet pour ajouter son contexte"
                        )
                        
                        profile_select = gr.Dropdown(
                            label="🎯 Optimisé pour",
                            choices=get_profile_choices(),
                            value="universel",
                            interactive=True,
                            info="Choisis le LLM cible pour un format optimal"
                        )
                        
                        profile_info = gr.Markdown(get_profile_info("universel"))

                        check_cves_checkbox = gr.Checkbox(
                            label="🔒 Vérifier les CVE (dépendances vulnérables)",
                            value=False,
                            info="Vérifie les vulnérabilités via OSV.dev (plus lent)"
                        )

                        gr.Markdown("### ✏️ Ton prompt")
                        
                        raw_prompt = gr.Textbox(
                            label="",
                            placeholder="Ex: crée une route pour gérer les utilisateurs avec authentification JWT...",
                            lines=8,
                            max_lines=15
                        )
                        
                        format_btn = gr.Button(
                            "🚀 Reformater",
                            variant="primary",
                            size="lg"
                        )
                        
                        format_status = gr.Markdown("")
                    
                    # Colonne droite: Output
                    with gr.Column(scale=1):
                        gr.Markdown("### 📤 Prompt enrichi")
                        gr.Markdown("*Copie ce prompt et colle-le dans ton LLM préféré*")
                        
                        formatted_output = gr.Textbox(
                            label="",
                            placeholder="Le prompt enrichi apparaîtra ici après reformatage...",
                            lines=15,
                            max_lines=25,
                            interactive=True
                        )
                        
                        stats_html = gr.HTML("")
                
                # Accordéons pour infos supplémentaires
                with gr.Accordion("🎯 Recommandation de modèle", open=False):
                    recommendation_output = gr.Markdown("*Lance un reformatage pour voir la recommandation...*")
                
                with gr.Accordion("📈 Analyse d'amélioration", open=False):
                    analysis_output = gr.Markdown("*Lance un reformatage pour voir l'analyse comparative...*")

                with gr.Accordion("🔒 Alertes de sécurité", open=False):
                    security_alerts_output = gr.Markdown("*Les alertes CVE apparaîtront ici si des vulnérabilités sont détectées...*")

                with gr.Accordion("📋 Configuration du projet", open=False):
                    project_config_display = gr.Markdown("*Sélectionne un projet pour voir sa configuration*")
            
            # ═══════════════════════════════════════════════════════════
            # TAB 2: PROJETS
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("📁 Projets", id="tab-projects"):
                gr.Markdown("## 📁 Gestion des projets")
                gr.Markdown("Crée et gère tes projets avec leurs configurations personnalisées.")
                
                with gr.Row():
                    # Colonne gauche: Création
                    with gr.Column(scale=1):
                        gr.Markdown("### ➕ Créer un projet")
                        
                        new_project_name = gr.Textbox(
                            label="1️⃣ Nom du projet",
                            placeholder="mon-super-projet",
                            max_lines=1
                        )
                        
                        gr.Markdown("**2️⃣ Configuration** (choisir une méthode)")
                        
                        with gr.Tabs():
                            with gr.Tab("📤 Uploader un .md"):
                                config_file = gr.File(
                                    label="Glisse-dépose ton fichier de config",
                                    file_types=[".md", ".txt"],
                                    type="filepath"
                                )
                                upload_btn = gr.Button("📤 Charger le fichier", variant="primary")
                            
                            with gr.Tab("✏️ Écrire manuellement"):
                                config_editor = gr.Textbox(
                                    label="Configuration (Markdown)",
                                    placeholder="# Mon Projet\n\n## Stack\n- Python 3.12\n- FastAPI\n- PostgreSQL\n\n## Conventions\n...",
                                    lines=12,
                                    max_lines=20
                                )
                                save_btn = gr.Button("💾 Sauvegarder", variant="primary")
                        
                        project_status = gr.Markdown("")
                        
                        gr.Markdown("---")
                        delete_btn = gr.Button("🗑️ Supprimer le projet sélectionné", variant="stop")
                    
                    # Colonne droite: Liste + Aperçu
                    with gr.Column(scale=1):
                        gr.Markdown("### 📂 Projets existants")
                        
                        projects_list_dropdown = gr.Dropdown(
                            label="Sélectionner un projet",
                            choices=get_projects_list(),
                            interactive=True,
                            allow_custom_value=True
                        )
                        
                        load_btn = gr.Button("📂 Charger dans l'éditeur", variant="secondary")
                        
                        gr.Markdown("### 📄 Aperçu de la configuration")
                        
                        project_preview = gr.Markdown("*Sélectionne un projet pour voir sa configuration*")
            
            # ═══════════════════════════════════════════════════════════
            # TAB 3: SCANNER
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("🔍 Scanner", id="tab-scanner"):
                gr.Markdown("## 🔍 Génère la config de ton projet (style CLAUDE.md)")

                with gr.Row():
                    # === COLONNE GAUCHE: Sélection dossier ===
                    with gr.Column(scale=1):
                        gr.Markdown("### 📂 1. Sélectionne ton projet")

                        with gr.Row():
                            scan_path = gr.Textbox(
                                label="Chemin du projet",
                                placeholder="Clique sur Parcourir...",
                                scale=4
                            )
                            browse_btn = gr.Button("📁 Parcourir", variant="primary", scale=1)

                        folder_info = gr.Markdown("*Clique sur Parcourir pour sélectionner un dossier*")

                        gr.Markdown("### ⚙️ 2. Configuration")

                        scan_project_name = gr.Textbox(
                            label="Nom du projet",
                            placeholder="mon-super-projet",
                            max_lines=1
                        )

                        scan_description = gr.Textbox(
                            label="Description (optionnel)",
                            placeholder="Laisse vide = extrait du README",
                            lines=2,
                            max_lines=3
                        )

                        scan_depth = gr.Slider(
                            label="Profondeur de scan",
                            minimum=2,
                            maximum=10,
                            value=5,
                            step=1,
                            info="5 = standard, 10 = scan complet"
                        )

                        use_ai_scan = gr.Checkbox(
                            label="🤖 Analyse IA (Ollama)",
                            value=True,
                            info="Utilise l'IA pour comprendre le projet et générer un contexte intelligent"
                        )

                        scan_check_cves = gr.Checkbox(
                            label="🔒 Vérifier les CVE (vulnérabilités)",
                            value=True,
                            info="Vérifie les dépendances via OSV.dev pour détecter les failles de sécurité"
                        )

                        gr.Markdown("### 🚀 3. Scanner")

                        scan_and_create_btn = gr.Button(
                            "⚡ Scanner + Créer projet",
                            variant="primary",
                            size="lg"
                        )

                        with gr.Row():
                            scan_btn = gr.Button("🔍 Aperçu seul", variant="secondary", scale=1)
                            save_scan_btn = gr.Button("💾 Sauver config", variant="secondary", scale=1)

                        scan_status = gr.Markdown("")

                    # === COLONNE DROITE: Résultats ===
                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Résultat du scan")

                        scan_summary = gr.Markdown("*Sélectionne un dossier et clique sur Scanner*")

                        scan_config_output = gr.Textbox(
                            label="Configuration générée (modifiable)",
                            lines=25,
                            max_lines=40,
                            interactive=True,
                            placeholder="La configuration apparaîtra ici..."
                        )

                # === OPTION ZIP ===
                with gr.Accordion("📦 Alternative: Upload ZIP", open=False):
                    gr.Markdown("*Pour scanner un projet depuis une autre machine*")
                    with gr.Row():
                        zip_file_upload = gr.File(
                            label="📦 projet.zip",
                            file_types=[".zip"],
                            type="filepath",
                            scale=2
                        )
                        zip_project_name = gr.Textbox(
                            label="📝 Nom",
                            placeholder="mon-projet",
                            max_lines=1,
                            scale=1
                        )
                        scan_zip_btn = gr.Button("🔍 Scanner", variant="primary", scale=1)
                    zip_scan_status = gr.Markdown("")

            # ═══════════════════════════════════════════════════════════
            # TAB 4: TEMPLATES MÉTIERS
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("👔 Templates Métiers", id="tab-templates"):
                gr.Markdown("## 👔 Créez votre profil métier")
                gr.Markdown("""
**Deux options pour créer rapidement ton profil:**
- 🚀 **Assistant Guidé** : Réponds à quelques questions et on génère ta config !
- 📄 **Templates Manuels** : Copie un template et personnalise-le toi-même
                """)
                
                with gr.Tabs():
                    # Sous-tab: Assistant Guidé
                    with gr.Tab("🚀 Assistant Guidé"):
                        gr.Markdown("### 🚀 Crée ton profil en 5 minutes!")
                        gr.Markdown("Réponds aux questions et PromptForge génère automatiquement ton fichier de contexte. **C'est la méthode recommandée!**")
                        
                        # États pour le wizard
                        wizard_answers = gr.State({})
                        wizard_step = gr.State(0)
                        wizard_profession = gr.State("")
                        
                        # Sélection du métier
                        with gr.Group() as wizard_start_group:
                            profession_choices = [(flow["name"], key) for key, flow in ONBOARDING_FLOWS.items()]
                            
                            wizard_profession_dropdown = gr.Dropdown(
                                label="🎯 Choisis ton métier",
                                choices=[name for name, _ in profession_choices],
                                value=None,
                                interactive=True,
                                info="Sélectionne ton domaine pour personnaliser les questions"
                            )
                            
                            wizard_welcome_msg = gr.Markdown("")
                            wizard_start_btn = gr.Button(
                                "▶️ Démarrer l'assistant",
                                variant="primary",
                                visible=False,
                                size="lg"
                            )
                        
                        # Questions
                        with gr.Group(visible=False) as wizard_questions_group:
                            wizard_progress = gr.Markdown("**Étape 1/5**")
                            wizard_step_title = gr.Markdown("### 📝 Questions")
                            
                            # Champs de questions (génériques)
                            wq_text_1 = gr.Textbox(label="Q1", visible=False, interactive=True)
                            wq_text_2 = gr.Textbox(label="Q2", visible=False, interactive=True)
                            wq_textarea = gr.Textbox(label="QTA", visible=False, lines=4, interactive=True)
                            wq_select_1 = gr.Dropdown(label="QS1", visible=False, interactive=True, allow_custom_value=True)
                            wq_select_2 = gr.Dropdown(label="QS2", visible=False, interactive=True, allow_custom_value=True)
                            wq_multiselect = gr.Dropdown(label="QMS", visible=False, multiselect=True, interactive=True, allow_custom_value=True)
                            wq_number = gr.Number(label="QN", visible=False, interactive=True)
                            wq_slider = gr.Slider(label="QSL", visible=False, minimum=0, maximum=100, interactive=True)
                            
                            with gr.Row():
                                wizard_prev_btn = gr.Button("⬅️ Précédent", variant="secondary")
                                wizard_next_btn = gr.Button("Suivant ➡️", variant="primary")
                        
                        # Résultat
                        with gr.Group(visible=False) as wizard_result_group:
                            gr.Markdown("### ✅ Ton profil est prêt!")
                            
                            wizard_result = gr.Textbox(
                                label="Configuration générée",
                                lines=18,
                                max_lines=25,
                                interactive=False
                            )
                            
                            with gr.Row():
                                wizard_project_name = gr.Textbox(
                                    label="Nom du projet",
                                    placeholder="ex: mon-projet-seo",
                                    scale=2
                                )
                                wizard_save_btn = gr.Button("💾 Sauvegarder le projet", variant="primary", scale=1)
                            
                            wizard_save_status = gr.Markdown("")
                            
                            with gr.Row():
                                wizard_restart_btn = gr.Button("🔄 Recommencer", variant="secondary")
                    
                    # Sous-tab: Templates Manuels
                    with gr.Tab("📄 Templates Manuels"):
                        gr.Markdown("### 📄 Templates prêts à l'emploi")
                        gr.Markdown("Sélectionne un template, personnalise-le et sauvegarde-le comme projet.")
                        
                        with gr.Row():
                            template_dropdown = gr.Dropdown(
                                label="📋 Sélectionner un template",
                                choices=[name for name, _ in get_template_choices()],
                                interactive=True,
                                scale=2
                            )
                            template_load_btn = gr.Button("📂 Charger", variant="secondary", scale=1)
                        
                        template_preview = gr.Markdown("*Sélectionne un template pour voir son contenu*")
                        
                        gr.Markdown("---")
                        gr.Markdown("**💡 Conseil:** Après avoir chargé un template, personnalise-le dans l'onglet **Projets** en cliquant sur 'Écrire manuellement'.")
            
            # ═══════════════════════════════════════════════════════════
            # TAB 5: HISTORIQUE
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("📜 Historique", id="tab-history"):
                gr.Markdown("## 📜 Historique des reformatages")
                gr.Markdown("Retrouve tous tes prompts reformatés précédemment.")
                
                with gr.Row():
                    history_filter = gr.Dropdown(
                        label="🔍 Filtrer par projet",
                        choices=["Tous"] + get_projects_list(),
                        value="Tous",
                        interactive=True,
                        scale=2
                    )
                    history_limit = gr.Slider(
                        label="📊 Nombre de résultats",
                        minimum=5,
                        maximum=50,
                        value=10,
                        step=5,
                        scale=2
                    )
                    refresh_history_btn = gr.Button("🔄", variant="secondary", scale=0, min_width=60)
                
                history_display = gr.Markdown(get_history_display("Tous", 10))
            
            # ═══════════════════════════════════════════════════════════
            # TAB 6: GÉNÉRER CONFIG
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("🎯 Générer config", id="tab-generate"):
                gr.Markdown("## 🎯 Générer une configuration projet")
                gr.Markdown("""
**Comment ça marche:**
1. 📋 Copie le prompt ci-dessous
2. 💬 Colle-le dans **Claude, ChatGPT, Gemini ou ton LLM préféré**
3. 💡 Réponds aux questions posées par l'IA
4. 📄 Copie la configuration Markdown générée
5. ✅ Colle-la dans l'onglet **Projets** pour créer ton projet
                """)
                
                gr.Markdown("---")
                
                config_prompt_display = gr.Textbox(
                    label="📋 Prompt à copier",
                    value=CONFIG_GENERATOR_PROMPT,
                    lines=30,
                    max_lines=40,
                    interactive=False
                )
                
                copy_prompt_btn = gr.Button("📋 Copier le prompt", variant="primary", size="lg")
                
                gr.Markdown("""
---
### 💡 Astuce
Plus tu donnes de détails à l'IA, meilleure sera ta configuration! N'hésite pas à être précis sur:
- Ta stack technique exacte avec les versions
- Tes conventions de code
- Les règles métier importantes
- Les erreurs à éviter
                """)
            
            # ═══════════════════════════════════════════════════════════
            # TAB 7: COMPARAISON
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("💰 Comparaison", id="tab-comparison"):
                gr.Markdown("## 💰 Comparaison des modèles LLM")
                gr.Markdown("Tous les prix sont en **$ par million de tokens** (décembre 2025).")
                
                comparison_table_display = gr.Markdown(get_comparison_table())
                
                gr.Markdown("---")
                gr.Markdown("### 💵 Calculateur de coût")
                
                with gr.Row():
                    input_tokens = gr.Number(
                        label="📥 Tokens en entrée",
                        value=1000,
                        minimum=100,
                        info="Nombre de tokens de ton prompt"
                    )
                    output_tokens = gr.Number(
                        label="📤 Tokens en sortie",
                        value=500,
                        minimum=100,
                        info="Nombre de tokens générés"
                    )
                    calc_cost_btn = gr.Button("💵 Calculer le coût", variant="primary")
                
                cost_result = gr.Markdown("")
                
                gr.Markdown("""
---
### 💡 Recommandations par cas d'usage

| Tâche | 🏆 Meilleur | ⚡ Équilibré | 💰 Budget |
|-------|------------|-------------|-----------|
| **Code complexe** | Claude Opus 4.5 | Claude Sonnet 4.5 | GPT-4o Mini |
| **Chat / Assistant** | GPT-4o | Gemini 2 Flash | Claude Haiku |
| **Analyse longue** | Gemini 2 Pro (1M!) | Claude Sonnet 4.5 | GPT-4o Mini |
| **Créativité** | GPT-4o | Claude Sonnet 4.5 | Gemini 2 Flash |
| **Volume élevé** | GPT-4o Mini | Claude Haiku | Gemini 2 Flash |
                """)
            
            # ═══════════════════════════════════════════════════════════
            # TAB 8: AIDE
            # ═══════════════════════════════════════════════════════════
            with gr.Tab("❓ Aide", id="tab-help"):
                gr.Markdown("""
## 📖 Guide complet de PromptForge

### 🚀 Démarrage rapide

#### Étape 1: Crée ton premier projet
1. Va dans l'onglet **👔 Templates Métiers**
2. Utilise l'**Assistant Guidé** pour créer un profil en 2 minutes
3. Ou utilise le **🔍 Scanner** pour analyser un projet existant

#### Étape 2: Reformate tes prompts
1. Va dans l'onglet **✨ Reformater**
2. Sélectionne ton projet
3. Entre ton prompt brut
4. Clique sur **Reformater**
5. Copie le résultat enrichi!

---

### 🎯 Comprendre les profils

| Profil | LLM cible | Format |
|--------|-----------|--------|
| **⚪ Universel** | Tous | Mixte compatible |
| **🟣 Claude** | Claude 4.x | XML structuré |
| **🟢 GPT** | GPT-4/4o | Markdown enrichi |
| **🔵 Gemini** | Gemini 2 | XML adapté |

---

### 🔍 Le Scanner automatique

Le scanner analyse ton projet et détecte automatiquement:
- Les langages utilisés
- Les frameworks
- La structure des dossiers
- Les dépendances
- Le README

**Comment l'utiliser:**
1. Entre le chemin de ton projet
2. Utilise le navigateur pour sélectionner le dossier
3. Clique sur **Scanner**
4. Vérifie et ajuste la config générée
5. Sauvegarde comme projet

---

### 🤖 Modèles Ollama recommandés

| Modèle | Usage | RAM nécessaire |
|--------|-------|----------------|
| `qwen3:8b` | Équilibré qualité/vitesse | 8 GB |
| `qwen3:14b` | Haute qualité | 16 GB |
| `phi4-mini` | Rapide, bon pour CPU | 4 GB |
| `llama3.2:3b` | Ultra-rapide | 4 GB |

**Installation:**
```bash
ollama pull qwen3:8b
```

---

### ⌨️ Raccourcis utiles

| Raccourci | Action |
|-----------|--------|
| `Ctrl+C` | Copier le prompt reformaté |
| `Ctrl+V` | Coller dans le champ de saisie |
| `Tab` | Naviguer entre les champs |

---

### 🔧 Troubleshooting

| Problème | Solution |
|----------|----------|
| **Ollama non disponible** | Lance `ollama serve` dans un terminal |
| **Modèle non trouvé** | `ollama pull nom-du-modele` |
| **Reformatage lent** | Utilise un modèle plus léger (phi4-mini) |
| **Interface ne charge pas** | Vérifie Python 3.10+ et Gradio 6+ |
| **Erreur de connexion** | Vérifie que le port 11434 est libre |

---

### 📞 Support

- 📚 Documentation: [GitHub](https://github.com/ton-repo/promptforge)
- 🐛 Bugs: Ouvre une issue sur GitHub
- 💡 Suggestions: Bienvenues via les issues!
                """)
        
        # ═══════════════════════════════════════════════════════════════
        # EVENT HANDLERS
        # ═══════════════════════════════════════════════════════════════
        
        # --- Ollama ---
        refresh_ollama_btn.click(
            fn=lambda: (check_ollama_status(), gr.update(choices=get_ollama_models())),
            outputs=[ollama_status, ollama_model_select]
        )
        
        ollama_model_select.change(
            fn=change_ollama_model,
            inputs=[ollama_model_select],
            outputs=[ollama_status]
        )

        # --- Reformater ---
        format_btn.click(
            fn=format_prompt_with_ollama,
            inputs=[raw_prompt, project_select, profile_select, check_cves_checkbox],
            outputs=[formatted_output, format_status, stats_html, analysis_output, recommendation_output, security_alerts_output]
        )
        
        profile_select.change(
            fn=get_profile_info,
            inputs=[profile_select],
            outputs=[profile_info]
        )
        
        project_select.change(
            fn=select_project,
            inputs=[project_select],
            outputs=[project_config_display, format_status]
        )
        
        def show_project_config(name):
            if not name or name == SANS_PROJET:
                return "*Aucun projet sélectionné*"
            config = get_project_config(name)
            return config if config else "*Configuration non trouvée*"
        
        project_select.change(
            fn=show_project_config,
            inputs=[project_select],
            outputs=[project_config_display]
        )
        
        # --- Projets ---
        # Wrappers pour extraire le statut des fonctions qui retournent des tuples
        def save_project_wrapper(name, config):
            result = create_project_from_editor(name, config)
            status = result[0] if isinstance(result, tuple) else result
            projects = get_projects_list()
            return status, gr.update(choices=projects), gr.update(choices=projects)

        def upload_file_wrapper(file, name):
            result = upload_file(file, name)
            status = result[0] if isinstance(result, tuple) else result
            projects = get_projects_list()
            return status, gr.update(choices=projects), gr.update(choices=projects)

        def delete_project_wrapper(name):
            result = delete_project(name)
            status = result[0] if isinstance(result, tuple) else result
            # Retourne aussi les mises à jour des dropdowns
            projects = get_projects_list()
            return status, gr.update(choices=projects, value=None), gr.update(choices=projects, value=None)

        save_btn.click(
            fn=save_project_wrapper,
            inputs=[new_project_name, config_editor],
            outputs=[project_status, projects_list_dropdown, project_select]
        )

        upload_btn.click(
            fn=upload_file_wrapper,
            inputs=[config_file, new_project_name],
            outputs=[project_status, projects_list_dropdown, project_select]
        )

        load_btn.click(
            fn=load_project_to_editor,
            inputs=[projects_list_dropdown],
            outputs=[new_project_name, config_editor]
        )

        projects_list_dropdown.change(
            fn=show_project_config,
            inputs=[projects_list_dropdown],
            outputs=[project_preview]
        )

        delete_btn.click(
            fn=delete_project_wrapper,
            inputs=[projects_list_dropdown],
            outputs=[project_status, projects_list_dropdown, project_select]
        )
        
        # --- Scanner: Browse button ---
        def on_browse_click():
            """Ouvre le dialogue système pour sélectionner un dossier."""
            folder_path = browse_for_folder()
            if not folder_path:
                return "", "*Aucun dossier sélectionné*", ""

            # Obtenir les infos du dossier
            info = get_folder_info(folder_path)

            # Suggérer un nom basé sur le nom du dossier
            suggested_name = Path(folder_path).name.lower().replace(" ", "-").replace("_", "-")

            return folder_path, info, suggested_name

        browse_btn.click(
            fn=on_browse_click,
            outputs=[scan_path, folder_info, scan_project_name]
        )

        # Mise à jour des infos quand le chemin change manuellement
        def on_path_change(path_str):
            if not path_str:
                return "*Entre un chemin ou clique sur Parcourir*", ""
            info = get_folder_info(path_str)
            suggested_name = Path(path_str).name.lower().replace(" ", "-").replace("_", "-")
            return info, suggested_name

        scan_path.change(
            fn=on_path_change,
            inputs=[scan_path],
            outputs=[folder_info, scan_project_name]
        )

        # Scan simple (aperçu)
        def do_scan(path, name, description, depth, use_ai, check_cves):
            """Effectue le scan avec ou sans IA."""
            if not path:
                return "❌ Sélectionne un dossier", "", ""
            if not name:
                return "❌ Entre un nom de projet", "", ""

            if use_ai:
                return generate_config_with_llm(path, name, description, depth, check_cves=check_cves)
            else:
                return scan_directory_for_ui(path, name, description, depth, check_cves=check_cves)

        scan_btn.click(
            fn=do_scan,
            inputs=[scan_path, scan_project_name, scan_description, scan_depth, use_ai_scan, scan_check_cves],
            outputs=[scan_status, scan_summary, scan_config_output]
        )

        # Scan + création projet
        def scan_and_create_project(path, name, description, depth, use_ai, check_cves):
            """Scan + création de projet en une seule action."""
            if not path:
                return "", "", "❌ Sélectionne un dossier avec le bouton Parcourir", gr.update(), gr.update()
            if not name:
                return "", "", "❌ Entre un nom de projet", gr.update(), gr.update()

            # 1. Scanner (avec ou sans IA)
            if use_ai:
                status, summary, config = generate_config_with_llm(path, name, description, depth, check_cves=check_cves)
            else:
                status, summary, config = scan_directory_for_ui(path, name, description, depth, check_cves=check_cves)

            if "❌" in status:
                return config, summary, status, gr.update(), gr.update()

            # 2. Créer le projet
            result = create_project_from_editor(name, config)
            create_status = result[0] if isinstance(result, tuple) else result

            if "✅" in create_status:
                forge = get_forge()
                forge.db.set_active_project(name)
                final_status = f"✅ Projet **{name}** scanné et créé ! Va dans 'Reformater' pour l'utiliser."
                projects = get_projects_list()
                return (
                    config, summary, final_status,
                    gr.update(choices=projects, value=name),
                    gr.update(choices=projects)
                )

            return config, summary, create_status, gr.update(), gr.update()

        scan_and_create_btn.click(
            fn=scan_and_create_project,
            inputs=[scan_path, scan_project_name, scan_description, scan_depth, use_ai_scan, scan_check_cves],
            outputs=[scan_config_output, scan_summary, scan_status, project_select, projects_list_dropdown]
        )

        def save_scanned_project(name, config):
            if not name or not config:
                return "⚠️ Nom et configuration requis"
            result = create_project_from_editor(name, config)
            return result[0] if isinstance(result, tuple) else result

        save_scan_btn.click(
            fn=save_scanned_project,
            inputs=[scan_project_name, scan_config_output],
            outputs=[scan_status]
        ).then(
            fn=lambda: gr.update(choices=get_projects_list()),
            outputs=[project_select]
        )

        # --- Scanner ZIP ---
        def scan_zip_and_create_project(zip_file, name, description, depth):
            """Scan un ZIP uploadé et crée le projet."""
            if not zip_file:
                return "❌ Uploade un fichier ZIP", "", ""
            if not name:
                return "❌ Entre un nom de projet", "", ""

            # Scanner le ZIP
            status, summary, config = scan_uploaded_zip(zip_file, name, description, depth)

            if "❌" in status:
                return status, summary, config

            # Créer le projet directement
            result = create_project_from_editor(name, config)
            create_status = result[0] if isinstance(result, tuple) else result

            if "✅" in create_status:
                forge = get_forge()
                forge.db.set_active_project(name)
                final_status = f"✅ Projet **{name}** créé depuis le ZIP ! Va dans 'Reformater' pour l'utiliser."
                return final_status, summary, config

            return create_status, summary, config

        scan_zip_btn.click(
            fn=scan_zip_and_create_project,
            inputs=[zip_file_upload, zip_project_name, scan_description, scan_depth],
            outputs=[zip_scan_status, scan_summary, scan_config_output]
        ).then(
            fn=lambda: gr.update(choices=get_projects_list()),
            outputs=[project_select]
        ).then(
            fn=lambda: gr.update(choices=get_projects_list()),
            outputs=[projects_list_dropdown]
        )

        # --- Templates ---
        template_dropdown.change(
            fn=load_template_by_name,
            inputs=[template_dropdown],
            outputs=[template_preview]
        )
        
        template_load_btn.click(
            fn=load_template_by_name,
            inputs=[template_dropdown],
            outputs=[template_preview]
        )
        
        # --- Historique ---
        def update_history(project_filter, limit):
            return get_history_display(project_filter, int(limit))
        
        history_filter.change(
            fn=update_history,
            inputs=[history_filter, history_limit],
            outputs=[history_display]
        )
        
        history_limit.change(
            fn=update_history,
            inputs=[history_filter, history_limit],
            outputs=[history_display]
        )
        
        refresh_history_btn.click(
            fn=update_history,
            inputs=[history_filter, history_limit],
            outputs=[history_display]
        )
        
        # --- Comparaison ---
        calc_cost_btn.click(
            fn=calculate_costs,
            inputs=[input_tokens, output_tokens],
            outputs=[cost_result]
        )
        
        # --- Wizard (Templates Métiers) ---
        def on_profession_selected(profession_name):
            """Quand un métier est sélectionné, affiche le message de bienvenue."""
            if not profession_name:
                return "", gr.update(visible=False)

            # Trouver la clé du flow
            flow_key = None
            for key, flow in ONBOARDING_FLOWS.items():
                if flow["name"] == profession_name:
                    flow_key = key
                    break

            if not flow_key:
                return "", gr.update(visible=False)

            flow = ONBOARDING_FLOWS[flow_key]

            # Compter le total de questions dans tous les steps
            total_questions = sum(len(step.questions) for step in flow.get('steps', []))
            num_steps = len(flow.get('steps', []))

            welcome = f"""
### 👋 Bienvenue, {flow['name']}!

{flow.get('welcome', 'Nous allons créer ensemble ta configuration personnalisée.')}

**{num_steps} étapes, ~{total_questions} questions** pour générer un profil adapté à ton métier.
            """

            return welcome, gr.update(visible=True)
        
        wizard_profession_dropdown.change(
            fn=on_profession_selected,
            inputs=[wizard_profession_dropdown],
            outputs=[wizard_welcome_msg, wizard_start_btn]
        )
        
        # Logique complète du wizard serait ici (similaire à interface.py)
        # Pour simplifier, on garde la logique existante
        
        logger.info("Interface v4 created successfully")
    
    return interface


def launch_web(
    host: str = "0.0.0.0",
    port: int = 7860,
    share: bool = False,
    base_path: str = None
):
    """Lance l'interface web."""
    if base_path:
        set_base_path(base_path)
    
    logger.info(f"Launching interface v4 on {host}:{port}")
    
    interface = create_interface()
    
    # Favicon
    favicon_path = None
    possible_paths = [
        Path(__file__).parent.parent.parent / "assets" / "favicon.svg",
        Path("assets") / "favicon.svg",
    ]
    for p in possible_paths:
        if p.exists():
            favicon_path = str(p)
            break
    
    interface.launch(
        server_name=host,
        server_port=port,
        share=share,
        favicon_path=favicon_path,
        show_error=True
    )


if __name__ == "__main__":
    launch_web()
