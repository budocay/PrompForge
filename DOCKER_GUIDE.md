# 🐳 PromptForge - Guide de Déploiement Docker

Guide complet pour lancer PromptForge avec Docker, incluant l'interface web Gradio et Ollama.

---

## 📋 Table des matières

1. [Prérequis](#-prérequis)
2. [Installation Rapide (5 minutes)](#-installation-rapide)
3. [Installation Détaillée](#-installation-détaillée)
4. [Configuration](#-configuration)
5. [Utilisation](#-utilisation)
6. [Changer de Modèle Ollama](#-changer-de-modèle-ollama)
7. [Dépannage](#-dépannage)
8. [Commandes Utiles](#-commandes-utiles)

---

## 🔧 Prérequis

### Minimum requis

| Composant | Version minimum | Vérification |
|-----------|-----------------|--------------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| RAM | 8 GB | - |
| Disque | 10 GB libre | Pour les modèles Ollama |

### Optionnel (recommandé)

| Composant | Pour quoi faire |
|-----------|-----------------|
| GPU NVIDIA | Accélérer Ollama (10x plus rapide) |
| NVIDIA Driver | 525+ |
| NVIDIA Container Toolkit | Support GPU dans Docker |

### Vérifier Docker

```bash
# Vérifier Docker
docker --version
# Docker version 24.0.0 ou supérieur

# Vérifier Docker Compose
docker compose version
# Docker Compose version v2.20.0 ou supérieur
```

### Installer NVIDIA Container Toolkit (optionnel, pour GPU)

```bash
# Ubuntu/Debian
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Vérifier
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

---

## 🚀 Installation Rapide

### Avec GPU NVIDIA

```bash
# 1. Extraire le projet
unzip promptforge.zip -d promptforge
cd promptforge

# 2. Créer le dossier de données (IMPORTANT pour la persistance!)
mkdir -p ./data/projects

# 3. Lancer tout (Ollama + Interface Web)
docker compose up -d

# 4. Attendre que le modèle soit téléchargé (~2-5 min)
docker compose logs -f ollama-pull

# 5. Ouvrir l'interface
# http://localhost:7860
```

### Sans GPU (CPU uniquement)

```bash
# 1. Extraire le projet
unzip promptforge.zip -d promptforge
cd promptforge

# 2. Créer le dossier de données (IMPORTANT!)
mkdir -p ./data/projects

# 3. Lancer avec le fichier CPU
docker compose -f docker-compose.cpu.yml up -d

# 4. Attendre le téléchargement du modèle
docker compose -f docker-compose.cpu.yml logs -f ollama-pull

# 5. Ouvrir l'interface
# http://localhost:7860
```

---

## 📦 Installation Détaillée

### Étape 1 : Extraire le projet

```bash
# Créer un dossier
mkdir -p ~/promptforge
cd ~/promptforge

# Extraire
unzip /chemin/vers/promptforge.zip -d .

# Vérifier la structure
ls -la
# Vous devez voir: docker-compose.yml, Dockerfile.web, promptforge/, etc.
```

### Étape 2 : Construire les images Docker

```bash
# Construire l'image de l'interface web
docker compose build promptforge-web

# Vérifier
docker images | grep promptforge
```

### Étape 3 : Démarrer Ollama

```bash
# Démarrer uniquement Ollama d'abord
docker compose up -d ollama

# Vérifier qu'il est healthy
docker compose ps
# ollama devrait être "healthy" après ~60 secondes
```

### Étape 4 : Télécharger le modèle LLM

```bash
# Méthode 1: Via le service automatique
docker compose up ollama-pull

# Méthode 2: Manuellement
docker compose exec ollama ollama pull llama3.1

# Vérifier les modèles installés
docker compose exec ollama ollama list
```

### Étape 5 : Démarrer l'interface web

```bash
# Démarrer l'interface
docker compose up -d promptforge-web

# Vérifier les logs
docker compose logs -f promptforge-web

# Vous devez voir:
# Running on local URL:  http://0.0.0.0:7860
```

### Étape 6 : Accéder à l'interface

Ouvrez votre navigateur à l'adresse :

🌐 **http://localhost:7860**

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Par défaut | Description |
|----------|------------|-------------|
| `OLLAMA_HOST` | `http://ollama:11434` | URL d'Ollama |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Adresse d'écoute |
| `GRADIO_SERVER_PORT` | `7860` | Port de l'interface |

### Changer le port de l'interface

Modifier `docker-compose.yml` :

```yaml
promptforge-web:
  ports:
    - "8080:7860"  # Interface sur le port 8080
```

### Persister les données

Les données sont stockées dans :

| Chemin local | Chemin container | Description |
|--------------|------------------|-------------|
| `./data/` | `/data/` | Base de données + projets créés |
| `./data/projects/` | `/data/projects/` | Projets créés via l'interface |
| `./data/promptforge.db` | `/data/promptforge.db` | Historique, config |
| Volume `ollama-data` | `/root/.ollama` | Modèles Ollama téléchargés |

**⚠️ Important:** Créez le dossier `data` avant le premier lancement pour éviter les problèmes de permissions :

```bash
mkdir -p ./data/projects
```

**Sauvegarder vos données:**

```bash
# Sauvegarder tout
tar -czvf promptforge-backup.tar.gz ./data

# Restaurer
tar -xzvf promptforge-backup.tar.gz
```

---

## 🎮 Utilisation

### Interface Web

1. **Onglet "✨ Reformater"**
   - Sélectionner un projet
   - Choisir le profil cible (Claude, GPT, Gemini...)
   - Entrer votre prompt brut
   - Cliquer sur "🚀 Reformater"
   - Voir la recommandation de modèle

2. **Onglet "📁 Projets"**
   - Créer un nouveau projet
   - Uploader un fichier `.md` de configuration
   - Ou écrire la config manuellement

3. **Onglet "📜 Historique"**
   - Voir les reformatages passés
   - Filtrer par projet

4. **Onglet "💰 Comparaison"**
   - Comparer les prix des modèles
   - Calculer les coûts estimés

### Créer un projet

1. Aller dans l'onglet "📁 Projets"
2. Entrer le nom du projet (ex: `mon-api`)
3. Uploader un fichier `.md` ou écrire :

```markdown
# Mon Projet API

## Stack
- Python 3.12
- FastAPI
- PostgreSQL
- Redis

## Structure
- src/api/ - Endpoints
- src/models/ - Modèles SQLAlchemy
- src/services/ - Logique métier

## Conventions
- snake_case pour les variables
- Type hints obligatoires
- Docstrings Google style
```

4. Cliquer sur "💾 Sauvegarder"

---

## 🔄 Changer de Modèle Ollama

### Modèles recommandés pour le reformatage

| Modèle | Taille | RAM requise | Commande |
|--------|--------|-------------|----------|
| `llama3.2:3b` | 2 GB | 4 GB | Ultra-léger, rapide |
| `llama3.1:8b` | 4.7 GB | 8 GB | **Recommandé** |
| `mistral:7b` | 4.1 GB | 8 GB | Rapide, fiable |
| `qwen2.5-coder:7b` | 4.7 GB | 8 GB | Excellent pour code |
| `llama3.3:70b` | 40 GB | 48 GB | Premium (GPU requis) |

### Installer un nouveau modèle

```bash
# Télécharger un modèle
docker compose exec ollama ollama pull mistral:7b

# Lister les modèles
docker compose exec ollama ollama list

# Supprimer un modèle (libérer de l'espace)
docker compose exec ollama ollama rm llama3.1
```

### Changer le modèle par défaut

Modifier `docker-compose.yml` dans la section `ollama-pull` :

```yaml
ollama-pull:
  command:
    - |
      echo "Pulling mistral model..."
      ollama pull mistral:7b
      echo "Model ready!"
```

Ou modifier le code dans `promptforge/providers.py` :

```python
@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "mistral:7b"  # Changer ici
```

---

## 🔧 Dépannage

### Problème : "Mes projets disparaissent après rebuild"

C'est un problème de persistance des volumes Docker.

```bash
# 1. Vérifier que le dossier data existe
ls -la ./data/

# 2. Si vide ou inexistant, le créer
mkdir -p ./data/projects

# 3. Vérifier les permissions
chmod -R 755 ./data

# 4. Relancer sans rebuild
docker compose up -d
```

**Note:** Utilisez `docker compose up -d` (sans `--build`) pour conserver les données. Utilisez `--build` uniquement quand vous modifiez le code.

### Problème : "Ollama non disponible"

```bash
# Vérifier qu'Ollama tourne
docker compose ps

# Si "unhealthy", voir les logs
docker compose logs ollama

# Redémarrer
docker compose restart ollama
```

### Problème : "Le modèle n'est pas téléchargé"

```bash
# Télécharger manuellement
docker compose exec ollama ollama pull llama3.1

# Vérifier
docker compose exec ollama ollama list
```

### Problème : "GPU non détecté"

```bash
# Vérifier NVIDIA
nvidia-smi

# Vérifier Docker GPU
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Si erreur, utiliser le mode CPU
docker compose -f docker-compose.cpu.yml up -d
```

### Problème : "Port 7860 déjà utilisé"

```bash
# Voir ce qui utilise le port
lsof -i :7860

# Changer le port dans docker-compose.yml
ports:
  - "7861:7860"
```

### Problème : "Erreur de build"

```bash
# Reconstruire sans cache
docker compose build --no-cache promptforge-web

# Supprimer les anciennes images
docker system prune -a
```

### Problème : "Lenteur extrême (CPU)"

Si vous utilisez le mode CPU et que c'est trop lent :

1. Utiliser un modèle plus petit :
```bash
docker compose exec ollama ollama pull llama3.2:3b
```

2. Ou installer le support GPU (voir prérequis)

---

## 📝 Commandes Utiles

### Gestion des services

```bash
# Démarrer tout
docker compose up -d

# Arrêter tout
docker compose down

# Redémarrer
docker compose restart

# Voir les logs en temps réel
docker compose logs -f

# Voir les logs d'un service
docker compose logs -f promptforge-web
docker compose logs -f ollama
```

### Gestion Ollama

```bash
# Lister les modèles
docker compose exec ollama ollama list

# Télécharger un modèle
docker compose exec ollama ollama pull <model>

# Supprimer un modèle
docker compose exec ollama ollama rm <model>

# Tester un modèle
docker compose exec ollama ollama run llama3.1 "Hello!"
```

### Maintenance

```bash
# Voir l'espace disque utilisé
docker system df

# Nettoyer les ressources inutilisées
docker system prune

# Sauvegarder les données
tar -czvf promptforge-backup.tar.gz ./data

# Mettre à jour Ollama
docker compose pull ollama
docker compose up -d ollama
```

### Accéder au conteneur

```bash
# Shell dans le conteneur web
docker compose exec promptforge-web bash

# Shell dans Ollama
docker compose exec ollama bash
```

---

## 🌐 Accès distant

Pour accéder à l'interface depuis un autre PC :

1. Trouver l'IP de votre machine :
```bash
ip addr show | grep inet
# ou sur Windows: ipconfig
```

2. Accéder via : `http://<IP>:7860`

3. Si firewall, ouvrir le port :
```bash
# Ubuntu
sudo ufw allow 7860
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Network                        │
│                                                             │
│  ┌─────────────────┐     ┌─────────────────────────────┐   │
│  │                 │     │                             │   │
│  │     Ollama      │◄────│    PromptForge Web         │   │
│  │   (Port 11434)  │     │      (Port 7860)           │   │
│  │                 │     │                             │   │
│  │  ┌───────────┐  │     │  ┌─────────────────────┐   │   │
│  │  │ llama3.1  │  │     │  │   Interface Gradio  │   │   │
│  │  │ mistral   │  │     │  │   + Recommandations │   │   │
│  │  │ qwen2.5   │  │     │  │   + Comparateur     │   │   │
│  │  └───────────┘  │     │  └─────────────────────┘   │   │
│  │                 │     │                             │   │
│  └────────┬────────┘     └──────────────┬──────────────┘   │
│           │                             │                   │
│           ▼                             ▼                   │
│    ┌──────────────┐              ┌──────────────┐          │
│    │ ollama-data  │              │   ./data/    │          │
│    │   (Volume)   │              │  (Bind mount)│          │
│    └──────────────┘              └──────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Navigateur    │
                    │ localhost:7860  │
                    └─────────────────┘
```

---

## ✅ Checklist de déploiement

- [ ] Docker et Docker Compose installés
- [ ] Projet extrait dans un dossier
- [ ] `docker compose up -d` exécuté
- [ ] Ollama en statut "healthy"
- [ ] Modèle téléchargé (llama3.1)
- [ ] Interface accessible sur http://localhost:7860
- [ ] Test de reformatage réussi

---

## 📞 Support

En cas de problème :

1. Vérifier les logs : `docker compose logs`
2. Consulter la section [Dépannage](#-dépannage)
3. Redémarrer les services : `docker compose restart`

---

**Bon reformatage ! 🚀**
