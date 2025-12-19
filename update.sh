#!/bin/bash
# ============================================
# PromptForge - Script de mise à jour
# Usage: ./update.sh [--force]
# ============================================

set -e

echo "🔄 PromptForge - Mise à jour Docker"
echo "===================================="

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Option --force pour rebuild sans cache
if [ "$1" == "--force" ] || [ "$1" == "-f" ]; then
    echo -e "${YELLOW}Mode forcé: reconstruction complète sans cache${NC}"
    echo ""
    
    echo "📦 Arrêt des conteneurs..."
    docker compose down
    
    echo "🗑️  Nettoyage des anciennes images..."
    docker compose rm -f 2>/dev/null || true
    
    echo "🔨 Reconstruction sans cache..."
    docker compose build --no-cache --pull
    
    echo "🚀 Démarrage..."
    docker compose up -d
else
    echo "Mode standard: mise à jour incrémentale"
    echo "(Utilise ./update.sh --force pour une reconstruction complète)"
    echo ""
    
    echo "📥 Téléchargement des dernières images..."
    docker compose pull
    
    echo "🔨 Reconstruction si nécessaire..."
    docker compose build
    
    echo "🚀 Redémarrage des services..."
    docker compose up -d
fi

echo ""
echo -e "${GREEN}✅ Mise à jour terminée !${NC}"
echo ""

# Afficher le statut
echo "📊 Statut des conteneurs:"
docker compose ps

echo ""
echo "🌐 Interface disponible sur: http://localhost:7860"
