"""
Assistant guide — logique de parcours (DEC-012).

Ce module contient **tout** le pilotage de l'assistant : plan d'affichage
d'une etape, collecte des reponses, navigation, sauvegarde. `interface.py`
ne fait plus qu'assembler les composants et brancher ces fonctions.

Il ne contient aucune logique metier : le questionnaire et la generation du
contexte appartiennent a `onboarding.py`, l'enregistrement d'un projet a
`core.PromptForge`. Ce module les appelle, il ne les recalcule pas.

Contrainte centrale — **aucune question perdue**
-----------------------------------------------
Les huit flux comptent 123 questions reparties sur 41 etapes. Mesure du
2026-09-07 sur `ONBOARDING_FLOWS` :

    questions dans une meme etape, maximum ......... 5
    par type dans une meme etape : select 4, multiselect 2, text 2,
                                   number 1, textarea 1, slider 1

L'ancienne interface n'offrait que huit champs fixes, dont **deux** listes
deroulantes simples et **une** liste multiple. Les cabler tels quels aurait
ampute silencieusement toute etape a trois selects ou plus — le piege exact
de cette dette.

La parade retenue est un **pool positionnel** : `WIZARD_SLOT_COUNT` blocs de
`len(SLOT_TYPE_ORDER)` champs, un champ par type de question. La question
numero *i* d'une etape occupe le bloc *i*, et seul le champ correspondant a
son type y est rendu visible. Deux proprietes en decoulent :

  1. la capacite est **derivee de la donnee** (`max(len(step.questions))`),
     donc l'ajout d'une etape plus longue agrandit le pool au lieu de
     tronquer — l'oubli devient impossible par construction ;
  2. l'ordre d'affichage est **l'ordre d'ecriture** du questionnaire, ce
     qu'un pool par type n'aurait pas garanti.

Cout mesure : `WIZARD_SLOT_COUNT * len(SLOT_TYPE_ORDER)` composants poses a
la construction, dont un seul par bloc est visible a un instant donne.

Alternative ecartee : `@gr.render` (present en Gradio 6.26.0, verifie). Les
composants qu'il produit n'existent pas dans `app.blocks` au moment de
l'assemblage : la sonde de `tests/test_web_interface.py`, qui detecte les
composants cables a rien, deviendrait aveugle sur tout l'onglet. On ne paye
pas un confort d'implementation avec la perte du seul verrou qui a rendu
D-063 visible.
"""

import gradio as gr

from ..logging_config import get_logger
from .ollama_helpers import get_forge
from .onboarding import (
    ONBOARDING_FLOWS,
    Question,
    QuestionType,
    generate_context_from_answers,
    get_onboarding_flow,
)
from .project_helpers import get_projects_list, normalize_name

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CAPACITE DU POOL — DERIVEE DE LA DONNEE, JAMAIS DEVINEE
# ═══════════════════════════════════════════════════════════════════════════

#: Ordre des champs a l'interieur d'un bloc positionnel. Un champ par type de
#: question ; un seul est visible a la fois.
SLOT_TYPE_ORDER: tuple[QuestionType, ...] = (
    QuestionType.TEXT,
    QuestionType.TEXTAREA,
    QuestionType.SELECT,
    QuestionType.MULTISELECT,
    QuestionType.NUMBER,
    QuestionType.SLIDER,
)

#: Position d'un type dans un bloc.
SLOT_TYPE_INDEX: dict[QuestionType, int] = {
    question_type: index for index, question_type in enumerate(SLOT_TYPE_ORDER)
}

FIELDS_PER_SLOT = len(SLOT_TYPE_ORDER)


def _max_questions_per_step() -> int:
    """Plus grand nombre de questions portees par une seule etape.

    Mesure, pas constante : si un flux gagne une etape plus longue, le pool
    s'agrandit au lieu de tronquer. Le verrou de comptage de blocs de
    `tests/test_web_interface.py` rend l'agrandissement visible en revue.
    """
    return max(len(step.questions) for flow in ONBOARDING_FLOWS.values() for step in flow["steps"])


#: Nombre de blocs positionnels. Mesure du 2026-09-07 : 5.
WIZARD_SLOT_COUNT = _max_questions_per_step()

#: Nombre total de champs poses par l'interface pour l'assistant.
WIZARD_FIELD_COUNT = WIZARD_SLOT_COUNT * FIELDS_PER_SLOT

#: Nombre de sorties de navigation avant la liste des champs. Voir
#: `WIZARD_NAV_OUTPUT_NAMES` pour le contrat exact.
WIZARD_NAV_HEADER_COUNT = 12

