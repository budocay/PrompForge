# ============================================
# PromptForge - Lancement AMD GPU (Windows)
# ============================================
# Usage: .\start-amd.ps1
#        .\start-amd.ps1 -Model "qwen2.5:32b"
#        .\start-amd.ps1 -Stop

param(
    [string]$Model = "qwen2.5:14b",
    [switch]$Stop,
    [switch]$Logs,
    [switch]$Setup
)

$ErrorActionPreference = "SilentlyContinue"

# Couleurs
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[..] $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[X] $msg" -ForegroundColor Red }

# Banner
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  PromptForge - AMD GPU (Windows)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# === MODE STOP ===
if ($Stop) {
    Write-Info "Arret de PromptForge et Ollama..."
    docker compose -f docker-compose.win-amd.yml down 2>$null
    Get-Process ollama* | Stop-Process -Force 2>$null
    Write-Success "Tout est arrete!"
    exit 0
}

# === MODE LOGS ===
if ($Logs) {
    docker logs -f promptforge-web
    exit 0
}

# === MODE SETUP (premiere fois) ===
if ($Setup) {
    Write-Info "Configuration initiale AMD GPU..."
    
    # Detecter la carte AMD
    $gpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -match "AMD|Radeon" }
    if ($gpu) {
        Write-Success "GPU detecte: $($gpu.Name)"
        
        # Determiner la version GFX
        if ($gpu.Name -match "7[0-9]{3}") {
            $gfxVersion = "11.0.0"
            Write-Info "Serie RX 7000 detectee -> HSA_OVERRIDE_GFX_VERSION=$gfxVersion"
        } elseif ($gpu.Name -match "6[0-9]{3}") {
            $gfxVersion = "10.3.0"
            Write-Info "Serie RX 6000 detectee -> HSA_OVERRIDE_GFX_VERSION=$gfxVersion"
        } else {
            $gfxVersion = "11.0.0"
            Write-Warn "Serie non reconnue, utilisation de $gfxVersion par defaut"
        }
        
        # Configurer les variables permanentes
        [Environment]::SetEnvironmentVariable("HSA_OVERRIDE_GFX_VERSION", $gfxVersion, "User")
        [Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")
        Write-Success "Variables d'environnement configurees (permanentes)"
    } else {
        Write-Err "Aucune carte AMD detectee!"
        exit 1
    }
    
    # Verifier Ollama
    $ollamaPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (-not (Test-Path $ollamaPath)) {
        Write-Warn "Ollama n'est pas installe!"
        Write-Info "Ouverture de la page de telechargement..."
        Start-Process "https://ollama.com/download/windows"
        Write-Host ""
        Write-Host "Apres installation, relance: .\start-amd.ps1 -Setup" -ForegroundColor Yellow
        exit 1
    }
    Write-Success "Ollama installe"
    
    # Telecharger le modele
    Write-Info "Telechargement du modele $Model (peut prendre plusieurs minutes)..."
    & ollama pull $Model
    
    Write-Host ""
    Write-Success "Configuration terminee!"
    Write-Host ""
    Write-Host "Tu peux maintenant lancer: .\start-amd.ps1" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# === MODE NORMAL (lancement) ===

# 1. Configurer les variables pour cette session
$env:OLLAMA_HOST = "0.0.0.0:11434"
$env:HSA_OVERRIDE_GFX_VERSION = if ($env:HSA_OVERRIDE_GFX_VERSION) { $env:HSA_OVERRIDE_GFX_VERSION } else { "11.0.0" }

# 2. Arreter les anciennes instances
Write-Info "Nettoyage des anciennes instances..."
docker compose -f docker-compose.win-amd.yml down 2>$null
Get-Process ollama* | Stop-Process -Force 2>$null
Start-Sleep -Seconds 2

# 3. Lancer Ollama en arriere-plan
Write-Info "Demarrage d'Ollama (GPU AMD)..."
$ollamaProcess = Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -PassThru

# Attendre qu'Ollama soit pret
$retries = 0
$maxRetries = 30
while ($retries -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Success "Ollama demarre (PID: $($ollamaProcess.Id))"
            break
        }
    } catch {
        $retries++
        Start-Sleep -Seconds 1
    }
}

if ($retries -ge $maxRetries) {
    Write-Err "Ollama n'a pas demarre correctement"
    exit 1
}

# 4. Verifier que le modele est installe
Write-Info "Verification du modele $Model..."
$models = & ollama list 2>$null
if ($models -notmatch $Model.Split(":")[0]) {
    Write-Warn "Modele $Model non installe, telechargement..."
    & ollama pull $Model
}
Write-Success "Modele $Model pret"

# 5. Lancer PromptForge
Write-Info "Demarrage de PromptForge..."
docker compose -f docker-compose.win-amd.yml up -d --build

# Attendre que PromptForge soit pret
Start-Sleep -Seconds 5

# 6. Verifier le statut
$containerStatus = docker ps --filter "name=promptforge-web" --format "{{.Status}}"
if ($containerStatus -match "Up") {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  PromptForge est pret!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Interface web: " -NoNewline
    Write-Host "http://localhost:7860" -ForegroundColor Cyan
    Write-Host "  GPU: " -NoNewline
    Write-Host "AMD (ROCm) - $env:HSA_OVERRIDE_GFX_VERSION" -ForegroundColor Yellow
    Write-Host "  Modele: " -NoNewline
    Write-Host "$Model" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Commandes utiles:" -ForegroundColor Gray
    Write-Host "    .\start-amd.ps1 -Stop   # Arreter tout" -ForegroundColor Gray
    Write-Host "    .\start-amd.ps1 -Logs   # Voir les logs" -ForegroundColor Gray
    Write-Host ""
    
    # Ouvrir le navigateur
    Start-Process "http://localhost:7860"
} else {
    Write-Err "PromptForge n'a pas demarre correctement"
    Write-Host "Logs:" -ForegroundColor Yellow
    docker logs promptforge-web --tail 20
}
