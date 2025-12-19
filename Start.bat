@echo off
title PromptForge - Mode Natif
cd /d "%~dp0"

echo.
echo ========================================
echo    PromptForge - Mode Natif
echo ========================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe!
    echo.
    echo Telecharge Python sur: https://python.org
    echo.
    pause
    exit /b 1
)

REM Lancer le script Python
python start.py %*

if errorlevel 1 (
    echo.
    echo [INFO] Une erreur s'est produite.
    pause
)
