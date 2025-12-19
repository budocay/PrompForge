"""
PromptForge Launcher - Interface de contrôle
Lance avec: python launcher.py
"""

import subprocess
import platform
import os
import sys
import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.error
import re

# Port du launcher
LAUNCHER_PORT = 7850
PROMPTFORGE_PORT = 7860
OLLAMA_PORT = 11434

# État global
state = {
    "os": platform.system(),
    "gpu": None,
    "gpu_type": None,  # "amd", "nvidia", "cpu"
    "gfx_version": None,
    "docker_installed": True,  # Par défaut True, vérifié après
    "docker_running": False,
    "ollama_installed": True,  # Par défaut True, vérifié après
    "ollama_running": False,
    "promptforge_running": False,
    "ollama_model": "qwen3:8b",  # Qwen3 = meilleur raisonnement + post-traitement XML
    "installed_models": [],  # Liste des modèles Ollama installés
    "model_installed": False,  # True si le modèle recommandé est installé
    "docker_compose_file": None,  # Fichier docker-compose sélectionné
    "available_compose_files": [],  # Fichiers disponibles
    "docker_images": {},  # État des images Docker {name: {exists, created, size}}
    "rebuild_needed": False,  # True si les images doivent être reconstruites
    "last_build_time": None,  # Timestamp du dernier build
    "logs": [],
    "action_in_progress": False
}

# Modèles recommandés selon le type de GPU
# IMPORTANT: Les petits modèles (4b, 8b) suivent moins bien les instructions XML
# mais sont nécessaires pour les configs limitées
RECOMMENDED_MODELS = {
    "amd": {
        "model": "qwen3:14b",
        "reason": "AMD (12GB+ VRAM) - qwen3:14b pour meilleur suivi XML"
    },
    "nvidia": {
        "model": "qwen3:8b",  # Meilleur raisonnement + post-traitement XML
        "reason": "NVIDIA (8GB+ VRAM) - qwen3:8b (meilleur raisonnement)"
    },
    "cpu": {
        "model": "phi4-mini",  # Optimisé CPU par Microsoft
        "reason": "CPU - phi4-mini (excellent rapport qualite/vitesse sur CPU)"
    },
    "apple": {
        "model": "qwen3:8b",
        "reason": "Apple Silicon - qwen3:8b via Metal (meilleur raisonnement)"
    }
}

# Mapping des docker-compose par configuration
DOCKER_COMPOSE_OPTIONS = {
    "nvidia": {
        "file": "docker-compose.yml",
        "label": "NVIDIA (Docker)",
        "description": "GPU NVIDIA 8GB+ - qwen3:8b (meilleur raisonnement)"
    },
    "win-nvidia-native": {
        "file": "docker-compose.win-nvidia.yml",
        "label": "Windows NVIDIA (Ollama natif)",
        "description": "Si conflit de port: utilise Ollama natif Windows"
    },
    "win-amd": {
        "file": "docker-compose.win-amd.yml",
        "label": "Windows + AMD (Ollama natif)",
        "description": "Pour Windows avec GPU AMD - Ollama tourne en natif"
    },
    "linux-amd": {
        "file": "docker-compose.amd.yml",
        "label": "Linux + AMD",
        "description": "Pour Linux avec GPU AMD 12GB+ - qwen3:14b"
    },
    "linux-amd-max": {
        "file": "docker-compose.amd-max.yml",
        "label": "Linux + AMD MAX (32B)",
        "description": "Pour Linux avec GPU AMD 20GB+ - qwen3:32b"
    },
    "cpu": {
        "file": "docker-compose.cpu.yml",
        "label": "CPU uniquement",
        "description": "Sans GPU - phi4-mini (Microsoft, optimise CPU, 8GB+ RAM)"
    }
}


def log(message):
    """Ajoute un message aux logs."""
    timestamp = time.strftime("%H:%M:%S")
    state["logs"].append(f"[{timestamp}] {message}")
    # Garder seulement les 50 derniers logs
    if len(state["logs"]) > 50:
        state["logs"] = state["logs"][-50:]
    print(f"[{timestamp}] {message}")


def check_installations():
    """Vérifie si Docker et Ollama sont installés (Windows uniquement pour Ollama)."""
    # Vérifier Docker (nécessaire partout)
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            encoding='utf-8',
            errors='replace'
        )
        state["docker_installed"] = result.returncode == 0
        if state["docker_installed"]:
            log(f"Docker: {result.stdout.strip()[:40]}")
    except FileNotFoundError:
        state["docker_installed"] = False
        log("Docker: Non installe")
    except:
        state["docker_installed"] = True  # En cas d'erreur, on suppose installé
    
    # Vérifier Ollama (seulement sur Windows car sur Linux c'est dans Docker)
    if state["os"] == "Windows":
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=3,
                encoding='utf-8',
                errors='replace'
            )
            state["ollama_installed"] = result.returncode == 0
            if state["ollama_installed"]:
                log(f"Ollama: {result.stdout.strip()[:40]}")
        except FileNotFoundError:
            state["ollama_installed"] = False
            log("Ollama: Non installe")
        except:
            state["ollama_installed"] = True
    else:
        # Sur Linux, Ollama est dans Docker, pas besoin de l'installer
        state["ollama_installed"] = True


def install_ollama_windows():
    """Ouvre la page de téléchargement Ollama pour Windows."""
    log("Ouverture page telechargement Ollama...")
    import webbrowser
    webbrowser.open("https://ollama.com/download/windows")
    log("Installez Ollama puis cliquez 'Rafraichir'")


def install_docker():
    """Ouvre la page de téléchargement Docker."""
    log("Ouverture page telechargement Docker...")
    import webbrowser
    if state["os"] == "Windows":
        webbrowser.open("https://docs.docker.com/desktop/install/windows-install/")
    elif state["os"] == "Darwin":
        webbrowser.open("https://docs.docker.com/desktop/install/mac-install/")
    else:
        webbrowser.open("https://docs.docker.com/engine/install/")
    log("Installez Docker puis cliquez 'Rafraichir'")