#: Contrat de sortie des trois fonctions de navigation, dans l'ordre.
#: `interface.py` branche sa liste `outputs` sur cet ordre ; les tests s'en
#: servent pour lire un resultat sans construire l'application.
WIZARD_NAV_OUTPUT_NAMES = (
    "profession",  # State — cle du metier
    "step",  # State — index d'etape
    "answers",  # State — reponses accumulees
    "start_group",  # visibilite de l'ecran de demarrage
    "questions_group",  # visibilite de l'ecran de questions
    "result_group",  # visibilite de l'ecran de resultat
    "progress",  # Markdown — « Etape 2/6 »
    "step_title",  # Markdown — titre et description de l'etape
    "error",  # Markdown — etat d'erreur (champ requis manquant)
    "prev_btn",  # bouton « Precedent »
    "next_btn",  # bouton « Suivant » / « Terminer »
    "result",  # Textbox — contexte genere
)

assert len(WIZARD_NAV_OUTPUT_NAMES) == WIZARD_NAV_HEADER_COUNT


class WizardCapacityError(RuntimeError):
    """Une etape demande plus de blocs que le pool n'en offre.

    Ne peut pas survenir tant que `WIZARD_SLOT_COUNT` est derive de la
    donnee. Existe pour transformer en echec bruyant le jour ou quelqu'un
    figera la capacite a la main : mieux vaut une exception qu'un
    questionnaire ampute en silence.
    """


# ═══════════════════════════════════════════════════════════════════════════
# LECTURE DU FLUX
# ═══════════════════════════════════════════════════════════════════════════


def profession_key_from_label(label: str) -> str | None:
    """Retrouve la cle d'un metier depuis le libelle affiche dans le menu."""
    if not label:
        return None
    for key, flow in ONBOARDING_FLOWS.items():
        if flow["name"] == label:
            return key
    return None


def get_steps(profession_key: str) -> list:
    """Etapes d'un metier, liste vide si la cle est inconnue."""
    flow = get_onboarding_flow(profession_key)
    return list(flow["steps"]) if flow else []


def plan_step(profession_key: str, step_index: int) -> list[Question | None]:
    """Affectation question -> bloc positionnel, longueur `WIZARD_SLOT_COUNT`.

    La question *i* occupe le bloc *i*. Les blocs restants valent `None`.
    Aucune troncature : une etape trop longue leve `WizardCapacityError`.
    """
    steps = get_steps(profession_key)
    if not steps or not 0 <= step_index < len(steps):
        return [None] * WIZARD_SLOT_COUNT

    questions = steps[step_index].questions
    if len(questions) > WIZARD_SLOT_COUNT:
        raise WizardCapacityError(
            f"L'etape {step_index} de « {profession_key} » porte {len(questions)} "
            f"questions pour {WIZARD_SLOT_COUNT} blocs disponibles. Aucune question "
            f"ne doit etre perdue : agrandissez le pool au lieu de tronquer."
        )
    return list(questions) + [None] * (WIZARD_SLOT_COUNT - len(questions))


# ═══════════════════════════════════════════════════════════════════════════
# VALEURS
# ═══════════════════════════════════════════════════════════════════════════


def _default_number(raw: str, fallback: int) -> int:
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return fallback


def initial_value(question: Question, answers: dict):
    """Valeur a afficher pour une question : la reponse deja donnee, sinon le defaut."""
    if question.id in answers:
        return answers[question.id]
    if question.question_type is QuestionType.MULTISELECT:
        return []
    if question.question_type is QuestionType.SLIDER:
        return _default_number(question.default, question.min_value)
    if question.question_type is QuestionType.NUMBER:
        return _default_number(question.default, None) if question.default else None
    if question.question_type is QuestionType.SELECT:
        return question.default or None
    return question.default or ""


def normalise_answer(question: Question, value):
    """Ramene une valeur de composant Gradio a une reponse stockable."""
    if question.question_type is QuestionType.MULTISELECT:
        if value is None:
            return []
        return list(value) if isinstance(value, (list, tuple)) else [value]
    if question.question_type in (QuestionType.NUMBER, QuestionType.SLIDER):
        if value is None or value == "":
            return ""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        return int(number) if number.is_integer() else number
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else value


def is_answered(question: Question, answers: dict) -> bool:
    """Une question requise est-elle effectivement renseignee ?"""
    value = answers.get(question.id)
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    if isinstance(value, str):
        return value.strip() != ""
    return True


