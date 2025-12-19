#!/usr/bin/env python3
"""
PromptForge Build System
========================
Script central pour construire les images Docker et gérer les dépendances.

Usage:
    python scripts/build.py [command] [options]

Commands:
    build       Construire les images Docker
    rebuild     Reconstruire les images (avec cache)
    clean       Nettoyer les images et conteneurs
    status      Afficher l'état des images
    deps        Installer les dépendances Python
"""

import subprocess
import sys
import os
import json
import argparse
from pathlib import Path

# Configurations Docker Compose disponibles
COMPOSE_FILES = {
    "nvidia": "docker-compose.yml",
    "linux-amd": "docker-compose.amd.yml",
    "linux-amd-max": "docker-compose.amd-max.yml",
    "cpu": "docker-compose.cpu.yml",
    "win-amd": "docker-compose.win-amd.yml",
    "win-nvidia-native": "docker-compose.win-nvidia.yml"
}

# Couleurs pour le terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_status(msg, status="info"):
    """Affiche un message avec couleur."""
    colors = {
        "info": Colors.BLUE,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED
    }
    color = colors.get(status, Colors.RESET)
    print(f"{color}{msg}{Colors.RESET}")

def run_cmd(cmd, capture=False):
    """Exécute une commande shell."""
    print_status(f"  → {' '.join(cmd)}", "info")
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    return result

def get_project_root():
    """Retourne le chemin racine du projet."""
    return Path(__file__).parent.parent

def detect_gpu():
    """Détecte le type de GPU disponible."""
    try:
        # Vérifier NVIDIA
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return "nvidia"
    except:
        pass
    
    try:
        # Vérifier AMD (Linux)
        result = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "amd" in result.stdout.lower() or "radeon" in result.stdout.lower():
            return "linux-amd"
    except:
        pass
    
    # Vérifier AMD sur Windows
    try:
        import platform
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", "Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "amd" in result.stdout.lower() or "radeon" in result.stdout.lower():
                return "win-amd"
    except:
        pass
    
    return "cpu"

def get_compose_file(config=None):
    """Retourne le fichier docker-compose approprié."""
    if config is None:
        config = detect_gpu()
    
    if config not in COMPOSE_FILES:
        print_status(f"Configuration '{config}' inconnue, utilisation de 'cpu'", "warning")
        config = "cpu"
    
    return COMPOSE_FILES[config]

