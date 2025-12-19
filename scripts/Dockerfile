# PromptForge Dockerfile
# Image légère Python pour l'application

FROM python:3.12-slim

LABEL maintainer="PromptForge Contributors"
LABEL description="Reformateur intelligent de prompts avec contexte projet"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# Copier les fichiers du projet
COPY pyproject.toml README.md LICENSE ./
COPY promptforge/ ./promptforge/

# Installer le package
RUN pip install -e .

# Créer les dossiers nécessaires
RUN mkdir -p /data/projects /data/history

# Volume pour la persistance des données
VOLUME ["/data"]

# Point d'entrée
ENTRYPOINT ["promptforge", "--path", "/data"]

# Commande par défaut
CMD ["status"]
