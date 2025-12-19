# Structure du Projet PromptForge

## Vue d'ensemble

```
promptforge/
├── promptforge/              # 📦 Package Python principal
│   ├── __init__.py
│   ├── cli.py               # Interface ligne de commande
│   ├── core.py              # Logique métier centrale
│   ├── database.py          # Gestion base de données
│   ├── profiles.py          # Profils des modèles LLM
│   ├── providers.py         # Connecteurs Ollama/API
│   ├── utils.py             # Utilitaires
│   └── web.py               # Interface web Gradio
│
├── scripts/                  # 🔧 Scripts utilitaires
│   ├── build.py             # Système de build central
│   ├── docker_helper.py     # Aide Docker
│   └── docker-run.sh        # Script de démarrage Linux
│
├── tests/                    # 🧪 Tests unitaires et d'intégration
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_core.py
│   ├── test_database.py
│   ├── test_integration.py
│   └── test_providers.py
│
├── data/                     # 💾 Données persistantes
│   ├── projects/            # Projets utilisateur
│   └── history/             # Historique des reformatages
│
├── templates/                # 📝 Templates
│   └── PROJECT_GENERATOR_PROMPT.md
│
├── docs/                     # 📚 Documentation
│   └── STRUCTURE.md         # Ce fichier
│
├── docker-compose.yml        # 🐳 Docker Compose NVIDIA (défaut)
├── docker-compose.amd.yml    # Docker Compose AMD ROCm
├── docker-compose.amd-max.yml# Docker Compose AMD (32B)
├── docker-compose.cpu.yml    # Docker Compose CPU only
├── docker-compose.win-amd.yml# Docker Compose Windows + AMD
├── Dockerfile               # Image CLI
├── Dockerfile.web           # Image interface web
│
├── launcher.py              # 🚀 Launcher GUI principal
├── launcher.sh              # Lanceur Linux
├── launcher.ps1             # Lanceur PowerShell
├── Launcher.bat             # Lanceur Windows (double-clic)
│
├── pyproject.toml           # Configuration Python/pip
├── Makefile                 # Commandes make
├── README.md                # Documentation principale
└── LICENSE                  # Licence MIT
```

## Composants principaux

### 1. Package Python (`promptforge/`)

Le cœur de l'application :

| Fichier | Rôle |
|---------|------|
| `core.py` | Logique de reformatage des prompts |
| `profiles.py` | Définitions des modèles cibles et templates |
| `providers.py` | Communication avec Ollama |
| `web.py` | Interface Gradio |
| `cli.py` | Interface ligne de commande |
| `database.py` | Stockage SQLite |

### 2. Docker Compose

Configurations par type de GPU :

| Fichier | GPU | Modèle recommandé |
|---------|-----|-------------------|
| `docker-compose.yml` | NVIDIA | qwen3:8b |
| `docker-compose.amd.yml` | AMD ROCm | qwen3:14b |
| `docker-compose.amd-max.yml` | AMD (18GB+) | qwen3:32b |
| `docker-compose.cpu.yml` | CPU | qwen3:4b |
| `docker-compose.win-amd.yml` | Windows+AMD | qwen3:14b |

### 3. Launcher (`launcher.py`)

Interface graphique web pour :
- Détection automatique GPU
- Gestion Docker (start/stop/rebuild)
- Téléchargement modèles Ollama
- Monitoring des services

## Commandes de build

### Via le Launcher (recommandé)

```bash
# Linux/Mac
./launcher.sh

# Windows
Launcher.bat
```

### Via le script build.py

```bash
# Voir l'état
python scripts/build.py status

# Construire les images
python scripts/build.py build                 # Auto-détection GPU
python scripts/build.py build -c nvidia       # Forcer NVIDIA
python scripts/build.py build --no-cache      # Sans cache

# Démarrer/Arrêter
python scripts/build.py up
python scripts/build.py down

# Nettoyer
python scripts/build.py clean --images
```

### Via Docker Compose direct

```bash
# NVIDIA
docker compose up -d --build

# AMD
docker compose -f docker-compose.amd.yml up -d --build

# CPU
docker compose -f docker-compose.cpu.yml up -d --build
```

### Via Make

```bash
make build          # Construire
make up             # Démarrer
make down           # Arrêter
make clean          # Nettoyer
make test           # Lancer les tests
```

## Flux de données

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Prompt    │ ──▶ │ PromptForge │ ──▶ │   Prompt    │
│   brut      │     │   (core)    │     │  optimisé   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌───────────┐
                    │  Ollama   │
                    │ (qwen3:*) │
                    └───────────┘
```

## Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `OLLAMA_HOST` | URL Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modèle par défaut | `qwen3:8b` |
| `HSA_OVERRIDE_GFX_VERSION` | Version GFX AMD | `11.0.0` |

## Ports utilisés

| Port | Service |
|------|---------|
| 7860 | PromptForge Web |
| 11434 | Ollama API |
| 8765 | Launcher GUI |

## Développement

### Installation locale

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate   # Windows

# Installer en mode développement
pip install -e ".[dev]"

# Lancer les tests
pytest

# Lancer le linter
ruff check .
```

### Structure des tests

```
tests/
├── test_core.py          # Tests du reformatage
├── test_providers.py     # Tests connexion Ollama
├── test_database.py      # Tests SQLite
├── test_cli.py           # Tests CLI
└── test_integration.py   # Tests end-to-end
```
