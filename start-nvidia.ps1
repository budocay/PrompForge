# ============================================
# PromptForge - Lancement NVIDIA GPU (Windows)
# ============================================
# Usage: .\start-nvidia.ps1
#        .\start-nvidia.ps1 -Stop

param(
    [string]$Model = "llama3.1:8b",
    [switch]$Stop,
    [switch]$Logs
)

$ErrorActionPreference = "SilentlyContinue"

# Couleurs
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[..] $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[X] $msg" -ForegroundColor Red }

# Banner
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  PromptForge - NVIDIA GPU (Windows)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# === MODE STOP ===
if ($Stop) {
    Write-Info "Arret de PromptForge..."
    docker compose down 2>$null
    Write-Success "Arrete!"
    exit 0
}

# === MODE LOGS ===
if ($Logs) {
    docker logs -f promptforge-web
    exit 0
}

# === MODE NORMAL ===

# 1. Verifier Docker
$dockerRunning = docker info 2>$null
if (-not $dockerRunning) {
    Write-Err "Docker n'est pas lance!"
    Write-Host "Lance Docker Desktop et reessaie." -ForegroundColor Yellow
    exit 1
}
Write-Success "Docker detecte"

# 2. Lancer PromptForge (Ollama inclus dans Docker)
Write-Info "Demarrage de PromptForge avec NVIDIA GPU..."
docker compose up -d --build

# Attendre
Write-Info "Attente du demarrage..."
Start-Sleep -Seconds 10

# 3. Verifier
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
    Write-Host "NVIDIA (CUDA)" -ForegroundColor Green
    Write-Host "  Modele: " -NoNewline
    Write-Host "$Model" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Commandes:" -ForegroundColor Gray
    Write-Host "    .\start-nvidia.ps1 -Stop   # Arreter" -ForegroundColor Gray
    Write-Host "    .\start-nvidia.ps1 -Logs   # Logs" -ForegroundColor Gray
    Write-Host ""
    
    Start-Process "http://localhost:7860"
} else {
    Write-Err "Erreur au demarrage"
    docker logs promptforge-web --tail 20
}