def detect_gpu():
    """Détecte le type de GPU."""
    system = platform.system()
    
    if system == "Windows":
        try:
            # Méthode 1: PowerShell (plus fiable)
            result = subprocess.run(
                ["powershell", "-Command", 
                 "Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            output = result.stdout
            
            if result.returncode != 0 or not output.strip():
                # Méthode 2: WMIC fallback
                result = subprocess.run(
                    ["wmic", "path", "win32_videocontroller", "get", "name"],
                    capture_output=True, text=True, timeout=10,
                    encoding='utf-8', errors='replace'
                )
                output = result.stdout
            
            log(f"Detection GPU - Sortie brute: {repr(output[:300])}")
            output_lower = output.lower()
            
            # Détecter AMD
            if "radeon" in output_lower or ("amd" in output_lower and "microsoft" not in output_lower):
                state["gpu_type"] = "amd"
                # Extraire le nom du GPU
                for line in output.split("\n"):
                    line = line.strip()
                    if line and ("radeon" in line.lower() or "amd" in line.lower()):
                        if "Microsoft" not in line and "Name" not in line:
                            state["gpu"] = line
                            break
                
                if not state["gpu"]:
                    state["gpu"] = "AMD Radeon (detecte)"
                
                # Déterminer la version GFX
                gpu_str = state["gpu"] or ""
                if re.search(r"7[0-9]{3}", gpu_str):
                    state["gfx_version"] = "11.0.0"
                    log(f"GPU AMD detecte: {state['gpu']} (RX 7000 -> gfx 11.0.0)")
                elif re.search(r"6[0-9]{3}", gpu_str):
                    state["gfx_version"] = "10.3.0"
                    log(f"GPU AMD detecte: {state['gpu']} (RX 6000 -> gfx 10.3.0)")
                else:
                    state["gfx_version"] = "11.0.0"
                    log(f"GPU AMD detecte: {state['gpu']} (gfx 11.0.0 par defaut)")
                return
                
            # Détecter NVIDIA
            elif "nvidia" in output_lower or "geforce" in output_lower or "rtx" in output_lower or "gtx" in output_lower:
                state["gpu_type"] = "nvidia"
                for line in output.split("\n"):
                    line = line.strip()
                    if line and ("nvidia" in line.lower() or "geforce" in line.lower() or "rtx" in line.lower()):
                        if "Name" not in line:
                            state["gpu"] = line
                            break
                if not state["gpu"]:
                    state["gpu"] = "NVIDIA (detecte)"
                log(f"GPU NVIDIA detecte: {state['gpu']}")
                return
            else:
                log(f"Aucun GPU reconnu dans: {output[:200]}")
                
        except Exception as e:
            log(f"Erreur detection GPU Windows: {e}")
    
    elif system == "Linux":
        try:
            # Essayer lspci
            result = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='replace'
            )
            output = result.stdout.lower()
            
            if "amd" in output or "radeon" in output:
                state["gpu_type"] = "amd"
                state["gpu"] = "AMD Radeon (Linux)"
                state["gfx_version"] = "11.0.0"
                log("GPU AMD detecte (Linux)")
                return
            elif "nvidia" in output:
                state["gpu_type"] = "nvidia"
                state["gpu"] = "NVIDIA (Linux)"
                log("GPU NVIDIA detecte (Linux)")
                return
        except Exception as e:
            log(f"Erreur detection GPU Linux: {e}")
    
    elif system == "Darwin":  # macOS
        state["gpu_type"] = "apple"
        state["gpu"] = "Apple Silicon / Metal"
        log("macOS detecte - utilisation Metal")
        return
    
    # Fallback CPU
    state["gpu_type"] = "cpu"
    state["gpu"] = "Aucun GPU compatible detecte"
    log("Aucun GPU detecte - mode CPU")


def select_recommended_model():
    """Sélectionne le modèle recommandé selon le GPU détecté."""
    gpu_type = state.get("gpu_type", "cpu")
    
    if gpu_type in RECOMMENDED_MODELS:
        recommended = RECOMMENDED_MODELS[gpu_type]
        state["ollama_model"] = recommended["model"]
        log(f"Modele recommande: {recommended['model']} ({recommended['reason']})")
    else:
        # Fallback: qwen3:8b - meilleur raisonnement + post-traitement XML
        state["ollama_model"] = "qwen3:8b"
        log("Modele par defaut: qwen3:8b (GPU non detecte)")


def select_docker_compose():
    """Sélectionne le fichier docker-compose approprié selon l'environnement."""
    system = state["os"]
    gpu_type = state["gpu_type"]
    
    # Déterminer les fichiers disponibles selon l'OS
    if system == "Windows":
        if gpu_type == "amd":
            # AMD sur Windows nécessite Ollama natif (pas de ROCm dans Docker Windows)
            state["docker_compose_file"] = "win-amd"
            state["available_compose_files"] = ["win-amd", "cpu"]
        elif gpu_type == "nvidia":
            # NVIDIA sur Windows: Docker par défaut, natif en option si conflit
            state["docker_compose_file"] = "nvidia"
            state["available_compose_files"] = ["nvidia", "win-nvidia-native", "cpu"]
        else:
            state["docker_compose_file"] = "cpu"
            state["available_compose_files"] = ["cpu"]
    else:  # Linux / Mac
        if gpu_type == "amd":
            state["docker_compose_file"] = "linux-amd"
            state["available_compose_files"] = ["linux-amd", "linux-amd-max", "cpu"]
        elif gpu_type == "nvidia":
            state["docker_compose_file"] = "nvidia"
            state["available_compose_files"] = ["nvidia", "cpu"]
        elif gpu_type == "apple":
            state["docker_compose_file"] = "cpu"  # Apple Silicon utilise Metal via Ollama natif
            state["available_compose_files"] = ["cpu"]
        else:
            state["docker_compose_file"] = "cpu"
            state["available_compose_files"] = ["cpu"]
    
    compose_info = DOCKER_COMPOSE_OPTIONS.get(state["docker_compose_file"], {})
    log(f"Docker Compose selectionne: {compose_info.get('label', state['docker_compose_file'])}")


def check_docker():
    """Vérifie si Docker est lancé."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        state["docker_running"] = result.returncode == 0
        if state["docker_running"]:
            log("Docker: OK")
        else:
            log("Docker: Non disponible")
    except Exception as e:
        state["docker_running"] = False
        log(f"Docker: Erreur - {e}")


def check_ollama():
    """Vérifie si Ollama est accessible et liste les modèles installés."""
    try:
        req = urllib.request.Request(f"http://localhost:{OLLAMA_PORT}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                state["ollama_running"] = True
                data = json.loads(response.read().decode())
                models = [m["name"] for m in data.get("models", [])]
                state["installed_models"] = models
                
                # Vérifier si le modèle recommandé est installé
                current_model = state.get("ollama_model", "qwen3:8b")
                model_installed = is_model_installed(current_model, models)
                state["model_installed"] = model_installed
                
                if model_installed:
                    log(f"Ollama: OK - {len(models)} modele(s) - {current_model} ✓")
                else:
                    log(f"Ollama: OK - {len(models)} modele(s) - ⚠️ {current_model} non installe!")
                return
    except:
        pass
    state["ollama_running"] = False
    state["installed_models"] = []
    state["model_installed"] = False
    log("Ollama: Non disponible")


def is_model_installed(target_model, installed_models):
    """
    Vérifie si un modèle cible est installé.
    Gère les différentes façons dont Ollama peut nommer les modèles:
    - qwen3:14b (exact)
    - qwen3:14b-q4_0 (avec suffixe de quantization)
    - qwen3:latest (tag latest)
    """
    if not installed_models:
        return False
    
    # Normaliser le modèle cible
    if ":" in target_model:
        target_base, target_tag = target_model.split(":", 1)
    else:
        target_base, target_tag = target_model, "latest"
    
    for installed in installed_models:
        # Normaliser le modèle installé
        if ":" in installed:
            inst_base, inst_tag = installed.split(":", 1)
        else:
            inst_base, inst_tag = installed, "latest"
        
        # Cas 1: Correspondance exacte
        if target_model == installed:
            return True
        
        # Cas 2: Même base, tags compatibles
        if target_base == inst_base:
            # Le tag installé commence par le tag cible (ex: 8b vs 8b-q4_0)
            if inst_tag.startswith(target_tag) or target_tag.startswith(inst_tag):
                return True
            # Le modèle cible est le base et latest est installé
            if target_tag == "latest" or inst_tag == "latest":
                return True
    
    return False


def check_promptforge():
    """Vérifie si PromptForge est accessible."""
    try:
        req = urllib.request.Request(f"http://localhost:{PROMPTFORGE_PORT}/")
        with urllib.request.urlopen(req, timeout=3) as response:
            state["promptforge_running"] = response.status == 200
            if state["promptforge_running"]:
                log("PromptForge: OK")
                return
    except:
        pass
    state["promptforge_running"] = False
    log("PromptForge: Non disponible")


def refresh_status():
    """Rafraîchit tous les statuts."""
    check_docker()
    check_ollama()
    check_promptforge()
    check_docker_images()


def check_docker_images():
    """Vérifie l'état des images Docker du projet."""
    if not state["docker_installed"] or not state["docker_running"]:
        state["docker_images"] = {}
        state["rebuild_needed"] = True
        return
    
    try:
        # Lister les images du projet
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}|{{.CreatedAt}}|{{.Size}}", 
             "--filter", "reference=*promptforge*"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10
        )
        
        images = {}
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        name = parts[0]
                        images[name] = {
                            "exists": True,
                            "created": parts[1],
                            "size": parts[2]
                        }
        
        state["docker_images"] = images
        
        # Vérifier si un rebuild est nécessaire
        state["rebuild_needed"] = check_rebuild_needed()
        
        if images:
            log(f"Images Docker: {len(images)} trouvee(s)")
        else:
            log("Images Docker: Aucune (build necessaire)")
            
    except Exception as e:
        log(f"Erreur verification images: {e}")
        state["docker_images"] = {}
        state["rebuild_needed"] = True