def cmd_status(args):
    """Affiche l'état des images Docker."""
    print_status("\n📦 État des images Docker PromptForge\n", "info")
    
    result = run_cmd([
        "docker", "images", 
        "--filter", "reference=*promptforge*",
        "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    ])
    
    if result.returncode != 0:
        print_status("Erreur lors de la vérification des images", "error")
        return 1
    
    print()
    
    # Vérifier les conteneurs
    print_status("\n🐳 Conteneurs actifs\n", "info")
    run_cmd([
        "docker", "ps",
        "--filter", "name=promptforge",
        "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    ])
    
    return 0

def cmd_build(args):
    """Construit les images Docker."""
    os.chdir(get_project_root())
    compose_file = get_compose_file(args.config)
    
    print_status(f"\n🔨 Construction des images ({compose_file})\n", "info")
    
    cmd = ["docker", "compose", "-f", compose_file, "build"]
    if args.no_cache:
        cmd.append("--no-cache")
    if args.parallel:
        cmd.extend(["--parallel", str(args.parallel)])
    
    result = run_cmd(cmd)
    
    if result.returncode == 0:
        print_status("\n✅ Images construites avec succès!", "success")
    else:
        print_status("\n❌ Erreur lors de la construction", "error")
    
    return result.returncode

def cmd_clean(args):
    """Nettoie les images et conteneurs."""
    os.chdir(get_project_root())
    
    print_status("\n🗑️ Nettoyage Docker\n", "warning")
    
    if not args.force:
        confirm = input("Confirmer le nettoyage? (y/N): ")
        if confirm.lower() != 'y':
            print_status("Annulé", "info")
            return 0
    
    # Arrêter tous les conteneurs
    print_status("\nArrêt des conteneurs...", "info")
    for config, file in COMPOSE_FILES.items():
        if os.path.exists(file):
            run_cmd(["docker", "compose", "-f", file, "down", "-v"])
    
    # Supprimer les images
    if args.images:
        print_status("\nSuppression des images...", "info")
        for config, file in COMPOSE_FILES.items():
            if os.path.exists(file):
                run_cmd(["docker", "compose", "-f", file, "down", "--rmi", "local"])
    
    # Nettoyer les ressources orphelines
    print_status("\nNettoyage des ressources orphelines...", "info")
    run_cmd(["docker", "image", "prune", "-f"])
    run_cmd(["docker", "volume", "prune", "-f"])
    
    print_status("\n✅ Nettoyage terminé!", "success")
    return 0

def cmd_deps(args):
    """Installe les dépendances Python."""
    os.chdir(get_project_root())
    
    print_status("\n📦 Installation des dépendances\n", "info")
    
    # Installer avec pip
    cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
    if args.dev:
        cmd.append("[dev]")
    
    result = run_cmd(cmd)
    
    if result.returncode == 0:
        print_status("\n✅ Dépendances installées!", "success")
    else:
        print_status("\n❌ Erreur lors de l'installation", "error")
    
    return result.returncode

def cmd_up(args):
    """Démarre les services."""
    os.chdir(get_project_root())
    compose_file = get_compose_file(args.config)
    
    print_status(f"\n▶️ Démarrage des services ({compose_file})\n", "info")
    
    cmd = ["docker", "compose", "-f", compose_file, "up", "-d"]
    if args.build:
        cmd.append("--build")
    
    result = run_cmd(cmd)
    
    if result.returncode == 0:
        print_status("\n✅ Services démarrés!", "success")
        print_status("   → PromptForge: http://localhost:7860", "info")
        print_status("   → Ollama: http://localhost:11434", "info")
    
    return result.returncode

def cmd_down(args):
    """Arrête les services."""
    os.chdir(get_project_root())
    compose_file = get_compose_file(args.config)
    
    print_status(f"\n⏹️ Arrêt des services ({compose_file})\n", "info")
    
    result = run_cmd(["docker", "compose", "-f", compose_file, "down"])
    
    if result.returncode == 0:
        print_status("\n✅ Services arrêtés!", "success")
    
    return result.returncode

def main():
    parser = argparse.ArgumentParser(
        description="PromptForge Build System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build.py status              # Voir l'état des images
  python scripts/build.py build               # Construire (auto-détection GPU)
  python scripts/build.py build -c nvidia     # Construire pour NVIDIA
  python scripts/build.py build --no-cache    # Reconstruire sans cache
  python scripts/build.py up                  # Démarrer les services
  python scripts/build.py down                # Arrêter les services
  python scripts/build.py clean               # Nettoyer
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # status
    p_status = subparsers.add_parser("status", help="Afficher l'état des images")
    p_status.set_defaults(func=cmd_status)
    
    # build
    p_build = subparsers.add_parser("build", help="Construire les images")
    p_build.add_argument("-c", "--config", choices=list(COMPOSE_FILES.keys()),
                         help="Configuration GPU (auto-détecté si non spécifié)")
    p_build.add_argument("--no-cache", action="store_true",
                         help="Reconstruire sans utiliser le cache")
    p_build.add_argument("--parallel", type=int, default=None,
                         help="Nombre de builds en parallèle")
    p_build.set_defaults(func=cmd_build)
    
    # clean
    p_clean = subparsers.add_parser("clean", help="Nettoyer les images et conteneurs")
    p_clean.add_argument("-f", "--force", action="store_true",
                         help="Ne pas demander de confirmation")
    p_clean.add_argument("--images", action="store_true",
                         help="Supprimer aussi les images")
    p_clean.set_defaults(func=cmd_clean)
    
    # deps
    p_deps = subparsers.add_parser("deps", help="Installer les dépendances")
    p_deps.add_argument("--dev", action="store_true",
                        help="Inclure les dépendances de développement")
    p_deps.set_defaults(func=cmd_deps)
    
    # up
    p_up = subparsers.add_parser("up", help="Démarrer les services")
    p_up.add_argument("-c", "--config", choices=list(COMPOSE_FILES.keys()),
                      help="Configuration GPU")
    p_up.add_argument("--build", action="store_true",
                      help="Reconstruire avant de démarrer")
    p_up.set_defaults(func=cmd_up)
    
    # down
    p_down = subparsers.add_parser("down", help="Arrêter les services")
    p_down.add_argument("-c", "--config", choices=list(COMPOSE_FILES.keys()),
                        help="Configuration GPU")
    p_down.set_defaults(func=cmd_down)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
