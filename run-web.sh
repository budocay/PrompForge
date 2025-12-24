#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PromptForge - Lancement direct de l'interface Web
# ═══════════════════════════════════════════════════════════════
# Usage: ./run-web.sh

set -e

echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║       PromptForge - Interface Web         ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────
# Vérification Python
# ─────────────────────────────────────────────────────────────────
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "[X] Python n'est pas installé!"
    echo ""
    echo "    Installe Python avec:"
    echo "    - Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "    - macOS: brew install python3"
    echo ""
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "[OK] $PYTHON_VERSION"

# ─────────────────────────────────────────────────────────────────
# Vérification des dépendances
# ─────────────────────────────────────────────────────────────────
echo ""
echo "[..] Vérification des dépendances..."

if ! $PYTHON_CMD -c "import gradio" 2>/dev/null; then
    echo "[!] Gradio non installé"
    echo ""
    echo "    Installation des dépendances..."
    $PYTHON_CMD -m pip install -e ".[web]"
else
    GRADIO_VERSION=$($PYTHON_CMD -c "import gradio; print(gradio.__version__)" 2>/dev/null)
    echo "[OK] Gradio $GRADIO_VERSION"
fi

# ─────────────────────────────────────────────────────────────────
# Vérification Ollama
# ─────────────────────────────────────────────────────────────────
echo ""
echo "[..] Vérification d'Ollama..."

if curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
    MODEL_COUNT=$(curl -s http://localhost:11434/api/tags | grep -o '"name"' | wc -l)
    echo "[OK] Ollama disponible ($MODEL_COUNT modèles)"
else
    echo "[!] Ollama n'est pas démarré"
    echo ""
    echo "    Options:"
    echo "    1. Lance 'ollama serve' dans un autre terminal"
    echo "    2. Ou installe Ollama: https://ollama.com/download"
    echo ""
    read -p "Continuer quand même? (O/N): " CONTINUE
    if [[ "$CONTINUE" != "O" && "$CONTINUE" != "o" ]]; then
        exit 0
    fi
fi

# ─────────────────────────────────────────────────────────────────
# Lancement de l'interface
# ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Démarrage de PromptForge..."
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Interface: http://localhost:7860"
echo ""
echo "  Appuie sur Ctrl+C pour arrêter"
echo ""

# Ouvrir le navigateur après un délai (en arrière-plan)
(sleep 3 && (xdg-open http://localhost:7860 2>/dev/null || open http://localhost:7860 2>/dev/null || true)) &

# Lancer l'interface
$PYTHON_CMD -m promptforge web --port 7860

echo ""
echo "Interface arrêtée."
