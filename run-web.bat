@echo off
chcp 65001 >nul
title PromptForge - Interface Web
color 0A

echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║       PromptForge - Interface Web         ║
echo  ╚═══════════════════════════════════════════╝
echo.

:: Vérifier Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python n'est pas installe ou pas dans le PATH
    echo.
    echo     Installe Python depuis: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [OK] Python detecte
echo.

:: Vérifier si Ollama tourne
echo [..] Verification d'Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama n'est pas demarre
    echo     Lance "ollama serve" dans un autre terminal
    echo.
    echo     Ou installe Ollama: https://ollama.com/download
    echo.
    set /p CONTINUE="Continuer quand meme? (O/N): "
    if /i not "%CONTINUE%"=="O" exit /b 1
) else (
    echo [OK] Ollama disponible
)
echo.

:: Se placer dans le répertoire du script
cd /d "%~dp0"

:: Lancer l'interface
echo [>>] Demarrage de l'interface web...
echo     L'interface va s'ouvrir sur http://localhost:7860
echo.
echo     Appuie sur Ctrl+C pour arreter
echo.

:: Définir PYTHONPATH pour trouver le module
set PYTHONPATH=%~dp0
python -m promptforge.cli web --port 7860

pause