def collect_answers(profession_key: str, step_index: int, answers: dict, raw_values) -> dict:
    """Fusionne les valeurs saisies a l'etape courante dans les reponses.

    Rend une **copie** : l'etat Gradio n'est jamais mute en place, ce qui
    evite qu'un retour arriere partage une reference avec l'ecran precedent.
    Seuls les champs decrits par le plan de l'etape sont lus, donc la valeur
    residuelle d'un champ masque ne peut pas contaminer une autre question.
    """
    merged = dict(answers or {})
    raw = list(raw_values)
    for slot, question in enumerate(plan_step(profession_key, step_index)):
        if question is None:
            continue
        index = slot * FIELDS_PER_SLOT + SLOT_TYPE_INDEX[question.question_type]
        if index >= len(raw):
            raise WizardCapacityError(
                f"Le champ {index} de la question « {question.id} » n'a pas ete "
                f"transmis : {len(raw)} valeurs recues pour {WIZARD_FIELD_COUNT} "
                f"champs attendus. La reponse serait perdue en silence."
            )
        merged[question.id] = normalise_answer(question, raw[index])
    return merged


# ═══════════════════════════════════════════════════════════════════════════
# RENDU D'UNE ETAPE
# ═══════════════════════════════════════════════════════════════════════════


def field_updates(profession_key: str, step_index: int, answers: dict) -> list:
    """Mises a jour des `WIZARD_FIELD_COUNT` champs pour une etape."""
    plan = plan_step(profession_key, step_index)
    updates = []
    for question in plan:
        for question_type in SLOT_TYPE_ORDER:
            if question is not None and question.question_type is question_type:
                updates.append(_visible_update(question, answers))
            else:
                updates.append(gr.update(visible=False))
    return updates


def _visible_update(question: Question, answers: dict):
    label = f"{question.label}{' *' if question.required else ''}"
    common = {
        "visible": True,
        "label": label,
        "info": question.help_text or None,
        "value": initial_value(question, answers),
    }
    if question.question_type in (QuestionType.SELECT, QuestionType.MULTISELECT):
        return gr.update(choices=list(question.options), **common)
    if question.question_type in (QuestionType.NUMBER, QuestionType.SLIDER):
        return gr.update(minimum=question.min_value, maximum=question.max_value, **common)
    if question.question_type in (QuestionType.TEXT, QuestionType.TEXTAREA):
        return gr.update(placeholder=question.placeholder or None, **common)
    return gr.update(**common)


def _step_view(profession_key: str, step_index: int, answers: dict, error: str = "") -> tuple:
    """Ecran de questions, conforme a `WIZARD_NAV_OUTPUT_NAMES`."""
    steps = get_steps(profession_key)
    step = steps[step_index]
    is_last = step_index == len(steps) - 1

    return (
        profession_key,
        step_index,
        answers,
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        f"**Étape {step_index + 1}/{len(steps)}**",
        f"### {step.icon} {step.title}\n\n{step.description}",
        error,
        # « Precedent » n'existe pas comme action a la premiere etape.
        gr.update(visible=step_index > 0),
        gr.update(value="✅ Terminer" if is_last else "Suivant ➡️"),
        gr.update(),
        *field_updates(profession_key, step_index, answers),
    )


def _result_view(profession_key: str, answers: dict) -> tuple:
    """Ecran de resultat, conforme a `WIZARD_NAV_OUTPUT_NAMES`."""
    context = generate_context_from_answers(profession_key, answers)
    steps = get_steps(profession_key)
    return (
        profession_key,
        max(len(steps) - 1, 0),
        answers,
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        "",
        "",
        "",
        gr.update(visible=False),
        gr.update(),
        gr.update(value=context),
        *([gr.update(visible=False)] * WIZARD_FIELD_COUNT),
    )


def _idle_view(message: str = "") -> tuple:
    """Ecran de demarrage, conforme a `WIZARD_NAV_OUTPUT_NAMES`."""
    return (
        "",
        0,
        {},
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        "",
        "",
        message,
        gr.update(visible=False),
        gr.update(),
        gr.update(),
        *([gr.update(visible=False)] * WIZARD_FIELD_COUNT),
    )


# ═══════════════════════════════════════════════════════════════════════════
# GESTIONNAIRES
# ═══════════════════════════════════════════════════════════════════════════


def on_profession_selected(profession_label: str):
    """Message d'accueil et apparition du bouton de demarrage."""
    key = profession_key_from_label(profession_label)
    if key is None:
        return "", gr.update(visible=False)

    flow = ONBOARDING_FLOWS[key]
    steps = flow["steps"]
    total_questions = sum(len(step.questions) for step in steps)
    welcome = (
        f"### 👋 Bienvenue, {flow['name']} !\n\n"
        f"{flow.get('welcome', 'Nous allons créer ensemble ta configuration personnalisée.')}\n\n"
        f"**{len(steps)} étapes, {total_questions} questions** "
        f"pour générer un profil adapté à ton métier."
    )
    return welcome, gr.update(visible=True)


