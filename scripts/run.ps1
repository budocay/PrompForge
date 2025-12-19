<# 
.SYNOPSIS
    PromptForge - Script d'aide pour Windows PowerShell
.DESCRIPTION
    Fournit des commandes simples pour gérer PromptForge sur Windows
.EXAMPLE
    .\run.ps1 help
    .\run.ps1 install
    .\run.ps1 docker-start
    .\run.ps1 web
#>

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1, ValueFromRemainingArguments)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

# Couleurs
function Write-Info { param($msg) Write-Host "[INFO] " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Warn { param($msg) Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err { param($msg) Write-Host "[ERROR] " -ForegroundColor Red -NoNewline; Write-Host $msg }
function Write-Step { param($msg) Write-Host "  -> " -ForegroundColor Cyan -NoNewline; Write-Host $msg }

# ===========================================
# Vérifications
# ===========================================

function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Err "Docker n'est pas installe"
        Write-Host "Telechargez Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Docker n'est pas demarre"
        Write-Host "Lancez Docker Desktop"
        exit 1
    }
}

function Test-Ollama {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# ===========================================
# Commandes Installation
# ===========================================

function Install-Basic {
    Write-Info "Installation de PromptForge..."
    pip install -e .
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Installation terminee!"
        Write-Step "Lancez 'promptforge status' pour verifier"
    }
}

function Install-Web {
    Write-Info "Installation avec interface web..."
    pip install -e ".[web]"
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Installation terminee!"
        Write-Step "Lancez '.\run.ps1 web' pour demarrer l'interface"
    }
}

function Install-Dev {
    Write-Info "Installation mode developpement..."
    pip install -e ".[dev]"
}

function Install-All {
    Write-Info "Installation complete..."
    pip install -e ".[all]"
}

# ===========================================
# Commandes Docker
# ===========================================

function Docker-Start {
    Test-Docker
    
    Write-Info "Demarrage d'Ollama..."
    docker compose up -d ollama
    
    Write-Info "Attente du demarrage (10 secondes)..."
    Start-Sleep -Seconds 10
    
    # Vérifier si le modèle existe
    Write-Info "Verification du modele llama3.1..."
    $models = docker exec promptforge-ollama ollama list 2>&1
    
    if ($models -notmatch "llama3.1") {
        Write-Info "Telechargement du modele llama3.1 (peut prendre plusieurs minutes)..."
        docker exec promptforge-ollama ollama pull llama3.1
    } else {
        Write-Info "Modele llama3.1 deja disponible"
    }
    
    Write-Info "Services prets!"
    Write-Step "Ollama accessible sur http://localhost:11434"
}

function Docker-Stop {
    Test-Docker
    Write-Info "Arret des services..."
    docker compose down
    Write-Info "Services arretes"
}

function Docker-Status {
    Test-Docker
    
    Write-Info "Statut des conteneurs:"
    docker compose ps
    
    Write-Host ""
    Write-Info "Test de connexion Ollama:"
    if (Test-Ollama) {
        Write-Host "  [OK] " -ForegroundColor Green -NoNewline
        Write-Host "Ollama accessible"
        
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
            $data = $response.Content | ConvertFrom-Json
            Write-Host "  Modeles disponibles:"
            foreach ($model in $data.models) {
                Write-Host "    - $($model.name)"
            }
        } catch {}
    } else {
        Write-Host "  [ERREUR] " -ForegroundColor Red -NoNewline
        Write-Host "Ollama non accessible"
    }
}

function Docker-Web {
    Test-Docker
    
    Write-Info "Demarrage d'Ollama + Interface Web..."
    docker compose up -d ollama promptforge-web
    
    Write-Info "Attente du demarrage..."
    Start-Sleep -Seconds 5
    
    Write-Info "Interface web disponible!"
    Write-Host ""
    Write-Host "  URL: " -NoNewline
    Write-Host "http://localhost:7860" -ForegroundColor Cyan
    Write-Host ""
    
    # Ouvrir dans le navigateur
    $openBrowser = Read-Host "Ouvrir dans le navigateur? [O/n]"
    if ($openBrowser -ne "n") {
        Start-Process "http://localhost:7860"
    }
}

function Docker-Logs {
    Test-Docker
    $service = if ($Arguments.Count -gt 0) { $Arguments[0] } else { "ollama" }
    Write-Info "Logs du service $service (Ctrl+C pour quitter)..."
    docker compose logs -f $service
}

