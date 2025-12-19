# ============================================
# PromptForge Launcher - Demarrage
# ============================================
# Double-cliquez sur ce fichier ou lancez: .\launcher.ps1

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  PromptForge Launcher" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verifier Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if (-not $pythonCmd) {
    Write-Host "[X] Python n'est pas installe!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installe Python depuis: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host "[OK] Python detecte: $pythonCmd" -ForegroundColor Green
Write-Host ""
Write-Host "Demarrage de l'interface..." -ForegroundColor Cyan
Write-Host "L'interface va s'ouvrir dans votre navigateur." -ForegroundColor Gray
Write-Host ""

# Lancer le launcher
& $pythonCmd launcher.py
