#!/usr/bin/env python3
"""
Script helper cross-platform pour Docker.
Fonctionne sur Windows, Linux et macOS.
"""

import subprocess
import sys
import time
import argparse
import shutil
from pathlib import Path

# Couleurs (désactivées sur Windows si pas de support)
try:
    import os
    if os.name == 'nt':
        os.system('color')  # Active les couleurs ANSI sur Windows 10+
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    NC = '\033[0m'
except:
    GREEN = RED = YELLOW = BLUE = NC = ''


def log_info(msg):
    print(f"{GREEN}[INFO]{NC} {msg}")


def log_warn(msg):
    print(f"{YELLOW}[WARN]{NC} {msg}")


def log_error(msg):
    print(f"{RED}[ERROR]{NC} {msg}")


def get_docker_compose_cmd():
    """Retourne la commande docker compose appropriée."""
    # Essayer docker compose (v2)
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return ["docker", "compose"]
    
    # Essayer docker-compose (v1)
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    
    log_error("Docker Compose n'est pas installé")
    sys.exit(1)


def docker_compose(*args):
    """Exécute une commande docker compose."""
    cmd = get_docker_compose_cmd() + list(args)
    return subprocess.run(cmd)


def check_docker():
    """Vérifie que Docker est installé et fonctionne."""
    if not shutil.which("docker"):
        log_error("Docker n'est pas installé")
        log_info("Téléchargez Docker sur https://www.docker.com/products/docker-desktop")
        sys.exit(1)
    
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        log_error("Docker n'est pas démarré")
        log_info("Lancez Docker Desktop ou le service Docker")
        sys.exit(1)


def cmd_start(args):
    """Démarre les services."""
    log_info("Démarrage d'Ollama...")
    docker_compose("up", "-d", "ollama")
    
    log_info("Attente du démarrage d'Ollama...")
    time.sleep(5)
    
    # Vérifier si le modèle est déjà téléchargé
    result = subprocess.run(
        ["docker", "exec", "promptforge-ollama", "ollama", "list"],
        capture_output=True,
        text=True
    )
    
    if "llama3.1" not in result.stdout:
        log_info("Téléchargement du modèle llama3.1 (peut prendre plusieurs minutes)...")
        subprocess.run(
            ["docker", "exec", "promptforge-ollama", "ollama", "pull", "llama3.1"]
        )
    else:
        log_info("Modèle llama3.1 déjà disponible")
    
    log_info("Services prêts !")


def cmd_stop(args):
    """Arrête les services."""
    log_info("Arrêt des services...")
    docker_compose("down")


def cmd_status(args):
    """Affiche le statut."""
    log_info("Statut des conteneurs:")
    docker_compose("ps")
    
    print()
    log_info("Test de connexion Ollama:")
    
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"{GREEN}✓ Ollama accessible{NC}")
                import json
                data = json.loads(response.read().decode())
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    print("Modèles disponibles:")
                    for m in models[:5]:
                        print(f"  - {m}")
                else:
                    print("  (aucun modèle)")
    except Exception:
        print(f"{RED}✗ Ollama non accessible{NC}")


def cmd_run(args):
    """Exécute une commande promptforge."""
    docker_compose(
        "run", "--rm", "promptforge",
        "promptforge", "--path", "/data",
        *args.cmd
    )


def cmd_web(args):
    """Lance l'interface web."""
    log_info("Lancement de l'interface web...")
    docker_compose("up", "-d", "ollama", "promptforge-web")
    log_info(f"Interface disponible sur {BLUE}http://localhost:7860{NC}")


def cmd_logs(args):
    """Affiche les logs."""
    service = args.service or "ollama"
    docker_compose("logs", "-f", service)


def cmd_shell(args):
    """Lance un shell interactif."""
    log_info("Mode interactif - tapez 'exit' pour quitter")
    docker_compose("run", "--rm", "promptforge")


def cmd_build(args):
    """Construit les images."""
    log_info("Construction des images...")
    docker_compose("build")


def cmd_clean(args):
    """Nettoie tout."""
    log_warn("Ceci va supprimer tous les conteneurs et volumes PromptForge")
    confirm = input("Continuer ? [y/N] ")
    if confirm.lower() == 'y':
        docker_compose("down", "-v")
        log_info("Nettoyage terminé")
    else:
        print("Annulé.")


def main():
    parser = argparse.ArgumentParser(
        description="PromptForge Docker Helper (Cross-platform)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commandes")
    
    # start
    subparsers.add_parser("start", help="Démarrer Ollama et télécharger le modèle")
    
    # stop
    subparsers.add_parser("stop", help="Arrêter tous les services")
    
    # status
    subparsers.add_parser("status", help="Afficher le statut")
    
    # run
    run_parser = subparsers.add_parser("run", help="Exécuter une commande promptforge")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Commande à exécuter")
    
    # web
    subparsers.add_parser("web", help="Lancer l'interface web")
    
    # logs
    logs_parser = subparsers.add_parser("logs", help="Afficher les logs")
    logs_parser.add_argument("service", nargs="?", help="Service (défaut: ollama)")
    
    # shell
    subparsers.add_parser("shell", help="Shell interactif")
    
    # build
    subparsers.add_parser("build", help="Construire les images")
    
    # clean
    subparsers.add_parser("clean", help="Supprimer conteneurs et volumes")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    check_docker()
    
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "run": cmd_run,
        "web": cmd_web,
        "logs": cmd_logs,
        "shell": cmd_shell,
        "build": cmd_build,
        "clean": cmd_clean,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
