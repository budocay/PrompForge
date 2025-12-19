# ============================================
# PromptForge - Script de mise à jour Windows
# Usage: .\update.ps1 [-Force]
# ============================================

param(
    [switch]$Force
)

Write-Host "🔄 PromptForge - Mise à jour Docker" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

if ($Force) {
    Write-Host "Mode forcé: reconstruction complète sans cache" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "📦 Arrêt des conteneurs..." -ForegroundColor White
    docker compose down
    
    Write-Host "🗑️  Nettoyage des anciennes images..." -ForegroundColor White
    docker compose rm -f 2>$null
    
    Write-Host "🔨 Reconstruction sans cache..." -ForegroundColor White
    docker compose build --no-cache --pull
    
    Write-Host "🚀 Démarrage..." -ForegroundColor White
    docker compose up -d
}
else {
    Write-Host "Mode standard: mise à jour incrémentale" -ForegroundColor White
    Write-Host "(Utilise .\update.ps1 -Force pour une reconstruction complète)" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "📥 Téléchargement des dernières images..." -ForegroundColor White
    docker compose pull
    
    Write-Host "🔨 Reconstruction si nécessaire..." -ForegroundColor White
    docker compose build
    
    Write-Host "🚀 Redémarrage des services..." -ForegroundColor White
    docker compose up -d
}

Write-Host ""
Write-Host "✅ Mise à jour terminée !" -ForegroundColor Green
Write-Host ""

# Afficher le statut
Write-Host "📊 Statut des conteneurs:" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "🌐 Interface disponible sur: http://localhost:7860" -ForegroundColor Green
