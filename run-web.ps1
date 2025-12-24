# ═══════════════════════════════════════════════════════════════
# PromptForge - Lancement direct de l'interface Web
# ═══════════════════════════════════════════════════════════════
# Double-clique sur ce fichier ou lance: .\run-web.ps1

$Host.UI.RawUI.WindowTitle = "PromptForge - Interface Web"

Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║       PromptForge - Interface Web         ║" -ForegroundColor Cyan
Write-Host "  ╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────────────────
# Vérification Python
# ─────────────────────────────────────────────────────────────────
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $pythonCmd = $cmd
        break
    }
}

if (-not $pythonCmd) {
    Write-Host "[X] Python n'est pas installe!" -ForegroundColor Red
    Write-Host ""
    Write-Host "    Installe Python depuis: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Appuie sur Entree pour quitter"
    exit 1
}

# Vérifier la version
$pythonVersion = & $pythonCmd --version 2>&1
Write-Host "[OK] $pythonVersion" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────
# Vérification des dépendances
# ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[..] Verification des dependances..." -ForegroundColor Gray

$checkGradio = & $pythonCmd -c "import gradio; print(gradio.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Gradio non installe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    Installation des dependances..." -ForegroundColor Cyan
    & $pythonCmd -m pip install -e ".[web]"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] Erreur d'installation" -ForegroundColor Red
        Read-Host "Appuie sur Entree pour quitter"
        exit 1
    }
} else {
    Write-Host "[OK] Gradio $checkGradio" -ForegroundColor Green
}

# ─────────────────────────────────────────────────────────────────
# Vérification Ollama
# ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[..] Verification d'Ollama..." -ForegroundColor Gray

$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    $ollamaRunning = $true
    $models = ($response.Content | ConvertFrom-Json).models
    $modelCount = if ($models) { $models.Count } else { 0 }
    Write-Host "[OK] Ollama disponible ($modelCount modeles)" -ForegroundColor Green
} catch {
    Write-Host "[!] Ollama n'est pas demarre" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    Options:" -ForegroundColor Gray
    Write-Host "    1. Lance 'ollama serve' dans un autre terminal" -ForegroundColor Gray
    Write-Host "    2. Ou installe Ollama: https://ollama.com/download" -ForegroundColor Gray
    Write-Host ""

    $continue = Read-Host "Continuer quand meme? (O/N)"
    if ($continue -ne "O" -and $continue -ne "o") {
        exit 0
    }
}

# ─────────────────────────────────────────────────────────────────
# Lancement de l'interface
# ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Demarrage de PromptForge..." -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Interface: " -NoNewline
Write-Host "http://localhost:7860" -ForegroundColor Green
Write-Host ""
Write-Host "  Appuie sur Ctrl+C pour arreter" -ForegroundColor Gray
Write-Host ""

# Ouvrir le navigateur après un délai
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:7860"
} | Out-Null

# Se placer dans le répertoire du script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir

# Lancer l'interface (avec PYTHONPATH pour trouver le module)
$env:PYTHONPATH = $scriptDir
& $pythonCmd -m promptforge.cli web --port 7860

Pop-Location

Write-Host ""
Write-Host "Interface arretee." -ForegroundColor Yellow
Read-Host "Appuie sur Entree pour quitter"
