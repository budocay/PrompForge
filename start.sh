#!/bin/bash
# PromptForge - Mode Natif (Mac/Linux)

cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "   PromptForge - Mode Natif"
echo "========================================"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé!"
    echo ""
    echo "Installe-le avec:"
    echo "  - Mac: brew install python3"
    echo "  - Ubuntu: sudo apt install python3 python3-pip"
    echo ""
    exit 1
fi

# Lancer le script Python
python3 start.py "$@"
