# PromptForge Makefile
# Usage: make <target>

.PHONY: help install install-dev test test-cov lint format clean docker-start docker-stop docker-status docker-run docker-clean web

# Variables
PYTHON := python3
PIP := pip
PYTEST := pytest
BLACK := black
RUFF := ruff

# Couleurs
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
NC := \033[0m

help: ## Afficher cette aide
	@echo "$(BLUE)PromptForge$(NC) - Reformateur intelligent de prompts"
	@echo ""
	@echo "$(GREEN)Targets disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================
# Installation
# ============================================

install: ## Installer le package
	$(PIP) install -e .

install-dev: ## Installer avec dépendances de développement
	$(PIP) install -e ".[dev]"

install-web: ## Installer avec interface web (Gradio)
	$(PIP) install -e ".[web]"

install-all: ## Installer toutes les dépendances
	$(PIP) install -e ".[all]"

# ============================================
# Tests
# ============================================

test: ## Lancer les tests
	$(PYTEST) tests/ -v

test-cov: ## Lancer les tests avec couverture
	$(PYTEST) tests/ -v --cov=promptforge --cov-report=html --cov-report=term-missing

test-fast: ## Lancer les tests sans les tests d'intégration
	$(PYTEST) tests/ -v -m "not integration"

# ============================================
# Qualité de code
# ============================================

lint: ## Vérifier le code avec ruff
	$(RUFF) check promptforge/ tests/

format: ## Formater le code avec black
	$(BLACK) promptforge/ tests/

format-check: ## Vérifier le formatage sans modifier
	$(BLACK) --check promptforge/ tests/

# ============================================
# Docker (cross-platform via Python)
# ============================================

docker-build: ## Construire l'image Docker
	docker compose build promptforge

docker-start: ## Démarrer Ollama + télécharger le modèle
	$(PYTHON) scripts/docker_helper.py start

docker-stop: ## Arrêter les services Docker
	$(PYTHON) scripts/docker_helper.py stop

docker-status: ## Statut des services Docker
	$(PYTHON) scripts/docker_helper.py status

docker-logs: ## Logs Ollama
	$(PYTHON) scripts/docker_helper.py logs

docker-run: ## Exécuter une commande (usage: make docker-run CMD="list")
	$(PYTHON) scripts/docker_helper.py run $(CMD)

docker-shell: ## Shell interactif dans le conteneur
	$(PYTHON) scripts/docker_helper.py shell

docker-clean: ## Supprimer conteneurs et volumes Docker
	$(PYTHON) scripts/docker_helper.py clean

# ============================================
# Interface Web
# ============================================

web: ## Lancer l'interface web Gradio
	promptforge web

web-public: ## Lancer l'interface web avec lien public
	promptforge web --host 0.0.0.0 --share

docker-web: ## Lancer l'interface web via Docker
	$(PYTHON) scripts/docker_helper.py web

# ============================================
# Développement
# ============================================

dev-setup: install-dev ## Setup complet pour développement
	@echo "$(GREEN)✓ Environnement de développement prêt$(NC)"

check: lint format-check test ## Vérifications complètes (lint + format + tests)
	@echo "$(GREEN)✓ Toutes les vérifications passées$(NC)"

# ============================================
# Nettoyage
# ============================================

clean: ## Nettoyer les fichiers générés
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-data: ## Nettoyer les données (DB + historique)
	rm -f promptforge.db
	rm -rf history/*
	@echo "$(YELLOW)⚠ Données supprimées$(NC)"

# ============================================
# Release
# ============================================

build-dist: clean ## Construire le package pour distribution
	$(PYTHON) -m build

publish-test: build-dist ## Publier sur TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*

publish: build-dist ## Publier sur PyPI
	$(PYTHON) -m twine upload dist/*
