"""
Tests pour le système d'onboarding guidé.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOnboardingFlows:
    """Tests pour les flows d'onboarding."""

    def test_import_onboarding(self):
        """Vérifie que le module onboarding est importable."""
        from promptforge.web.onboarding import (
            ONBOARDING_FLOWS,
            get_available_professions,
            get_onboarding_flow,
            generate_context_from_answers
        )
        assert callable(get_available_professions)
        assert callable(get_onboarding_flow)
        assert callable(generate_context_from_answers)

    def test_onboarding_flows_exist(self):
        """Vérifie que les flows d'onboarding existent."""
        from promptforge.web.onboarding import ONBOARDING_FLOWS
        
        expected_professions = [
            'seo-specialist',
            'marketing-digital',
            'dev-backend',
            'product-manager',
            'commercial-sales',
            'rh-recruteur',
            'data-analyst',
            'support-client',
        ]
        
        for profession in expected_professions:
            assert profession in ONBOARDING_FLOWS, f"Flow manquant: {profession}"

    def test_flow_structure(self):
        """Vérifie la structure d'un flow."""
        from promptforge.web.onboarding import ONBOARDING_FLOWS
        
        for key, flow in ONBOARDING_FLOWS.items():
            assert "name" in flow, f"{key}: 'name' manquant"
            assert "welcome" in flow, f"{key}: 'welcome' manquant"
            assert "steps" in flow, f"{key}: 'steps' manquant"
            assert len(flow["steps"]) >= 3, f"{key}: moins de 3 étapes"

    def test_step_structure(self):
        """Vérifie la structure des étapes."""
        from promptforge.web.onboarding import ONBOARDING_FLOWS
        
        for key, flow in ONBOARDING_FLOWS.items():
            for i, step in enumerate(flow["steps"]):
                assert hasattr(step, "title"), f"{key} step {i}: 'title' manquant"
                assert hasattr(step, "description"), f"{key} step {i}: 'description' manquant"
                assert hasattr(step, "questions"), f"{key} step {i}: 'questions' manquant"
                assert len(step.questions) >= 1, f"{key} step {i}: pas de questions"

    def test_question_structure(self):
        """Vérifie la structure des questions."""
        from promptforge.web.onboarding import ONBOARDING_FLOWS, QuestionType
        
        for key, flow in ONBOARDING_FLOWS.items():
            for step in flow["steps"]:
                for q in step.questions:
                    assert hasattr(q, "id"), f"Question sans id dans {key}"
                    assert hasattr(q, "label"), f"Question sans label dans {key}"
                    assert hasattr(q, "question_type"), f"Question sans type dans {key}"
                    assert isinstance(q.question_type, QuestionType)


class TestContextGeneration:
    """Tests pour la génération de contexte."""

    def test_generate_empty_answers(self):
        """Génère un contexte avec des réponses vides."""
        from promptforge.web.onboarding import generate_context_from_answers
        
        result = generate_context_from_answers('seo-specialist', {})
        
        assert result is not None
        assert len(result) > 100
        assert "# Configuration Projet" in result

    def test_generate_with_answers(self):
        """Génère un contexte avec des réponses."""
        from promptforge.web.onboarding import generate_context_from_answers
        
        answers = {
            'level': 'Senior (3-5 ans)',
            'site_url': 'mon-site.fr',
            'site_type': 'Blog',
            'site_niche': 'Jardinage',
            'domain_rating': 25,
        }
        
        result = generate_context_from_answers('seo-specialist', answers)
        
        assert "mon-site.fr" in result
        assert "Jardinage" in result
        assert "Blog" in result

    def test_generate_includes_llm_instructions(self):
        """Vérifie que les instructions LLM sont incluses."""
        from promptforge.web.onboarding import generate_context_from_answers
        
        result = generate_context_from_answers('dev-backend', {'level': 'Senior'})
        
        assert "Instructions pour le LLM" in result
        assert "Utilise mon contexte" in result

    def test_generate_for_all_professions(self):
        """Génère un contexte pour chaque métier."""
        from promptforge.web.onboarding import ONBOARDING_FLOWS, generate_context_from_answers
        
        for profession_key in ONBOARDING_FLOWS.keys():
            result = generate_context_from_answers(profession_key, {})
            assert result is not None, f"Génération échouée pour {profession_key}"
            assert len(result) > 200, f"Contexte trop court pour {profession_key}"


class TestGetFunctions:
    """Tests pour les fonctions d'accès."""

    def test_get_available_professions(self):
        """Vérifie la liste des professions disponibles."""
        from promptforge.web.onboarding import get_available_professions
        
        professions = get_available_professions()
        
        assert isinstance(professions, list)
        assert len(professions) >= 8
        
        for name, key in professions:
            assert isinstance(name, str)
            assert isinstance(key, str)
            assert len(name) > 0
            assert len(key) > 0

    def test_get_onboarding_flow(self):
        """Vérifie la récupération d'un flow."""
        from promptforge.web.onboarding import get_onboarding_flow
        
        flow = get_onboarding_flow('seo-specialist')
        assert flow is not None
        assert "name" in flow
        assert "steps" in flow

    def test_get_nonexistent_flow(self):
        """Vérifie le comportement avec un flow inexistant."""
        from promptforge.web.onboarding import get_onboarding_flow
        
        flow = get_onboarding_flow('metier-qui-nexiste-pas')
        assert flow is None


class TestQuestionTypes:
    """Tests pour les types de questions."""

    def test_all_question_types_used(self):
        """Vérifie que tous les types de questions sont utilisés."""
        from promptforge.web.onboarding import ONBOARDING_FLOWS, QuestionType
        
        used_types = set()
        
        for flow in ONBOARDING_FLOWS.values():
            for step in flow["steps"]:
                for q in step.questions:
                    used_types.add(q.question_type)
        
        # Au moins TEXT, SELECT, MULTISELECT doivent être utilisés
        assert QuestionType.TEXT in used_types
        assert QuestionType.SELECT in used_types
        assert QuestionType.MULTISELECT in used_types

    def test_select_questions_have_options(self):
        """Vérifie que les SELECT ont des options."""
        from promptforge.web.onboarding import ONBOARDING_FLOWS, QuestionType
        
        for key, flow in ONBOARDING_FLOWS.items():
            for step in flow["steps"]:
                for q in step.questions:
                    if q.question_type in [QuestionType.SELECT, QuestionType.MULTISELECT]:
                        assert len(q.options) >= 2, f"{key}: {q.id} a moins de 2 options"