def start_wizard(profession_label: str) -> tuple:
    """Demarre le parcours a la premiere etape du metier choisi."""
    key = profession_key_from_label(profession_label)
    if key is None or not get_steps(key):
        return _idle_view("⚠️ Choisis d'abord un métier dans la liste.")
    logger.info("Wizard started", extra={"profession": key})
    return _step_view(key, 0, {})


def go_next(profession_key: str, step_index: int, answers: dict, *raw_values) -> tuple:
    """Enregistre l'etape courante puis avance — ou termine le parcours."""
    steps = get_steps(profession_key)
    if not steps:
        return _idle_view("⚠️ Parcours interrompu, recommence depuis le choix du métier.")

    step_index = max(0, min(int(step_index or 0), len(steps) - 1))
    merged = collect_answers(profession_key, step_index, answers, raw_values)

    missing = [
        question.label
        for question in steps[step_index].questions
        if question.required and not is_answered(question, merged)
    ]
    if missing:
        # Les reponses deja saisies sont conservees : on reaffiche la meme
        # etape avec `merged`, pas avec l'etat d'avant la saisie.
        return _step_view(
            profession_key,
            step_index,
            merged,
            "⚠️ Champ obligatoire manquant : " + ", ".join(missing),
        )

    if step_index >= len(steps) - 1:
        return _result_view(profession_key, merged)
    return _step_view(profession_key, step_index + 1, merged)


def go_prev(profession_key: str, step_index: int, answers: dict, *raw_values) -> tuple:
    """Recule d'une etape **sans perdre** ce qui vient d'etre saisi."""
    steps = get_steps(profession_key)
    if not steps:
        return _idle_view("⚠️ Parcours interrompu, recommence depuis le choix du métier.")

    step_index = max(0, min(int(step_index or 0), len(steps) - 1))
    merged = collect_answers(profession_key, step_index, answers, raw_values)
    return _step_view(profession_key, max(step_index - 1, 0), merged)


#: Contrat de sortie de `restart_wizard`.
WIZARD_RESTART_OUTPUT_NAMES = (
    "profession",
    "step",
    "answers",
    "start_group",
    "questions_group",
    "result_group",
    "profession_dropdown",
    "welcome_msg",
    "start_btn",
    "result",
    "project_name",
    "save_status",
)


def restart_wizard() -> tuple:
    """Remet le parcours a zero — les trois `State` compris."""
    return (
        "",
        0,
        {},
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(value=None),
        "",
        gr.update(visible=False),
        gr.update(value=""),
        gr.update(value=""),
        "",
    )


# ═══════════════════════════════════════════════════════════════════════════
# SAUVEGARDE — une sauvegarde qui echoue le dit (anti D-054)
# ═══════════════════════════════════════════════════════════════════════════

SAVE_PENDING_MESSAGE = "⏳ Sauvegarde en cours…"


def save_wizard_project(project_name: str, config_content: str):
    """Ecrit la config, enregistre le projet, l'active, **puis verifie**.

    Aucun message de succes n'est emis sans relecture effective : c'est la
    lecon de D-054, ou le CLI annoncait une sauvegarde qui n'avait pas eu
    lieu. Toute defaillance — disque, base, projet introuvable apres coup —
    ressort en message d'erreur.
    """
    if not (project_name or "").strip():
        return "❌ Nom de projet requis", gr.update(), gr.update()
    if not (config_content or "").strip():
        return (
            "❌ Configuration vide — termine d'abord l'assistant",
            gr.update(),
            gr.update(),
        )

    forge = get_forge()
    normalized = normalize_name(project_name.strip())
    config_path = forge.projects_path / f"{normalized}.md"

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content, encoding="utf-8")
    except OSError as error:
        logger.error(f"Wizard save failed on write: {error}")
        return f"❌ Écriture impossible ({config_path.name}) : {error}", gr.update(), gr.update()

    try:
        success, message = forge.init_project(normalized, str(config_path))
    except Exception as error:  # noqa: BLE001 — remonte tel quel a l'utilisateur
        logger.error(f"Wizard save failed on register: {error}")
        return f"❌ Enregistrement impossible : {error}", gr.update(), gr.update()

    if not success:
        projects = get_projects_list()
        return f"❌ {message}", gr.update(choices=projects), gr.update(choices=projects)

    forge.use_project(normalized)

    # Relecture : sans elle, le message de succes serait une declaration.
    projects = get_projects_list()
    if normalized not in projects:
        return (
            f"❌ Projet « {normalized} » introuvable après enregistrement — "
            f"rien n'a été sauvegardé.",
            gr.update(choices=projects),
            gr.update(choices=projects),
        )

    logger.info(f"Wizard project saved: {normalized}")
    return (
        f"✅ Projet « {normalized} » créé et activé",
        gr.update(choices=projects, value=normalized),
        gr.update(choices=projects, value=normalized),
    )
