#!/bin/bash
# PromptForge Docker Helper Script
# Usage: ./scripts/docker-run.sh [command]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier que Docker est installé
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi
}

# Commande docker compose (v1 ou v2)
docker_compose() {
    if docker compose version &> /dev/null; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

# Démarrer les services
start() {
    log_info "Démarrage des services..."
    docker_compose up -d ollama
    
    log_info "Attente du démarrage d'Ollama..."
    sleep 5
    
    # Vérifier si le modèle est déjà téléchargé
    if ! docker exec promptforge-ollama ollama list | grep -q "llama3.1"; then
        log_info "Téléchargement du modèle llama3.1 (peut prendre plusieurs minutes)..."
        docker exec promptforge-ollama ollama pull llama3.1
    else
        log_info "Modèle llama3.1 déjà disponible"
    fi
    
    log_info "Services prêts !"
}

# Arrêter les services
stop() {
    log_info "Arrêt des services..."
    docker_compose down
}

# Exécuter une commande promptforge
run() {
    docker_compose run --rm promptforge promptforge --path /data "$@"
}

# Mode interactif
interactive() {
    log_info "Mode interactif - tapez 'exit' pour quitter"
    docker_compose run --rm promptforge
}

# Afficher les logs
logs() {
    docker_compose logs -f "${1:-ollama}"
}

# Statut des services
status() {
    log_info "Statut des conteneurs:"
    docker_compose ps
    
    echo ""
    log_info "Test de connexion Ollama:"
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama accessible${NC}"
        echo "Modèles disponibles:"
        curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; [print(f'  - {m[\"name\"]}') for m in json.load(sys.stdin).get('models', [])]" 2>/dev/null || echo "  (aucun)"
    else
        echo -e "${RED}✗ Ollama non accessible${NC}"
    fi
}

# Nettoyer tout
clean() {
    log_warn "Ceci va supprimer tous les conteneurs et volumes PromptForge"
    read -p "Continuer ? [y/N] " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        docker_compose down -v
        log_info "Nettoyage terminé"
    fi
}

# Build l'image
build() {
    log_info "Construction de l'image PromptForge..."
    docker_compose build promptforge
}

# Aide
help() {
    echo "PromptForge Docker Helper"
    echo ""
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  start       Démarrer Ollama et télécharger le modèle"
    echo "  stop        Arrêter tous les services"
    echo "  status      Afficher le statut des services"
    echo "  run <cmd>   Exécuter une commande promptforge"
    echo "  interactive Mode shell interactif"
    echo "  logs [svc]  Afficher les logs (défaut: ollama)"
    echo "  build       Construire l'image Docker"
    echo "  clean       Supprimer conteneurs et volumes"
    echo "  help        Afficher cette aide"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 run init my-project --config /data/projects/my-project.md"
    echo "  $0 run format 'create a REST API'"
    echo "  $0 run list"
}

# Main
check_docker

case "${1:-help}" in
    start)      start ;;
    stop)       stop ;;
    status)     status ;;
    run)        shift; run "$@" ;;
    interactive) interactive ;;
    logs)       logs "$2" ;;
    build)      build ;;
    clean)      clean ;;
    help|*)     help ;;
esac