def check_rebuild_needed():
    """Vérifie si les images doivent être reconstruites."""
    # Si aucune image n'existe, rebuild nécessaire
    if not state["docker_images"]:
        return True
    
    # Vérifier si les Dockerfiles ont été modifiés après le dernier build
    try:
        dockerfiles = ["Dockerfile", "Dockerfile.web"]
        latest_dockerfile_time = 0
        
        for df in dockerfiles:
            if os.path.exists(df):
                mtime = os.path.getmtime(df)
                latest_dockerfile_time = max(latest_dockerfile_time, mtime)
        
        # Vérifier aussi les fichiers source Python
        src_dir = "promptforge"
        if os.path.isdir(src_dir):
            for f in os.listdir(src_dir):
                if f.endswith(".py"):
                    mtime = os.path.getmtime(os.path.join(src_dir, f))
                    latest_dockerfile_time = max(latest_dockerfile_time, mtime)
        
        # Comparer avec le temps de création des images
        for img_info in state["docker_images"].values():
            created_str = img_info.get("created", "")
            # Format: "2024-01-15 10:30:00 +0000 UTC"
            # Simplification: on considère rebuild nécessaire si fichiers modifiés récemment
            pass
        
        state["last_build_time"] = latest_dockerfile_time
        return False
        
    except Exception as e:
        return True


def rebuild_docker_images(force=False):
    """Reconstruit les images Docker."""
    compose_key = state.get("docker_compose_file", "cpu")
    compose_info = DOCKER_COMPOSE_OPTIONS.get(compose_key, DOCKER_COMPOSE_OPTIONS["cpu"])
    compose_file = compose_info["file"]
    
    if not os.path.exists(compose_file):
        log(f"ERREUR: Fichier {compose_file} non trouve!")
        return False
    
    log(f"Reconstruction des images Docker{' (no-cache)' if force else ''}...")
    
    # Arrêter les conteneurs existants d'abord
    log("Arret des conteneurs existants...")
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "down", "--remove-orphans"],
        capture_output=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # IMPORTANT: Mettre à jour l'état immédiatement après l'arrêt
    # pour que le bouton d'accès UI soit masqué
    state["promptforge_running"] = False
    state["ollama_running"] = False
    
    # Construire les images
    cmd = ["docker", "compose", "-f", compose_file, "build"]
    if force:
        cmd.append("--no-cache")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode == 0:
        log("Images reconstruites avec succes")
        check_docker_images()
        state["rebuild_needed"] = False
        return True
    else:
        error_msg = result.stderr[:200] if result.stderr else "Erreur inconnue"
        log(f"Erreur build: {error_msg}")
        return False


def clean_docker():
    """Nettoie les images et conteneurs Docker du projet."""
    log("Nettoyage Docker en cours...")
    
    # IMPORTANT: Mettre à jour l'état immédiatement
    # pour que le bouton d'accès UI soit masqué pendant le nettoyage
    state["promptforge_running"] = False
    state["ollama_running"] = False
    
    # Arrêter tous les conteneurs du projet
    for key, info in DOCKER_COMPOSE_OPTIONS.items():
        if os.path.exists(info["file"]):
            subprocess.run(
                ["docker", "compose", "-f", info["file"], "down", "-v", "--rmi", "local"],
                capture_output=True,
                encoding='utf-8',
                errors='replace'
            )
    
    # Supprimer les images orphelines
    subprocess.run(
        ["docker", "image", "prune", "-f"],
        capture_output=True,
        encoding='utf-8',
        errors='replace'
    )
    
    log("Nettoyage termine")
    check_docker_images()


def start_ollama():
    """Démarre Ollama."""
    if state["os"] == "Windows":
        # Sur Windows, lancer Ollama nativement
        log("Demarrage d'Ollama...")
        env = os.environ.copy()
        env["OLLAMA_HOST"] = "0.0.0.0:11434"
        if state["gfx_version"]:
            env["HSA_OVERRIDE_GFX_VERSION"] = state["gfx_version"]
        
        subprocess.Popen(
            ["ollama", "serve"],
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if state["os"] == "Windows" else 0
        )
        time.sleep(5)
        check_ollama()
    else:
        log("Sur Linux/Mac, Ollama est gere par Docker")


