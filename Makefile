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
	$(PYTHON) scripts/build.py status

docker-logs: ## Logs Ollama
	$(PYTHON) scripts/docker_helper.py logs

docker-run: ## Exécuter une commande (usage: make docker-run CMD="list")
	$(PYTHON) scripts/docker_helper.py run $(CMD)

docker-shell: ## Shell interactif dans le conteneur
	$(PYTHON) scripts/docker_helper.py shell

docker-clean: ## Supprimer conteneurs et volumes Docker
	$(PYTHON) scripts/build.py clean --force --images

# ============================================
# Build System (nouveau)
# ============================================

build: ## Construire les images Docker (auto-détection GPU)
	$(PYTHON) scripts/build.py build

build-nvidia: ## Construire pour NVIDIA
	$(PYTHON) scripts/build.py build -c nvidia

build-amd: ## Construire pour AMD
	$(PYTHON) scripts/build.py build -c amd

build-cpu: ## Construire pour CPU
	$(PYTHON) scripts/build.py build -c cpu

rebuild: ## Reconstruire sans cache
	$(PYTHON) scripts/build.py build --no-cache

up: ## Démarrer les services (auto-détection GPU)
	$(PYTHON) scripts/build.py up

down: ## Arrêter les services
	$(PYTHON) scripts/build.py down

launcher: ## Lancer le launcher GUI
	$(PYTHON) launcher.py

# ============================================
# Mise à jour Docker
# ============================================

update: ## Mettre à jour les images Docker (pull + rebuild + restart)
	@echo "$(BLUE)🔄 Mise à jour PromptForge...$(NC)"
	docker compose pull
	docker compose build
	docker compose up -d
	@echo "$(GREEN)✅ Mise à jour terminée!$(NC)"
	docker compose ps

update-force: ## Forcer reconstruction complète (sans cache)
	@echo "$(YELLOW)🔄 Reconstruction forcée (sans cache)...$(NC)"
	docker compose down
	docker compose build --no-cache --pull
	docker compose up -d
	@echo "$(GREEN)✅ Reconstruction terminée!$(NC)"
	docker compose ps

update-all: ## Mettre à jour + nettoyer les anciennes images
	@echo "$(BLUE)🔄 Mise à jour complète...$(NC)"
	docker compose down
	docker compose pull
	docker compose build --no-cache
	docker image prune -f
	docker compose up -d
	@echo "$(GREEN)✅ Mise à jour complète terminée!$(NC)"
	docker compose ps

# ============================================
# Docker AMD GPU (ROCm)
# ============================================

docker-amd: ## Démarrer avec GPU AMD (ROCm) - modèle 14B
	@echo "$(BLUE)🎮 Démarrage avec GPU AMD (qwen2.5:14b)...$(NC)"
	docker compose -f docker-compose.amd.yml up -d
	@echo "$(GREEN)✅ Interface: http://localhost:7860$(NC)"

docker-amd-max: ## Démarrer avec GPU AMD - modèle 32B (max qualité)
	@echo "$(BLUE)🎮 Démarrage avec GPU AMD MAX (qwen2.5:32b)...$(NC)"
	@echo "$(YELLOW)⚠️  Premier lancement: téléchargement ~18GB$(NC)"
	docker compose -f docker-compose.amd-max.yml up -d
	@echo "$(GREEN)✅ Interface: http://localhost:7860$(NC)"

docker-amd-stop: ## Arrêter les services AMD
	docker compose -f docker-compose.amd.yml down 2>/dev/null || true
	docker compose -f docker-compose.amd-max.yml down 2>/dev/null || true

docker-amd-logs: ## Logs AMD (vérifier détection GPU)
	docker compose -f docker-compose.amd.yml logs ollama 2>/dev/null || \
	docker compose -f docker-compose.amd-max.yml logs ollama

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