function Docker-Shell {
    Test-Docker
    Write-Info "Shell interactif (tapez 'exit' pour quitter)..."
    docker compose run --rm promptforge
}

function Docker-Build {
    Test-Docker
    Write-Info "Construction des images..."
    docker compose build
}

function Docker-Clean {
    Test-Docker
    Write-Warn "Ceci va supprimer tous les conteneurs et volumes PromptForge"
    $confirm = Read-Host "Continuer? [o/N]"
    if ($confirm -eq "o" -or $confirm -eq "O") {
        docker compose down -v
        Write-Info "Nettoyage termine"
    } else {
        Write-Host "Annule."
    }
}

function Docker-Run {
    Test-Docker
    if ($Arguments.Count -eq 0) {
        Write-Err "Usage: .\run.ps1 docker-run <commande>"
        Write-Host "Exemple: .\run.ps1 docker-run list"
        return
    }
    docker compose run --rm promptforge promptforge --path /data $Arguments
}

# ===========================================
# Commandes Locales
# ===========================================

function Start-Web {
    Write-Info "Demarrage de l'interface web..."
    
    if (-not (Test-Ollama)) {
        Write-Warn "Ollama n'est pas accessible sur localhost:11434"
        Write-Host "Lancez 'ollama serve' ou '.\run.ps1 docker-start'"
    }
    
    promptforge web
}

function Start-Tests {
    Write-Info "Lancement des tests..."
    python -m pytest tests/ -v
}

function Show-Status {
    Write-Info "Statut PromptForge"
    promptforge status
}

# ===========================================
# Aide
# ===========================================

function Show-Help {
    Write-Host ""
    Write-Host "  PromptForge - Reformateur intelligent de prompts" -ForegroundColor Cyan
    Write-Host "  ================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Usage: " -NoNewline
    Write-Host ".\run.ps1 <commande>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  INSTALLATION" -ForegroundColor Green
    Write-Host "    install          Installer PromptForge (base)"
    Write-Host "    install-web      Installer avec interface web (Gradio)"
    Write-Host "    install-dev      Installer avec outils de dev"
    Write-Host "    install-all      Installer tout"
    Write-Host ""
    Write-Host "  UTILISATION LOCALE" -ForegroundColor Green
    Write-Host "    web              Lancer l'interface web"
    Write-Host "    status           Voir le statut"
    Write-Host "    test             Lancer les tests"
    Write-Host ""
    Write-Host "  DOCKER" -ForegroundColor Green
    Write-Host "    docker-start     Demarrer Ollama + telecharger modele"
    Write-Host "    docker-stop      Arreter les services"
    Write-Host "    docker-status    Voir le statut des conteneurs"
    Write-Host "    docker-web       Lancer l'interface web (Docker)"
    Write-Host "    docker-logs      Voir les logs (defaut: ollama)"
    Write-Host "    docker-shell     Shell interactif"
    Write-Host "    docker-build     Construire les images"
    Write-Host "    docker-run       Executer une commande promptforge"
    Write-Host "    docker-clean     Supprimer conteneurs et volumes"
    Write-Host ""
    Write-Host "  EXEMPLES" -ForegroundColor Green
    Write-Host "    .\run.ps1 docker-start" -ForegroundColor DarkGray
    Write-Host "    .\run.ps1 docker-web" -ForegroundColor DarkGray
    Write-Host "    .\run.ps1 docker-run list" -ForegroundColor DarkGray
    Write-Host "    .\run.ps1 docker-run format 'cree une API REST'" -ForegroundColor DarkGray
    Write-Host ""
}

# ===========================================
# Main
# ===========================================

switch ($Command.ToLower()) {
    # Installation
    "install"       { Install-Basic }
    "install-web"   { Install-Web }
    "install-dev"   { Install-Dev }
    "install-all"   { Install-All }
    
    # Local
    "web"           { Start-Web }
    "status"        { Show-Status }
    "test"          { Start-Tests }
    
    # Docker
    "docker-start"  { Docker-Start }
    "docker-stop"   { Docker-Stop }
    "docker-status" { Docker-Status }
    "docker-web"    { Docker-Web }
    "docker-logs"   { Docker-Logs }
    "docker-shell"  { Docker-Shell }
    "docker-build"  { Docker-Build }
    "docker-run"    { Docker-Run }
    "docker-clean"  { Docker-Clean }
    
    # Aide
    "help"          { Show-Help }
    "-h"            { Show-Help }
    "--help"        { Show-Help }
    
    default { 
        Write-Err "Commande inconnue: $Command"
        Show-Help
    }
}
