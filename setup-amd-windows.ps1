# ============================================
# PromptForge - Setup AMD GPU sur Windows
# ============================================
# Usage: .\setup-amd-windows.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  PromptForge - Setup AMD GPU Windows" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verifier si Ollama est installe
$ollamaPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaPath)) {
    Write-Host "[X] Ollama n'est pas installe!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Telecharge Ollama depuis: https://ollama.com/download/windows" -ForegroundColor Yellow
    Write-Host ""
    Start-Process "https://ollama.com/download/windows"
    exit 1
}

Write-Host "[OK] Ollama detecte: $ollamaPath" -ForegroundColor Green
Write-Host ""

# Configurer HSA_OVERRIDE_GFX_VERSION pour RX 7900 XT
Write-Host "[...] Configuration de la variable d'environnement pour AMD GPU..." -ForegroundColor Yellow

$currentValue = [Environment]::GetEnvironmentVariable("HSA_OVERRIDE_GFX_VERSION", "User")
if ($currentValue -eq "11.0.0") {
    Write-Host "[OK] HSA_OVERRIDE_GFX_VERSION deja configure (11.0.0)" -ForegroundColor Green
} else {
    Write-Host "   Quelle est ta carte graphique AMD?" -ForegroundColor White
    Write-Host "   1) RX 7900 XT / XTX / 7800 XT / 7600 (serie 7000)" -ForegroundColor White
    Write-Host "   2) RX 6900 XT / 6800 XT / 6700 XT (serie 6000)" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Ton choix (1 ou 2)"
    
    if ($choice -eq "2") {
        $gfxVersion = "10.3.0"
    } else {
        $gfxVersion = "11.0.0"
    }
    
    [Environment]::SetEnvironmentVariable("HSA_OVERRIDE_GFX_VERSION", $gfxVersion, "User")
    Write-Host "[OK] HSA_OVERRIDE_GFX_VERSION configure: $gfxVersion" -ForegroundColor Green
    Write-Host ""
    Write-Host "[!] IMPORTANT: Redemarre ton PC pour que la variable soit prise en compte!" -ForegroundColor Yellow
}

Write-Host ""

# Telecharger le modele recommande
Write-Host "[...] Verification du modele qwen2.5:14b..." -ForegroundColor Yellow
$models = & ollama list 2>$null

if ($models -match "qwen2.5:14b") {
    Write-Host "[OK] Modele qwen2.5:14b deja installe" -ForegroundColor Green
} else {
    Write-Host "[...] Telechargement de qwen2.5:14b (~9GB)..." -ForegroundColor Yellow
    Write-Host "   (Cela peut prendre plusieurs minutes)" -ForegroundColor Gray
    & ollama pull qwen2.5:14b
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Configuration terminee!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prochaines etapes:" -ForegroundColor White
Write-Host ""
Write-Host "1. Redemarre ton PC (si premiere fois)" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Ouvre un terminal PowerShell et lance Ollama:" -ForegroundColor Yellow
Write-Host "   ollama serve" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Dans un autre terminal, lance PromptForge:" -ForegroundColor Yellow
Write-Host "   docker compose -f docker-compose.win-amd.yml up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Ouvre ton navigateur:" -ForegroundColor Yellow
Write-Host "   http://localhost:7860" -ForegroundColor Cyan
Write-Host ""