def stop_ollama():
    """Arrête Ollama."""
    if state["os"] == "Windows":
        log("Arret d'Ollama...")
        subprocess.run(["taskkill", "/IM", "ollama.exe", "/F"], 
                      capture_output=True,
                      encoding='utf-8',
                      errors='replace')
        time.sleep(2)
        check_ollama()


def start_promptforge():
    """Démarre PromptForge via Docker."""
    log("Demarrage de PromptForge...")
    
    # Utiliser le docker-compose sélectionné
    compose_key = state.get("docker_compose_file", "cpu")
    compose_info = DOCKER_COMPOSE_OPTIONS.get(compose_key, DOCKER_COMPOSE_OPTIONS["cpu"])
    compose_file = compose_info["file"]
    
    log(f"Utilisation de {compose_file} ({compose_info['label']})")
    
    # Vérifier que le fichier existe
    if not os.path.exists(compose_file):
        log(f"ERREUR: Fichier {compose_file} non trouve!")
        return
    
    # Créer le dossier data s'il n'existe pas (pour la persistance SQLite)
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/projects", exist_ok=True)
    os.makedirs("data/history", exist_ok=True)
    
    # Sur Windows, arrêter Ollama natif si on utilise une config Docker avec Ollama
    # (pour éviter le conflit de port 11434)
    if state["os"] == "Windows" and compose_key not in ["win-nvidia-native", "win-amd"]:
        log("Arret d'Ollama natif (liberation port 11434)...")
        subprocess.run(
            ["taskkill", "/IM", "ollama.exe", "/F"],
            capture_output=True,
            encoding='utf-8',
            errors='replace'
        )
        # Aussi arrêter le service Ollama s'il existe
        subprocess.run(
            ["sc", "stop", "ollama"],
            capture_output=True,
            encoding='utf-8',
            errors='replace'
        )
        time.sleep(2)  # Attendre la libération du port
    
    # Arrêter les conteneurs existants pour éviter les conflits
    log("Nettoyage des conteneurs existants...")
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "down", "--remove-orphans"],
        capture_output=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # Démarrer les services
    log("Lancement des services...")
    result = subprocess.run(
        ["docker", "compose", "-f", compose_file, "up", "-d", "--build"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode == 0:
        log("Docker compose demarre")
        time.sleep(10)
    else:
        error_msg = result.stderr[:200] if result.stderr else "Erreur inconnue"
        log(f"Erreur: {error_msg}")
    
    check_promptforge()


def stop_promptforge():
    """Arrête PromptForge."""
    log("Arret de PromptForge...")
    
    # Arrêter avec le fichier actuel
    compose_key = state.get("docker_compose_file", "cpu")
    compose_info = DOCKER_COMPOSE_OPTIONS.get(compose_key, DOCKER_COMPOSE_OPTIONS["cpu"])
    compose_file = compose_info["file"]
    
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "down"],
        capture_output=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # Aussi essayer les autres au cas où
    for key, info in DOCKER_COMPOSE_OPTIONS.items():
        if key != compose_key:
            subprocess.run(
                ["docker", "compose", "-f", info["file"], "down"],
                capture_output=True,
                encoding='utf-8',
                errors='replace'
            )
    
    time.sleep(2)
    check_promptforge()


def pull_model(model_name):
    """Télécharge un modèle Ollama."""
    log(f"Telechargement de {model_name}...")
    state["ollama_model"] = model_name
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            log(f"Modele {model_name} pret")
            # Rafraîchir la liste des modèles installés
            check_ollama()
        else:
            error_msg = result.stderr[:100] if result.stderr else "Erreur inconnue"
            log(f"Erreur telechargement: {error_msg}")
    except Exception as e:
        log(f"Erreur pull: {str(e)[:100]}")


# === HTML de l'interface ===
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PromptForge Launcher</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4KICA8ZGVmcz4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZmlyZSIgeDE9IjAlIiB5MT0iMTAwJSIgeDI9IjAlIiB5Mj0iMCUiPgogICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdHlsZT0ic3RvcC1jb2xvcjojZmY0ZDAwIi8+CiAgICAgIDxzdG9wIG9mZnNldD0iMTAwJSIgc3R5bGU9InN0b3AtY29sb3I6I2ZmYjM0NyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0ibWV0YWwiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4KICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3R5bGU9InN0b3AtY29sb3I6IzVhNWE1YSIvPgogICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiMyZDJkMmQiLz4KICAgIDwvbGluZWFyR3JhZGllbnQ+CiAgPC9kZWZzPgogIDxyZWN0IHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgcng9IjEyIiBmaWxsPSIjMWExYTJlIi8+CiAgPGVsbGlwc2UgY3g9IjMyIiBjeT0iNTAiIHJ4PSIxOCIgcnk9IjYiIGZpbGw9IiNmZjZiMzUiIG9wYWNpdHk9IjAuNCIvPgogIDxwYXRoIGQ9Ik0xOCA0OCBMMjIgNDAgTDQyIDQwIEw0NiA0OCBaIiBmaWxsPSJ1cmwoI21ldGFsKSIvPgogIDxyZWN0IHg9IjIwIiB5PSIzNiIgd2lkdGg9IjI0IiBoZWlnaHQ9IjYiIHJ4PSIxIiBmaWxsPSIjNGE0YTRhIi8+CiAgPHBhdGggZD0iTTI2IDM4IEwyMiA0MiBMMjYgNDYiIHN0cm9rZT0iI2ZmNmIzNSIgc3Ryb2tlLXdpZHRoPSIyLjUiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgogIDxwYXRoIGQ9Ik0zOCAzOCBMNDIgNDIgTDM4IDQ2IiBzdHJva2U9IiNmZjZiMzUiIHN0cm9rZS13aWR0aD0iMi41IiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KICA8ZyB0cmFuc2Zvcm09InJvdGF0ZSgtNDAsIDQwLCAyNCkiPgogICAgPHJlY3QgeD0iMzYiIHk9IjE4IiB3aWR0aD0iNCIgaGVpZ2h0PSIyNCIgcng9IjEiIGZpbGw9IiMzZDNkM2QiLz4KICAgIDxyZWN0IHg9IjMwIiB5PSIxMiIgd2lkdGg9IjE2IiBoZWlnaHQ9IjgiIHJ4PSIyIiBmaWxsPSIjNGE0YTRhIi8+CiAgPC9nPgogIDxjaXJjbGUgY3g9IjI4IiBjeT0iMzAiIHI9IjIiIGZpbGw9IiNmZmRkMDAiLz4KICA8Y2lyY2xlIGN4PSIzNiIgY3k9IjI4IiByPSIyIiBmaWxsPSIjZmZhYTAwIi8+CiAgPGNpcmNsZSBjeD0iMjQiIGN5PSIzNCIgcj0iMS41IiBmaWxsPSIjZmY4ODAwIi8+CiAgPGNpcmNsZSBjeD0iNDAiIGN5PSIzMiIgcj0iMS41IiBmaWxsPSIjZmZjYzAwIi8+Cjwvc3ZnPg==">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .card h2 {
            margin-bottom: 15px;
            font-size: 1.3em;
            color: #00d4ff;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .status-item {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .status-item .icon {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .status-item .label {
            font-size: 0.9em;
            color: #aaa;
        }
        .status-item .value {
            font-size: 1.1em;
            margin-top: 5px;
        }
        .status-ok { color: #00ff88; }
        .status-error { color: #ff4757; }
        .status-warning { color: #ffa502; }
        .status-warning { color: #ffa502; }
        .btn-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .btn {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-primary {
            background: linear-gradient(90deg, #00d4ff, #0099cc);
            color: #fff;
        }
        .btn-success {
            background: linear-gradient(90deg, #00ff88, #00cc6a);
            color: #000;
        }
        .btn-danger {
            background: linear-gradient(90deg, #ff4757, #cc3344);
            color: #fff;
        }
        .btn-secondary {
            background: rgba(255,255,255,0.2);
            color: #fff;
        }
        .btn-large {
            padding: 20px 40px;
            font-size: 1.3em;
            width: 100%;
        }
        .logs {
            background: #000;
            border-radius: 10px;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Consolas', monospace;
            font-size: 0.85em;
            color: #0f0;
        }
        .gpu-amd { border-left: 4px solid #ed1c24; }
        .gpu-nvidia { border-left: 4px solid #76b900; }
        .gpu-apple { border-left: 4px solid #a3aaae; }
        .gpu-cpu { border-left: 4px solid #888; }
        select {
            padding: 10px;
            border-radius: 8px;
            border: none;
            background: #2a2a4e;
            color: #fff;
            font-size: 1em;
            cursor: pointer;
        }
        select option { 
            background: #1a1a2e; 
            color: #fff;
            padding: 8px;
        }
        select optgroup {
            background: #0a0a1e;
            color: #4dabf7;
            font-weight: bold;
            font-style: normal;
            padding: 5px;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="display: flex; align-items: center; justify-content: center; gap: 15px;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" style="flex-shrink: 0;">
                <defs>
                    <linearGradient id="fire" x1="0%" y1="100%" x2="0%" y2="0%">
                        <stop offset="0%" style="stop-color:#ff4d00"/>
                        <stop offset="100%" style="stop-color:#ffb347"/>
                    </linearGradient>
                    <linearGradient id="metal" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#5a5a5a"/>
                        <stop offset="100%" style="stop-color:#2d2d2d"/>
                    </linearGradient>
                </defs>
                <rect width="64" height="64" rx="12" fill="#1a1a2e"/>
                <ellipse cx="32" cy="50" rx="18" ry="6" fill="#ff6b35" opacity="0.4"/>
                <path d="M18 48 L22 40 L42 40 L46 48 Z" fill="url(#metal)"/>
                <rect x="20" y="36" width="24" height="6" rx="1" fill="#4a4a4a"/>
                <path d="M26 38 L22 42 L26 46" stroke="#ff6b35" stroke-width="2.5" fill="none" stroke-linecap="round"/>
                <path d="M38 38 L42 42 L38 46" stroke="#ff6b35" stroke-width="2.5" fill="none" stroke-linecap="round"/>
                <g transform="rotate(-40, 40, 24)">
                    <rect x="36" y="18" width="4" height="24" rx="1" fill="#3d3d3d"/>
                    <rect x="30" y="12" width="16" height="8" rx="2" fill="#4a4a4a"/>
                </g>
                <circle cx="28" cy="30" r="2" fill="#ffdd00"/>
                <circle cx="36" cy="28" r="2" fill="#ffaa00"/>
                <circle cx="24" cy="34" r="1.5" fill="#ff8800"/>
                <circle cx="40" cy="32" r="1.5" fill="#ffcc00"/>
            </svg>
            <span>Prompt<span style="color: #ff6b35;">Forge</span> Launcher</span>
        </h1>
        
        <!-- Détection système -->
        <div class="card" id="system-card">
            <h2>🖥️ Systeme detecte</h2>
            <div class="status-grid">
                <div class="status-item" id="gpu-status">
                    <div class="icon">🎮</div>
                    <div class="label">GPU</div>
                    <div class="value" id="gpu-value">Detection...</div>
                </div>
                <div class="status-item">
                    <div class="icon">🐳</div>
                    <div class="label">Docker</div>
                    <div class="value" id="docker-value">Verification...</div>
                </div>
                <div class="status-item">
                    <div class="icon">🦙</div>
                    <div class="label">Ollama</div>
                    <div class="value" id="ollama-value">Verification...</div>
                </div>
                <div class="status-item">
                    <div class="icon">🔧</div>
                    <div class="label">PromptForge</div>
                    <div class="value" id="promptforge-value">Verification...</div>
                </div>
            </div>
        </div>
        
        <!-- Alertes d'installation (Windows uniquement) -->
        <div class="card" id="install-alert" style="display: none; border-left: 4px solid #ffa502;">
            <h2>⚠️ Installation requise</h2>
            <div id="alert-content"></div>
        </div>
        
        <!-- Contrôles -->
        <div class="card">
            <h2>⚡ Controles</h2>
            
            <!-- Configuration Docker Compose -->
            <div class="config-section" style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                    <div>
                        <label style="display: block; font-size: 0.85em; color: #aaa; margin-bottom: 5px;">Configuration Docker:</label>
                        <select id="compose-select" onchange="selectCompose(this.value)" style="min-width: 250px;">
                            <!-- Options générées dynamiquement -->
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-size: 0.85em; color: #aaa; margin-bottom: 5px;">Modele IA:</label>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <select id="model-select" onchange="onModelChange(this.value)">
                                <optgroup label="🖥️ CPU Only (8GB+ RAM) - Optimises pour CPU">
                                    <option value="phi4-mini">phi4-mini (2.5GB) - Microsoft, excellent CPU</option>
                                    <option value="gemma3n:e4b">gemma3n:e4b (3GB) - Google, edge optimise</option>
                                    <option value="qwen3:4b">qwen3:4b (3GB) - Qwen leger</option>
                                    <option value="llama3.2:3b">llama3.2:3b (2GB) - Meta ultra leger</option>
                                </optgroup>
                                <optgroup label="⚡ GPU 8GB - Recommandés pour PromptForge">
                                    <option value="qwen3:8b" selected>qwen3:8b (5GB) - Meilleur raisonnement ⭐</option>
                                    <option value="llama3.1:8b">llama3.1:8b (5GB) - Meilleur format natif</option>
                                    <option value="mistral:7b">mistral:7b (4GB) - Alternative légère</option>
                                </optgroup>
                                <optgroup label="⭐ GPU 12GB+ (qualité supérieure)">
                                    <option value="llama3.1:70b">llama3.1:70b (40GB) - Qualité maximale</option>
                                    <option value="qwen3:14b">qwen3:14b (9GB) - Recommande pour qualite</option>
                                    <option value="qwen2.5:14b">qwen2.5:14b (9GB) - Alternative stable</option>
                                    <option value="deepseek-r1:14b">deepseek-r1:14b (9GB) - Raisonnement</option>
                                </optgroup>
                                <optgroup label="💪 GPU 20GB+ (excellent suivi XML)">
                                    <option value="qwen3:32b">qwen3:32b (20GB) - Meilleure qualite</option>
                                    <option value="qwen3:30b-a3b">qwen3:30b-a3b (18GB) - MoE optimal</option>
                                    <option value="deepseek-r1:32b">deepseek-r1:32b (20GB) - Raisonnement max</option>
                                </optgroup>
                                <optgroup label="💻 Specialises Code">
                                    <option value="qwen2.5-coder:7b">qwen2.5-coder:7b (5GB) - Code GPU 8GB</option>
                                    <option value="qwen2.5-coder:14b">qwen2.5-coder:14b (9GB) - Code GPU 12GB+</option>
                                </optgroup>
                            </select>
                            <span id="model-status" style="font-size: 1.2em;" title="Statut du modele"></span>
                        </div>
                        <div style="margin-top: 5px; font-size: 0.75em; color: #4CAF50;">
                            ✅ qwen3:8b recommandé - Meilleur raisonnement (format XML via post-traitement)
                        </div>
                    </div>
                </div>
                <div id="compose-description" style="margin-top: 10px; font-size: 0.85em; color: #888;"></div>
            </div>
            
            <div class="btn-grid">
                <button class="btn btn-primary" onclick="action('start_ollama')" id="btn-ollama-start">
                    ▶️ Demarrer Ollama
                </button>
                <button class="btn btn-danger" onclick="action('stop_ollama')" id="btn-ollama-stop">
                    ⏹️ Arreter Ollama
                </button>
                <button class="btn btn-primary" onclick="action('start_promptforge')" id="btn-pf-start">
                    ▶️ Demarrer PromptForge
                </button>
                <button class="btn btn-danger" onclick="action('stop_promptforge')" id="btn-pf-stop">
                    ⏹️ Arreter PromptForge
                </button>
                <button class="btn btn-secondary" onclick="action('pull_model')" id="btn-pull">
                    📥 Telecharger modele
                </button>
                <button class="btn btn-secondary" onclick="action('refresh')">
                    🔄 Rafraichir
                </button>
            </div>
            
            <!-- Outils Docker -->
            <div style="margin-top: 20px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                <h3 style="margin-bottom: 10px; font-size: 1em; color: #aaa;">🐳 Outils Docker</h3>
                <div id="docker-images-status" style="font-size: 0.85em; margin-bottom: 10px; color: #888;"></div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-secondary" onclick="action('rebuild')" id="btn-rebuild" style="font-size: 0.9em;">
                        🔨 Rebuild images
                    </button>
                    <button class="btn btn-secondary" onclick="action('rebuild_force')" id="btn-rebuild-force" style="font-size: 0.9em;">
                        🔥 Rebuild (no-cache)
                    </button>
                    <button class="btn btn-danger" onclick="confirmClean()" id="btn-clean" style="font-size: 0.9em;">
                        🗑️ Nettoyer
                    </button>
                    <button class="btn btn-secondary" onclick="action('detect_gpu')" style="font-size: 0.9em;">
                        🔍 Re-detecter GPU
                    </button>
                </div>
            </div>
            
            <div style="margin-top: 15px;">
                <label>Forcer le type de GPU:</label>
                <select id="force-gpu" onchange="forceGpu(this.value)">
                    <option value="">-- Auto --</option>
                    <option value="amd">AMD (ROCm)</option>
                    <option value="nvidia">NVIDIA (CUDA)</option>
                    <option value="cpu">CPU uniquement</option>
                </select>
            </div>
        </div>
        
        <!-- Accès PromptForge -->
        <div class="card" id="access-card" style="display: none;">
            <h2>✅ Tout est pret!</h2>
            <button class="btn btn-success btn-large" onclick="openPromptForge()">
                🚀 Acceder a PromptForge
            </button>
        </div>
        
        <!-- Logs -->
        <div class="card">
            <h2>📋 Logs</h2>
            <div class="logs" id="logs"></div>
            <div id="debug" style="margin-top:10px; padding:10px; background:#330; color:#ff0; font-family:monospace; font-size:12px; border-radius:5px;">JS Loading...</div>
        </div>
    </div>
    
    <script>
        function updateUI(data) {
            try {
                // GPU
                const gpuEl = document.getElementById('gpu-value');
                const gpuCard = document.getElementById('gpu-status');
                if (gpuEl) gpuEl.textContent = data.gpu || 'Non detecte';
                if (gpuCard) gpuCard.className = 'status-item gpu-' + (data.gpu_type || 'cpu');
                
                // Docker
                const dockerEl = document.getElementById('docker-value');
                if (dockerEl) {
                    if (!data.docker_installed) {
                        dockerEl.textContent = '❌ Non installe';
                        dockerEl.className = 'value status-error';
                    } else if (data.docker_running) {
                        dockerEl.textContent = '✅ Actif';
                        dockerEl.className = 'value status-ok';
                    } else {
                        dockerEl.textContent = '⚠️ Non demarre';
                        dockerEl.className = 'value status-warning';
                    }
                }
                
                // Ollama
                const ollamaEl = document.getElementById('ollama-value');
                if (ollamaEl) {
                    if (data.os === 'Windows' && !data.ollama_installed) {
                        ollamaEl.textContent = '❌ Non installe';
                        ollamaEl.className = 'value status-error';
                    } else if (data.ollama_running) {
                        ollamaEl.textContent = '✅ Actif';
                        ollamaEl.className = 'value status-ok';
                    } else {
                        ollamaEl.textContent = data.os === 'Windows' ? '⚠️ Non demarre' : '⏳ Via Docker';
                        ollamaEl.className = 'value ' + (data.os === 'Windows' ? 'status-warning' : 'status-ok');
                    }
                }
                
                // PromptForge
                const pfEl = document.getElementById('promptforge-value');
                if (pfEl) {
                    pfEl.textContent = data.promptforge_running ? '✅ Actif' : '❌ Inactif';
                    pfEl.className = 'value ' + (data.promptforge_running ? 'status-ok' : 'status-error');
                }
                
                // Alertes d'installation
                updateInstallAlerts(data);
                
                // Bouton accès
                const accessCard = document.getElementById('access-card');
                if (accessCard) accessCard.style.display = data.promptforge_running ? 'block' : 'none';
                
                // Docker Compose selector
                updateComposeSelector(data);
                
                // État des images Docker
                updateDockerImagesStatus(data);
                
                // Sélectionner le modèle recommandé et mettre à jour l'indicateur
                var modelSelect = document.getElementById('model-select');
                var modelStatus = document.getElementById('model-status');
                if (modelSelect && data.ollama_model) {
                    modelSelect.value = data.ollama_model;
                }
                if (modelStatus) {
                    if (!data.ollama_running) {
                        modelStatus.textContent = '⏸️';
                        modelStatus.title = 'Ollama non demarre';
                    } else if (data.model_installed) {
                        modelStatus.textContent = '✅';
                        modelStatus.title = 'Modele installe et pret';
                    } else {
                        modelStatus.textContent = '⚠️';
                        modelStatus.title = 'Modele non installe - cliquez sur Telecharger';
                    }
                }
                
                // Logs
                const logsEl = document.getElementById('logs');
                if (logsEl && data.logs) {
                    logsEl.innerHTML = data.logs.map(function(l) { return '<div>' + l + '</div>'; }).join('');
                    logsEl.scrollTop = logsEl.scrollHeight;
                }
                
                // Boutons
                const btnOllamaStart = document.getElementById('btn-ollama-start');
                const btnOllamaStop = document.getElementById('btn-ollama-stop');
                const btnPfStart = document.getElementById('btn-pf-start');
                const btnPfStop = document.getElementById('btn-pf-stop');
                
                if (btnOllamaStart) btnOllamaStart.disabled = data.ollama_running || data.action_in_progress || (data.os === 'Windows' && !data.ollama_installed);
                if (btnOllamaStop) btnOllamaStop.disabled = !data.ollama_running || data.action_in_progress;
                if (btnPfStart) btnPfStart.disabled = data.promptforge_running || data.action_in_progress || !data.docker_installed;
                if (btnPfStop) btnPfStop.disabled = !data.promptforge_running || data.action_in_progress;
            } catch (e) {
                console.error('Erreur updateUI:', e);
            }
        }
        
        function updateInstallAlerts(data) {
            try {
                const alertCard = document.getElementById('install-alert');
                const alertContent = document.getElementById('alert-content');
                if (!alertCard || !alertContent) return;
                
                let alerts = [];
            
            // Docker non installé (tous OS)
            if (!data.docker_installed) {
                alerts.push(
                    '<div style="display: flex; align-items: center; gap: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-bottom: 10px;">' +
                    '<span style="font-size: 2.5em;">🐳</span>' +
                    '<div style="flex: 1;"><strong>Docker non installe</strong><p style="margin: 5px 0 0 0; color: #aaa;">Docker est necessaire pour lancer PromptForge.</p></div>' +
                    '<button class="btn btn-primary" onclick="action(&#39;install_docker&#39;)">📥 Installer Docker</button>' +
                    '</div>'
                );
            }
            
            // Ollama non installé (Windows seulement, car sur Linux c'est dans Docker)
            if (data.os === 'Windows' && !data.ollama_installed) {
                alerts.push(
                    '<div style="display: flex; align-items: center; gap: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-bottom: 10px;">' +
                    '<span style="font-size: 2.5em;">🦙</span>' +
                    '<div style="flex: 1;"><strong>Ollama non installe</strong><p style="margin: 5px 0 0 0; color: #aaa;">Sur Windows avec AMD, Ollama doit etre installe separement.</p></div>' +
                    '<button class="btn btn-primary" onclick="action(&#39;install_ollama&#39;)">📥 Installer Ollama</button>' +
                    '</div>'
                );
            }
            
            // Modèle non installé (quand Ollama est actif)
            if (data.ollama_running && !data.model_installed && data.ollama_model) {
                var modelName = data.ollama_model;
                var installedList = (data.installed_models || []).join(', ') || 'aucun';
                alerts.push(
                    '<div style="display: flex; align-items: center; gap: 15px; padding: 15px; background: rgba(255,152,0,0.15); border: 1px solid #ff9800; border-radius: 8px; margin-bottom: 10px;">' +
                    '<span style="font-size: 2.5em;">⚠️</span>' +
                    '<div style="flex: 1;"><strong>Modele ' + modelName + ' non installe</strong>' +
                    '<p style="margin: 5px 0 0 0; color: #aaa;">Modeles disponibles: ' + installedList + '</p></div>' +
                    '<button class="btn btn-primary" onclick="action(&#39;pull_model&#39;)" style="background: #ff9800;">📥 Telecharger ' + modelName + '</button>' +
                    '</div>'
                );
            }
            
            if (alerts.length > 0) {
                alertCard.style.display = 'block';
                alertContent.innerHTML = alerts.join('');
            } else {
                alertCard.style.display = 'none';
            }
            } catch (e) {
                console.error('Erreur updateInstallAlerts:', e);
            }
        }
        
        const COMPOSE_OPTIONS = {
            "nvidia": { label: "NVIDIA (Docker)", desc: "GPU NVIDIA 8GB+ - qwen3:8b (meilleur raisonnement)" },
            "win-nvidia-native": { label: "Windows NVIDIA (Ollama natif)", desc: "Si conflit de port: utilise Ollama natif Windows" },
            "win-amd": { label: "Windows + AMD (Ollama natif)", desc: "Pour Windows avec GPU AMD - Ollama tourne en natif" },
            "linux-amd": { label: "Linux + AMD", desc: "Pour Linux avec GPU AMD 12GB+ - qwen3:14b" },
            "linux-amd-max": { label: "Linux + AMD MAX (32B)", desc: "Pour Linux avec GPU AMD 20GB+ - qwen3:32b" },
            "cpu": { label: "CPU uniquement", desc: "Sans GPU - phi4-mini (Microsoft, optimise CPU)" }
        };
        
        function updateComposeSelector(data) {
            try {
                const select = document.getElementById('compose-select');
                const descEl = document.getElementById('compose-description');
                if (!select || !descEl) return;
                
                // Mettre à jour les options disponibles
                const available = data.available_compose_files || ['cpu'];
                const current = data.docker_compose_file || 'cpu';
                
                select.innerHTML = available.map(function(key) {
                    var opt = COMPOSE_OPTIONS[key] || { label: key };
                    var selected = key === current ? ' selected' : '';
                    return '<option value="' + key + '"' + selected + '>' + opt.label + '</option>';
                }).join('');
                
                // Mettre à jour la description
                const currentOpt = COMPOSE_OPTIONS[current] || {};
                descEl.textContent = currentOpt.desc || '';
            } catch (e) {
                console.error('Erreur updateComposeSelector:', e);
            }
        }
        
        async function onModelChange(model) {
            try {
                const resp = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: 'select_model', model: model})
                });
                const data = await resp.json();
                updateUI(data);
            } catch (e) {
                console.error('Erreur onModelChange:', e);
            }
        }
        
        async function selectCompose(composeKey) {
            try {
                const resp = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: 'select_compose', compose_key: composeKey})
                });
                const data = await resp.json();
                updateUI(data);
            } catch (e) {
                console.error('Erreur selectCompose:', e);
            }
        }
        
        async function action(act) {
            try {
                const modelEl = document.getElementById('model-select');
                const model = modelEl ? modelEl.value : 'qwen3:8b';
                const resp = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: act, model: model})
                });
                const data = await resp.json();
                updateUI(data);
            } catch (e) {
                console.error('Erreur action:', e);
            }
        }
        
        function openPromptForge() {
            window.open('http://localhost:7860', '_blank');
        }
        
        function confirmClean() {
            if (confirm('⚠️ Ceci va supprimer toutes les images Docker du projet.\\nVous devrez les reconstruire.\\n\\nContinuer?')) {
                action('clean_docker');
            }
        }
        
        function updateDockerImagesStatus(data) {
            var el = document.getElementById('docker-images-status');
            if (!el) return;
            
            var images = data.docker_images || {};
            var imageCount = Object.keys(images).length;
            var rebuildNeeded = data.rebuild_needed;
            
            if (imageCount === 0) {
                el.innerHTML = '⚠️ Aucune image - <strong>Build necessaire</strong>';
                el.style.color = '#ff9800';
            } else if (rebuildNeeded) {
                el.innerHTML = '📦 ' + imageCount + ' image(s) - <span style="color:#ff9800">Rebuild recommande</span>';
                el.style.color = '#aaa';
            } else {
                el.innerHTML = '✅ ' + imageCount + ' image(s) prete(s)';
                el.style.color = '#4caf50';
            }
        }
        
        async function forceGpu(gpuType) {
            if (!gpuType) {
                action('detect_gpu');
                return;
            }
            const resp = await fetch('/api/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'force_gpu', gpu_type: gpuType})
            });
            const data = await resp.json();
            updateUI(data);
        }
        
        async function refresh() {
            var dbg = document.getElementById('debug');
            try {
                if (dbg) dbg.innerHTML = 'Fetching...';
                const resp = await fetch('/api/status');
                if (dbg) dbg.innerHTML = 'Got response: ' + resp.status;
                const data = await resp.json();
                if (dbg) dbg.innerHTML = 'Parsed JSON. GPU: ' + (data.gpu || 'null');
                updateUI(data);
                if (dbg) dbg.innerHTML = 'UI Updated! GPU: ' + (data.gpu || 'null') + ', Docker: ' + data.docker_running;
            } catch (e) {
                console.error('Erreur refresh:', e);
                if (dbg) dbg.innerHTML = 'ERROR: ' + e.message;
            }
        }
        
        // Rafraîchir toutes les 3 secondes
        setInterval(refresh, 3000);
        
        // Premier appel
        document.addEventListener('DOMContentLoaded', function() {
            var dbg = document.getElementById('debug');
            if (dbg) dbg.innerHTML = 'DOM Ready, calling refresh...';
            refresh();
        });
    </script>
