#!/bin/bash
# ============================================
# PromptForge Launcher - Linux/Mac
# ============================================

echo ""
echo "============================================"
echo "  PromptForge Launcher"
echo "============================================"
echo ""

# Vérifier Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[X] Python n'est pas installé!"
    echo ""
    echo "Installe Python avec: sudo apt install python3"
    exit 1
fi

echo "[OK] Python détecté: $PYTHON_CMD"
echo ""
echo "Démarrage de l'interface..."
echo "L'interface va s'ouvrir dans votre navigateur."
echo ""

# Lancer le launcher
$PYTHON_CMD launcher.py
