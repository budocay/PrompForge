# 🔧 PromptForge

**Reformateur intelligent de prompts avec contexte projet**

PromptForge transforme vos prompts bruts en prompts optimisés et structurés, en utilisant le contexte complet de votre projet (stack technique, conventions, architecture...).

100% **open-source** et **local** grâce à [Ollama](https://ollama.ai).

---

## ✨ Fonctionnalités

- 📁 **Multi-projets** : Gérez plusieurs projets avec leurs propres configurations
- 🧠 **IA locale** : Utilise Ollama (Llama 3.1, Mistral...) - aucune donnée envoyée à l'extérieur
- 🌐 **Interface Web** : UI Gradio moderne et intuitive
- 📝 **Historique complet** : Chaque prompt (brut + reformaté) est sauvegardé
- 🎯 **Template IA** : Prompt prêt à l'emploi pour générer ta config avec Claude/ChatGPT
- 🐳 **Docker ready** : Déploiement simple avec Docker Compose
- 🔄 **Portable** : SQLite + fichiers markdown, facile à versionner et partager

---

## 🚀 Installation

### Prérequis

| OS | Python | Ollama |
|----|--------|--------|
| **Windows** | [Python 3.10+](https://www.python.org/downloads/) | [Ollama Windows](https://ollama.com/download/windows) |
| **macOS** | `brew install python` ou [Python.org](https://www.python.org/downloads/) | `brew install ollama` ou [Ollama.com](https://ollama.com/download/mac) |
| **Linux** | `sudo apt install python3 python3-pip` | `curl -fsSL https://ollama.ai/install.sh \| sh` |

### Option 1 : Installation locale

#### Windows (PowerShell)
```powershell
# Cloner le repo
git clone https://github.com/yourusername/promptforge.git
cd promptforge

# Installer
pip install -e .

# Ou avec interface web
pip install -e ".[web]"

# Lancer Ollama (dans un autre terminal)
ollama serve

# Télécharger le modèle
ollama pull llama3.1

# Vérifier
promptforge status
```

#### macOS / Linux
```bash
# Cloner le repo
git clone https://github.com/yourusername/promptforge.git
cd promptforge

# Installer
pip install -e .

# Ou avec interface web
pip install -e ".[web]"

# Lancer Ollama (dans un autre terminal)
ollama serve

# Télécharger le modèle
ollama pull llama3.1

# Vérifier
promptforge status
```

### Option 2 : Docker (recommandé - tous OS)

Docker fonctionne de manière identique sur Windows, macOS et Linux.

```bash
# Cloner le repo
git clone https://github.com/yourusername/promptforge.git
cd promptforge

# Windows (PowerShell)
.\run.ps1 docker-start

# macOS / Linux
python scripts/docker_helper.py start
# ou
make docker-start
```

---

## 📖 Utilisation

### Quick Start par plateforme

<details>
<summary><b>🪟 Windows</b></summary>

```powershell
# Avec PowerShell
.\run.ps1 install-web

# Ou manuellement
pip install -e ".[web]"

# Lancer l'interface
promptforge web
```
</details>

<details>
<summary><b>🍎 macOS</b></summary>

```bash
# Installation
pip install -e ".[web]"

# Lancer l'interface
promptforge web

# Ou avec Make
make install-web
make web
```
</details>

<details>
<summary><b>🐧 Linux</b></summary>

```bash
# Installation (+ xclip pour presse-papier)
sudo apt install xclip  # Debian/Ubuntu
pip install -e ".[web]"

# Lancer
promptforge web

# Ou avec Make
make install-web
make web
```
</details>

### Mode local

```bash
# 1. Créer un fichier de config projet
cat > mon-projet.md << 'EOF'
# Mon Projet
## Stack
- Python 3.12
- FastAPI
## Conventions
- Type hints obligatoires
EOF

# 2. Initialiser le projet
promptforge init mon-projet --config ./mon-projet.md

# 3. Reformater un prompt
promptforge format "crée une route pour les users"
```

### Mode Docker

```bash
# Initialiser un projet (les configs sont dans ./projects/)
make docker-run CMD="init mon-projet --config /data/projects/exemple-webapp.md"

# Reformater
make docker-run CMD="format 'crée une API REST'"

# Lister les projets
make docker-run CMD="list"

# Shell interactif
make docker-shell
```

### Commandes disponibles

| Commande | Description |
|----------|-------------|
| `promptforge init <nom> --config <file.md>` | Initialiser un projet |
| `promptforge use <nom>` | Activer un projet |
| `promptforge list` | Lister les projets |
| `promptforge format "<prompt>"` | Reformater un prompt |
| `promptforge format` | Mode interactif |
| `promptforge history` | Voir l'historique |
| `promptforge status` | Statut du système |
| `promptforge reload <nom>` | Recharger la config |
| `promptforge delete <nom>` | Supprimer un projet |
| `promptforge web` | Lancer l'interface web |
| `promptforge template` | Afficher le template de génération |

---

## 🌐 Interface Web

PromptForge inclut une interface web moderne avec Gradio.

### Lancement

```bash
# Installation avec support web
pip install -e ".[web]"

# Lancer l'interface
promptforge web

# Options
promptforge web --port 8080           # Port personnalisé
promptforge web --host 0.0.0.0        # Écouter sur toutes les interfaces
promptforge web --share               # Créer un lien public Gradio
```

### Avec Docker

```bash
# Lancer Ollama + Interface Web
docker-compose up -d ollama promptforge-web

# Accéder à http://localhost:7860
```

### Fonctionnalités de l'interface

| Onglet | Description |
|--------|-------------|
| ✨ Reformater | Reformate tes prompts avec le contexte projet |
| 📁 Projets | Créer, modifier, supprimer des projets |
| 📜 Historique | Consulter l'historique des prompts |
| 🎯 Générer config | Template pour créer ta config avec une IA |
| ❓ Aide | Guide d'utilisation |

---

## 🎯 Générer ta configuration avec une IA

Tu ne sais pas comment structurer ton fichier de config ? Utilise le template intégré !

### Option 1 : Via CLI

```bash
# Afficher le template
promptforge template

# Sauvegarder dans un fichier
promptforge template --output mon-template.md
```

### Option 2 : Via l'interface web

1. Ouvre l'interface : `promptforge web`
2. Va dans l'onglet **🎯 Générer config**
3. Copie le prompt
4. Envoie-le à Claude, ChatGPT ou ton IA préférée
5. L'IA va te poser des questions sur ton projet
6. Elle génère un fichier .md complet
7. Colle-le dans l'onglet **📁 Projets**

### Le workflow idéal

```
1. promptforge template > template.md     # Récupérer le template
2. [Envoyer à Claude/ChatGPT]             # L'IA pose des questions
3. [Recevoir le fichier .md généré]       # Config complète
4. promptforge init mon-projet --config config.md
5. promptforge format "mon prompt"        # Prêt à reformater !
```

---

## 🧪 Tests

```bash
# Installer les dépendances de dev
make install-dev

# Lancer les tests
make test

# Tests avec couverture
make test-cov

# Vérifications complètes (lint + tests)
make check
```

---

## 🐳 Docker

### Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   PromptForge   │────▶│     Ollama      │
│   (Python CLI)  │     │  (LLM Server)   │
└─────────────────┘     └─────────────────┘
        │                       │
        ▼                       ▼
   ./data/              ollama-data volume
   - promptforge.db     - modèles LLM
   - history/
   - projects/
```

### Commandes Docker

```bash
make docker-start    # Démarrer Ollama + télécharger modèle
make docker-stop     # Arrêter les services
make docker-status   # Vérifier le statut
make docker-logs     # Voir les logs Ollama
make docker-shell    # Shell interactif
make docker-clean    # Supprimer tout
```

### GPU Support (NVIDIA)

Décommentez la section GPU dans `docker-compose.yml` :

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

---

## 📁 Structure des fichiers

```
promptforge/
├── promptforge/          # Code source
│   ├── __init__.py
│   ├── cli.py           # Interface ligne de commande
│   ├── core.py          # Logique principale
│   ├── database.py      # SQLite
│   ├── providers.py     # Ollama
│   ├── utils.py         # Utilitaires cross-platform
│   └── web.py           # Interface Gradio
├── tests/               # Tests pytest
├── scripts/
│   ├── docker_helper.py # Helper Docker (Python, cross-platform)
│   └── docker-run.sh    # Helper Docker (bash, Linux/macOS)
├── templates/           # Template génération config
├── projects/            # Configs projet exemple
├── run.ps1              # Script Windows PowerShell
├── Makefile             # Commandes Make (Linux/macOS/Windows avec make)
├── Dockerfile
├── Dockerfile.web
└── docker-compose.yml
```

---

## 🖥️ Compatibilité

| Fonctionnalité | Windows | macOS | Linux |
|----------------|---------|-------|-------|
| CLI | ✅ | ✅ | ✅ |
| Interface Web | ✅ | ✅ | ✅ |
| Docker | ✅ | ✅ | ✅ |
| Presse-papier | ✅ clip.exe | ✅ pbcopy | ✅ xclip/xsel |
| Ollama | ✅ | ✅ | ✅ |
| WSL | ✅ (auto-détecté) | - | - |

---

## 📄 Format de configuration projet

```markdown
# Nom du Projet

## Description
Application de gestion de tâches...

## Stack
- Python 3.12
- FastAPI
- PostgreSQL

## Structure
src/
├── api/
├── models/
└── services/

## Conventions
- Type hints obligatoires
- Docstrings Google style
- Tests avec pytest

## Notes
Informations supplémentaires...
```

---

## 🔧 Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `OLLAMA_HOST` | URL du serveur Ollama | `http://localhost:11434` |

### Changer le modèle

```bash
promptforge format "mon prompt" --model mistral
```

---

## 🤝 Contribution

Les contributions sont les bienvenues !

```bash
# Setup dev
make dev-setup

# Vérifications avant commit
make check
```

1. Fork le projet
2. Créez une branche (`git checkout -b feature/ma-feature`)
3. Lancez les tests (`make check`)
4. Committez (`git commit -am 'Ajout de ma feature'`)
5. Push (`git push origin feature/ma-feature`)
6. Ouvrez une Pull Request

---

## 📜 Licence

MIT License - voir [LICENSE](LICENSE)