</body>
</html>
"""


class LauncherHandler(SimpleHTTPRequestHandler):
    """Handler HTTP pour le launcher."""
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/status":
            self.send_json(state)
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == "/api/action":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            action = data.get("action")
            model = data.get("model", state.get("ollama_model", "qwen3:8b"))
            
            state["action_in_progress"] = True
            
            if action == "start_ollama":
                threading.Thread(target=start_ollama).start()
            elif action == "stop_ollama":
                threading.Thread(target=stop_ollama).start()
            elif action == "start_promptforge":
                threading.Thread(target=start_promptforge).start()
            elif action == "stop_promptforge":
                threading.Thread(target=stop_promptforge).start()
            elif action == "pull_model":
                threading.Thread(target=pull_model, args=(model,)).start()
            elif action == "refresh":
                refresh_status()
            elif action == "detect_gpu":
                detect_gpu()
                select_recommended_model()
                select_docker_compose()
            elif action == "force_gpu":
                gpu_type = data.get("gpu_type", "cpu")
                state["gpu_type"] = gpu_type
                if gpu_type == "amd":
                    state["gpu"] = "AMD (force manuellement)"
                    state["gfx_version"] = "11.0.0"
                elif gpu_type == "nvidia":
                    state["gpu"] = "NVIDIA (force manuellement)"
                    state["gfx_version"] = None
                else:
                    state["gpu"] = "CPU (force manuellement)"
                    state["gfx_version"] = None
                log(f"GPU force: {gpu_type}")
                select_recommended_model()  # Mettre à jour le modèle
                select_docker_compose()  # Recalculer le docker-compose
            elif action == "select_compose":
                compose_key = data.get("compose_key", "cpu")
                if compose_key in DOCKER_COMPOSE_OPTIONS:
                    state["docker_compose_file"] = compose_key
                    compose_info = DOCKER_COMPOSE_OPTIONS[compose_key]
                    log(f"Docker Compose change: {compose_info['label']}")
            elif action == "select_model":
                new_model = data.get("model", "qwen3:8b")
                state["ollama_model"] = new_model
                # Vérifier si ce modèle est installé
                installed = state.get("installed_models", [])
                state["model_installed"] = is_model_installed(new_model, installed)
                log(f"Modele selectionne: {new_model}" + (" ✓" if state["model_installed"] else " (non installe)"))
            elif action == "rebuild":
                threading.Thread(target=rebuild_docker_images, args=(False,)).start()
            elif action == "rebuild_force":
                threading.Thread(target=rebuild_docker_images, args=(True,)).start()
            elif action == "clean_docker":
                threading.Thread(target=clean_docker).start()
            elif action == "install_ollama":
                install_ollama_windows()
            elif action == "install_docker":
                install_docker()
            elif action == "check_install":
                check_installations()
            
            time.sleep(1)
            state["action_in_progress"] = False
            self.send_json(state)
        else:
            self.send_error(404)
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        pass  # Désactiver les logs HTTP


def main():
    """Point d'entrée principal."""
    print("=" * 50)
    print("  PromptForge Launcher")
    print("=" * 50)
    print()
    
    # Détection initiale
    log("Demarrage du launcher...")
    detect_gpu()
    select_recommended_model()  # Choisir le modèle selon le GPU
    check_installations()
    select_docker_compose()
    refresh_status()
    
    # Démarrer le serveur
    server = HTTPServer(("0.0.0.0", LAUNCHER_PORT), LauncherHandler)
    log(f"Launcher accessible sur http://localhost:{LAUNCHER_PORT}")
    
    # Ouvrir le navigateur
    import webbrowser
    webbrowser.open(f"http://localhost:{LAUNCHER_PORT}")
    
    print()
    print(f"Interface: http://localhost:{LAUNCHER_PORT}")
    print("Appuie sur Ctrl+C pour quitter")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArret du launcher...")
        server.shutdown()


if __name__ == "__main__":
    main()
