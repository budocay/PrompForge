"""
PromptForge Launcher - Interface de contrôle
Lance avec: python launcher.py
"""

import subprocess
import platform
import os
import socket
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

# ---------------------------------------------------------------------------
# Trois etats de service, jamais deux
# ---------------------------------------------------------------------------
# `check_ollama()` ecrivait `False` sur toute exception, delai depasse compris :
# « je ne sais pas » devenait « c'est eteint », et l'utilisateur concluait que
# le produit ne marchait pas. Meme confusion que D-018, ou « non mesurable »
# devenait « pas de GPU ».
#
#   STATUS_UP      : sonde reussie, le service repond comme attendu.
#   STATUS_DOWN    : sonde concluante et negative (connexion refusee, binaire
#                    absent, code de retour non nul). C'est une connaissance.
#   STATUS_UNKNOWN : la sonde n'a pas conclu (delai depasse, reponse illisible,
#                    erreur inattendue). Ce n'est PAS un service eteint.
STATUS_UP = "up"
STATUS_DOWN = "down"
STATUS_UNKNOWN = "unknown"

# ---------------------------------------------------------------------------
# Cadence de rafraichissement de l'etat
# ---------------------------------------------------------------------------
# Le client interroge deja `/api/status` toutes les 3 s, mais le serveur rendait
# le meme dictionnaire fige depuis son demarrage : une instance lancee a 11h14
# affichait encore a 15h l'etat mesure a 11h14. Le rafraichissement est donc
# fait cote serveur, declenche par `/api/status`, avec deux cadences distinctes
# justifiees par le cout mesure de chaque sonde sur la machine de reference :
#
#   ollama /api/tags     4.4 ms   | sondes HTTP sur la boucle locale
#   promptforge /        0.5 ms   |
#   docker info        107.6 ms   | sous-processus vers le demon
#   docker images       88.0 ms   |
#
# (mesure du 2026-09-04, moyenne de 5 appels pour le HTTP, 3 pour Docker)
#
# Les sondes HTTP coutent trois ordres de grandeur de moins que les sondes
# Docker : les separer evite de payer 200 ms de sous-processus toutes les
# deux secondes pour observer un demon qui, lui, ne demarre ni ne s'arrete
# plusieurs fois par minute.
FAST_PROBE_TTL = 2.0    # Ollama + PromptForge : cadence utile au client (3 s)
SLOW_PROBE_TTL = 15.0   # Docker : evenement rare et lent, 15 s suffisent
STALE_AFTER = 10.0      # Au-dela, l'interface declare son etat perime

# Delai des sondes HTTP. Court, parce que la boucle locale ne justifie pas
# davantage : soit rien n'ecoute et l'echec est immediat, soit le service
# repond en quelques millisecondes. Un delai long ne ferait que bloquer plus
# longtemps sur le seul cas ambigu, qui est desormais rendu STATUS_UNKNOWN.
HTTP_PROBE_TIMEOUT = 2.0

# État global
state = {
    "os": platform.system(),
    "gpu": None,
    "gpu_type": None,  # "amd", "nvidia", "cpu"
    "gfx_version": None,
    "docker_installed": True,  # Par défaut True, vérifié après
    "docker_running": False,
    "docker_status": STATUS_UNKNOWN,  # up | down | unknown
    "ollama_installed": True,  # Par défaut True, vérifié après
    "ollama_running": False,
    "ollama_status": STATUS_UNKNOWN,  # up | down | unknown
    "promptforge_running": False,
    "promptforge_status": STATUS_UNKNOWN,  # up | down | unknown
    "ollama_model": "qwen3:8b",  # Qwen3 = meilleur raisonnement + post-traitement XML
    "installed_models": [],  # Liste des modèles Ollama installés
    "model_installed": False,  # True si le modèle recommandé est installé
    "docker_compose_file": None,  # Fichier docker-compose sélectionné
    "available_compose_files": [],  # Fichiers disponibles
    "docker_images": {},  # État des images Docker {name: {exists, created, size}}
    "rebuild_needed": False,  # True si les images doivent être reconstruites
    "last_build_time": None,  # Timestamp du dernier build
    "checked_at": None,  # Epoch de la derniere sonde rapide (None = jamais)
    "checked_at_label": None,  # Meme instant, en HH:MM:SS, pour l'interface
    "docker_checked_at": None,  # Epoch de la derniere sonde Docker
    "probe_in_progress": False,  # Une sonde est en vol (evite l'empilement)
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
#
# `default` est le chemin par defaut de DEC-010 : seule l'interface tourne en
# conteneur, Ollama reste natif sur l'hote, a l'identique sur Windows, macOS et
# Linux. C'est la valeur retenue par `select_docker_compose()` sur les trois
# systemes. Les autres entrees embarquent Ollama en conteneur et ne se
# justifient que si le GPU est expose a Docker, donc jamais sur macOS.
DOCKER_COMPOSE_OPTIONS = {
    "default": {
        "file": "compose.yaml",
        "label": "Par defaut (Ollama natif)",
        "description": "Interface en conteneur, Ollama natif sur l'hote - Windows, macOS, Linux"
    },
    "nvidia": {
        "file": "docker/compose/docker-compose.yml",
        "label": "NVIDIA (Docker)",
        "description": "GPU NVIDIA 8GB+ - qwen3:8b (meilleur raisonnement)"
    },
    "win-nvidia-native": {
        "file": "docker/compose/docker-compose.win-nvidia.yml",
        "label": "Windows NVIDIA (Ollama natif)",
        "description": "Si conflit de port: utilise Ollama natif Windows"
    },
    "win-amd": {
        "file": "docker/compose/docker-compose.win-amd.yml",
        "label": "Windows + AMD (Ollama natif)",
        "description": "Pour Windows avec GPU AMD - Ollama tourne en natif"
    },
    "linux-amd": {
        "file": "docker/compose/docker-compose.amd.yml",
        "label": "Linux + AMD",
        "description": "Pour Linux avec GPU AMD 12GB+ - qwen3:14b"
    },
    "linux-amd-max": {
        "file": "docker/compose/docker-compose.amd-max.yml",
        "label": "Linux + AMD MAX (32B)",
        "description": "Pour Linux avec GPU AMD 20GB+ - qwen3:32b"
    },
    "cpu": {
        "file": "docker/compose/docker-compose.cpu.yml",
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


# Dernier message journalise par sonde, pour n'ecrire qu'aux transitions.
_last_logged = {}


def log_change(key, message):
    """Journalise seulement si le message differe du precedent pour cette cle.

    Les sondes tournent desormais toutes les deux secondes. Les faire ecrire a
    chaque passage noierait en quelques secondes le tampon de cinquante lignes
    et effacerait precisement ce que l'utilisateur cherche a y lire.
    """
    if _last_logged.get(key) == message:
        return False
    _last_logged[key] = message
    log(message)
    return True


def probe_http(url, timeout=HTTP_PROBE_TIMEOUT):
    """Sonde HTTP a trois etats. Rend `(statut, corps)`.

    - `STATUS_DOWN` seulement quand la sonde conclut : rien n'ecoute sur le
      port (connexion refusee), ou l'hote est injoignable.
    - `STATUS_UNKNOWN` des que la sonde ne conclut pas : delai depasse, code
      HTTP inattendu, erreur non prevue. Le corps vaut alors `None`.
    """
    try:
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status == 200:
                return STATUS_UP, response.read()
            # Quelque chose repond, mais pas ce qui est attendu : on ne sait pas.
            return STATUS_UNKNOWN, None
    except urllib.error.HTTPError:
        # Le serveur a repondu : il tourne, mais pas comme prevu.
        return STATUS_UNKNOWN, None
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ConnectionRefusedError):
            return STATUS_DOWN, None
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return STATUS_UNKNOWN, None
        if isinstance(reason, OSError):
            # Hote introuvable, reseau coupe : le service n'est pas la.
            return STATUS_DOWN, None
        return STATUS_UNKNOWN, None
    # `socket.timeout` n'est un alias de `TimeoutError` qu'a partir de 3.10.
    # `launcher.py` amorce une machine nue et tourne sous le Python systeme,
    # soit 3.9.6 ici (D-061), ou les deux classes sont distinctes : appliquer
    # la simplification suggeree par ruff (UP041) casserait silencieusement la
    # distinction entre « delai depasse » et « service eteint » sur la seule
    # machine ou elle compte. Mesure : sous 3.9, `socket.timeout is
    # TimeoutError` rend False ; sous 3.14, True.
    except (socket.timeout, TimeoutError):  # noqa: UP041
        return STATUS_UNKNOWN, None
    except ConnectionRefusedError:
        return STATUS_DOWN, None
    except Exception:
        return STATUS_UNKNOWN, None


def set_service_status(service, status):
    """Ecrit le statut a trois etats et le booleen historique qui en derive.

    Le booleen `<service>_running` est conserve : il est lu ailleurs dans le
    fichier. Il ne vaut `True` que sur `STATUS_UP`, donc « inconnu » n'est
    jamais confondu avec « actif ». L'interface, elle, lit le statut a trois
    etats et distingue « eteint » de « indetermine ».
    """
    state[f"{service}_status"] = status
    state[f"{service}_running"] = status == STATUS_UP
    return status


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
    """Selectionne le fichier docker-compose approprie selon l'environnement.

    Le choix par defaut est `default` (compose.yaml) sur les trois systemes,
    conformement a DEC-010. Les variantes a Ollama conteneurise restent
    proposees la ou elles ont un sens, c'est-a-dire la ou le GPU peut etre
    expose a Docker. Sur macOS, elles ne sont pas proposees du tout : Docker
    Desktop ne passe pas Metal aux conteneurs, un Ollama conteneurise y
    tournerait CPU-only (D-020).
    """
    system = state["os"]
    gpu_type = state["gpu_type"]

    # Chemin par defaut, identique partout.
    state["docker_compose_file"] = "default"

    if system == "Darwin":
        # macOS : aucune variante a Ollama conteneurise n'est proposee.
        state["available_compose_files"] = ["default"]
    elif system == "Windows":
        if gpu_type == "amd":
            # Sur Windows, Docker n'accede pas au GPU AMD : Ollama reste natif.
            state["available_compose_files"] = ["default", "win-amd", "cpu"]
        elif gpu_type == "nvidia":
            state["available_compose_files"] = ["default", "win-nvidia-native", "nvidia", "cpu"]
        else:
            state["available_compose_files"] = ["default", "cpu"]
    else:  # Linux
        if gpu_type == "amd":
            state["available_compose_files"] = ["default", "linux-amd", "linux-amd-max", "cpu"]
        elif gpu_type == "nvidia":
            state["available_compose_files"] = ["default", "nvidia", "cpu"]
        else:
            state["available_compose_files"] = ["default", "cpu"]

    compose_info = DOCKER_COMPOSE_OPTIONS.get(state["docker_compose_file"], {})
    log(f"Docker Compose selectionne: {compose_info.get('label', state['docker_compose_file'])}")


def check_docker():
    """Sonde le demon Docker. Rend un des trois statuts.

    `TimeoutExpired` ne veut pas dire « Docker est eteint » : le demon peut
    etre en train de demarrer. Ce cas rend `STATUS_UNKNOWN`. Un code de
    retour non nul, lui, conclut : le client a parle, le demon n'a pas
    repondu, c'est `STATUS_DOWN`.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
    except subprocess.TimeoutExpired:
        log_change("docker", "Docker: indetermine (delai depasse)")
        return set_service_status("docker", STATUS_UNKNOWN)
    except FileNotFoundError:
        state["docker_installed"] = False
        log_change("docker", "Docker: binaire absent")
        return set_service_status("docker", STATUS_DOWN)
    except Exception as e:
        log_change("docker", f"Docker: indetermine - {e}")
        return set_service_status("docker", STATUS_UNKNOWN)

    if result.returncode == 0:
        log_change("docker", "Docker: OK")
        return set_service_status("docker", STATUS_UP)
    log_change("docker", "Docker: demon non demarre")
    return set_service_status("docker", STATUS_DOWN)


def check_ollama():
    """Sonde Ollama et liste les modeles installes. Rend un des trois statuts.

    Le `except: pass` d'origine ecrasait tout en `False` : un delai depasse,
    donc « je ne sais pas », s'affichait « Ollama non disponible » et
    l'utilisateur en concluait que le produit ne marchait pas.
    """
    status, payload = probe_http(
        f"http://localhost:{OLLAMA_PORT}/api/tags", timeout=HTTP_PROBE_TIMEOUT
    )

    if status == STATUS_UP:
        try:
            data = json.loads(payload.decode("utf-8"))
            models = [m["name"] for m in data.get("models", []) if "name" in m]
        except (ValueError, AttributeError, TypeError, UnicodeDecodeError) as e:
            # Quelque chose ecoute et rend 200, mais pas l'API d'Ollama.
            log_change("ollama", f"Ollama: reponse illisible, etat indetermine - {e}")
            return set_service_status("ollama", STATUS_UNKNOWN)

        state["installed_models"] = models
        current_model = state.get("ollama_model", "qwen3:8b")
        model_installed = is_model_installed(current_model, models)
        state["model_installed"] = model_installed

        if model_installed:
            log_change("ollama", f"Ollama: OK - {len(models)} modele(s) - {current_model} ✓")
        else:
            log_change(
                "ollama",
                f"Ollama: OK - {len(models)} modele(s) - ⚠️ {current_model} non installe!"
            )
        return set_service_status("ollama", STATUS_UP)

    if status == STATUS_DOWN:
        # Rien n'ecoute : aucun modele n'est joignable, l'affirmer est exact.
        state["installed_models"] = []
        state["model_installed"] = False
        log_change("ollama", "Ollama: arrete (aucune ecoute sur le port)")
        return set_service_status("ollama", STATUS_DOWN)

    # Indetermine : on ne sait pas, donc on n'efface pas la derniere liste
    # connue et on ne pretend pas non plus qu'elle est a jour.
    log_change("ollama", "Ollama: etat indetermine (pas de reponse concluante)")
    return set_service_status("ollama", STATUS_UNKNOWN)


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
    """Sonde l'interface PromptForge. Rend un des trois statuts."""
    status, _ = probe_http(f"http://localhost:{PROMPTFORGE_PORT}/", timeout=HTTP_PROBE_TIMEOUT)
    if status == STATUS_UP:
        log_change("promptforge", "PromptForge: OK")
    elif status == STATUS_DOWN:
        log_change("promptforge", "PromptForge: arrete")
    else:
        log_change("promptforge", "PromptForge: etat indetermine")
    return set_service_status("promptforge", status)


# ---------------------------------------------------------------------------
# Ordonnancement des sondes
# ---------------------------------------------------------------------------
# Une seule sonde en vol a la fois : sans cela, un `docker info` lent
# (10 s de delai) verrait s'empiler derriere lui une sonde toutes les
# deux secondes. `_probe_lock` protege la decision, pas l'execution.
_probe_lock = threading.Lock()


def stamp_probe(now=None, include_docker=False):
    """Horodate la derniere sonde. C'est ce que l'interface affiche."""
    now = time.time() if now is None else now
    state["checked_at"] = now
    state["checked_at_label"] = time.strftime("%H:%M:%S", time.localtime(now))
    if include_docker:
        state["docker_checked_at"] = now
    return now


def run_probes(include_docker=True, now=None):
    """Execute les sondes et horodate le resultat.

    `include_docker` separe la cadence lente (sous-processus vers le demon)
    de la cadence rapide (deux requetes HTTP sur la boucle locale).
    """
    if include_docker:
        check_docker()
        check_docker_images()
    check_ollama()
    check_promptforge()
    return stamp_probe(now=now, include_docker=include_docker)


def probe_due(now=None):
    """Rend `(sonde_rapide_due, sonde_docker_due)` pour l'instant donne."""
    now = time.time() if now is None else now
    fast_due = now - (state["checked_at"] or 0) >= FAST_PROBE_TTL
    slow_due = now - (state["docker_checked_at"] or 0) >= SLOW_PROBE_TTL
    return fast_due, slow_due


def ensure_fresh_status(now=None):
    """Declenche une sonde en tache de fond si l'etat a vieilli.

    Appele par `/api/status`, donc a la cadence du client (3 s). Rend le
    `Thread` lance, ou `None` si rien n'etait du. La reponse HTTP n'attend
    jamais la sonde : elle rend l'instantane courant avec son horodatage, et
    le client obtient la valeur fraiche au sondage suivant. Peremption
    maximale observee par l'utilisateur : environ 5 s.
    """
    with _probe_lock:
        if state["probe_in_progress"]:
            return None
        fast_due, slow_due = probe_due(now)
        if not fast_due and not slow_due:
            return None
        state["probe_in_progress"] = True

    thread = threading.Thread(target=_probe_worker, args=(slow_due,), daemon=True)
    thread.start()
    return thread


def _probe_worker(include_docker):
    try:
        run_probes(include_docker=include_docker)
    finally:
        with _probe_lock:
            state["probe_in_progress"] = False


def status_payload(now=None):
    """L'instantane servi par `/api/status`, augmente de sa fraicheur.

    Un etat affiche sans date est un etat qui ment des qu'il vieillit : le
    payload porte donc toujours l'age de la mesure et le drapeau `stale`.
    """
    now = time.time() if now is None else now
    payload = dict(state)
    payload["logs"] = list(state["logs"])
    checked_at = state.get("checked_at")
    payload["age_seconds"] = None if not checked_at else round(now - checked_at, 1)
    payload["stale"] = checked_at is None or (now - checked_at) > STALE_AFTER
    payload["stale_after_seconds"] = STALE_AFTER
    payload["server_time"] = now
    # D-060 : la table de compose n'existe qu'ici, en Python. Elle est
    # envoyee au client au lieu d'etre recopiee en JavaScript.
    payload["compose_options"] = DOCKER_COMPOSE_OPTIONS
    return payload


def refresh_status():
    """Rafraichit tous les statuts, sans condition de fraicheur.

    Chemin synchrone : demarrage du launcher et bouton « Rafraichir ».
    """
    return run_probes(include_docker=True)


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
            log_change("images", f"Images Docker: {len(images)} trouvee(s)")
        else:
            log_change("images", "Images Docker: Aucune (build necessaire)")
            
    except Exception as e:
        log_change("images", f"Erreur verification images: {e}")
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
    compose_key = state.get("docker_compose_file", "default")
    compose_info = DOCKER_COMPOSE_OPTIONS.get(compose_key, DOCKER_COMPOSE_OPTIONS["default"])
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
    # Le statut a trois etats suit le booleen : on vient de les arreter,
    # ce n'est pas une mesure indeterminee.
    state["promptforge_status"] = STATUS_DOWN
    state["ollama_status"] = STATUS_DOWN
    
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
    # Le statut a trois etats suit le booleen : on vient de les arreter,
    # ce n'est pas une mesure indeterminee.
    state["promptforge_status"] = STATUS_DOWN
    state["ollama_status"] = STATUS_DOWN
    
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
    compose_key = state.get("docker_compose_file", "default")
    compose_info = DOCKER_COMPOSE_OPTIONS.get(compose_key, DOCKER_COMPOSE_OPTIONS["default"])
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
    if state["os"] == "Windows" and compose_key not in ["default", "win-nvidia-native", "win-amd"]:
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
    compose_key = state.get("docker_compose_file", "default")
    compose_info = DOCKER_COMPOSE_OPTIONS.get(compose_key, DOCKER_COMPOSE_OPTIONS["default"])
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
        /* Troisieme etat : ni actif, ni eteint. La sonde n'a pas conclu. */
        .status-unknown { color: #b0b8c4; font-style: italic; }
        /* Fraicheur de la mesure affichee, a cote du titre de la carte. */
        .freshness {
            font-size: 0.75em;
            font-weight: normal;
            color: #8ea0b5;
            margin-left: 10px;
        }
        .freshness-stale { color: #ffa502; }
        .freshness-offline { color: #ff4757; }
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
            <h2>🖥️ Systeme detecte<span class="freshness" id="freshness">Etat jamais verifie</span></h2>
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
                
                // Fraicheur de la mesure affichee
                updateFreshness(data);

                // Docker (trois etats)
                const dockerEl = document.getElementById('docker-value');
                if (dockerEl) {
                    if (!data.docker_installed) {
                        dockerEl.textContent = '❌ Non installe';
                        dockerEl.className = 'value status-error';
                    } else if (data.docker_status === 'up') {
                        dockerEl.textContent = '✅ Actif';
                        dockerEl.className = 'value status-ok';
                    } else if (data.docker_status === 'unknown') {
                        dockerEl.textContent = '❔ Indetermine';
                        dockerEl.className = 'value status-unknown';
                    } else {
                        dockerEl.textContent = '⚠️ Non demarre';
                        dockerEl.className = 'value status-warning';
                    }
                }

                // Ollama (trois etats)
                const ollamaEl = document.getElementById('ollama-value');
                if (ollamaEl) {
                    if (data.os === 'Windows' && !data.ollama_installed) {
                        ollamaEl.textContent = '❌ Non installe';
                        ollamaEl.className = 'value status-error';
                    } else if (data.ollama_status === 'up') {
                        ollamaEl.textContent = '✅ Actif';
                        ollamaEl.className = 'value status-ok';
                    } else if (data.ollama_status === 'unknown') {
                        ollamaEl.textContent = '❔ Indetermine';
                        ollamaEl.className = 'value status-unknown';
                    } else {
                        ollamaEl.textContent = data.os === 'Windows' ? '⚠️ Non demarre' : '⏳ Via Docker';
                        ollamaEl.className = 'value ' + (data.os === 'Windows' ? 'status-warning' : 'status-ok');
                    }
                }

                // PromptForge (trois etats)
                const pfEl = document.getElementById('promptforge-value');
                if (pfEl) {
                    if (data.promptforge_status === 'up') {
                        pfEl.textContent = '✅ Actif';
                        pfEl.className = 'value status-ok';
                    } else if (data.promptforge_status === 'unknown') {
                        pfEl.textContent = '❔ Indetermine';
                        pfEl.className = 'value status-unknown';
                    } else {
                        pfEl.textContent = '❌ Inactif';
                        pfEl.className = 'value status-error';
                    }
                }

                // Alertes d'installation
                updateInstallAlerts(data);
                
                // Bouton accès
                const accessCard = document.getElementById('access-card');
                // Masque seulement sur un « eteint » mesure. Sur un etat
                // indetermine on laisse le lien : au pire il ne repond pas,
                // au mieux il marche - et cacher l'acces au produit sur une
                // absence de mesure est precisement le defaut corrige ici.
                if (accessCard) accessCard.style.display = (data.promptforge_status === 'down') ? 'none' : 'block';
                
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
                    if (data.ollama_status === 'unknown') {
                        modelStatus.textContent = '❔';
                        modelStatus.title = 'Etat d\'Ollama indetermine - la liste des modeles peut etre perimee';
                    } else if (data.ollama_status !== 'up') {
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
                
                // Sur un etat indetermine, les DEUX boutons restent actifs :
                // un etat qu'on ne connait pas ne doit jamais verrouiller
                // l'utilisateur hors de son produit.
                if (btnOllamaStart) btnOllamaStart.disabled = data.ollama_status === 'up' || data.action_in_progress || (data.os === 'Windows' && !data.ollama_installed);
                if (btnOllamaStop) btnOllamaStop.disabled = data.ollama_status === 'down' || data.action_in_progress;
                if (btnPfStart) btnPfStart.disabled = data.promptforge_status === 'up' || data.action_in_progress || !data.docker_installed;
                if (btnPfStop) btnPfStop.disabled = data.promptforge_status === 'down' || data.action_in_progress;
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
        
        // Fraicheur de l'etat affiche.
        //
        // Un etat sans date ment des qu'il vieillit. Trois rendus :
        //   - frais       : horodatage + age en secondes ;
        //   - perime      : au-dela de stale_after_seconds, en orange ;
        //   - hors ligne  : le launcher lui-meme ne repond plus, en rouge.
        // Le dernier cas compte : sans lui, l'age afficherait la meme valeur
        // pour l'eternite pendant que le serveur est mort.
        function updateFreshness(data) {
            const el = document.getElementById('freshness');
            if (!el) return;
            if (!data.checked_at_label) {
                el.textContent = 'Etat jamais verifie';
                el.className = 'freshness freshness-stale';
                return;
            }
            var age = (data.age_seconds === null || data.age_seconds === undefined)
                ? '?' : Math.round(data.age_seconds);
            var suffixe = data.probe_in_progress ? ' - verification en cours' : '';
            el.textContent = 'Etat verifie a ' + data.checked_at_label
                + ' (il y a ' + age + ' s)' + suffixe;
            el.className = data.stale ? 'freshness freshness-stale' : 'freshness';
        }

        function markLauncherOffline(message) {
            const el = document.getElementById('freshness');
            if (!el) return;
            el.textContent = 'Launcher injoignable - etat fige (' + message + ')';
            el.className = 'freshness freshness-offline';
        }

        // D-060 : la table des compose n'existe qu'en Python
        // (DOCKER_COMPOSE_OPTIONS). Elle arrive par /api/status dans
        // data.compose_options. La copie JavaScript qui vivait ici a ete
        // supprimee : elle avait deja divergee de son original.
        function updateComposeSelector(data) {
            try {
                const select = document.getElementById('compose-select');
                const descEl = document.getElementById('compose-description');
                if (!select || !descEl) return;

                const options = data.compose_options || {};
                const available = data.available_compose_files || ['default'];
                const current = data.docker_compose_file || 'default';

                select.innerHTML = available.map(function(key) {
                    var opt = options[key] || { label: key };
                    var selected = key === current ? ' selected' : '';
                    return '<option value="' + key + '"' + selected + '>' + (opt.label || key) + '</option>';
                }).join('');

                // Mettre à jour la description
                const currentOpt = options[current] || {};
                descEl.textContent = currentOpt.description || '';
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
                markLauncherOffline(e.message);
                if (dbg) dbg.innerHTML = 'ERROR: ' + e.message;
            }
        }

        // Cadence du client : 3 s.
        //
        // Le serveur ne resonde pas a chaque appel. `/api/status` declenche
        // une sonde seulement si l'etat a depasse son TTL (2 s pour Ollama et
        // PromptForge, 15 s pour Docker), en tache de fond et une seule a la
        // fois. Un Ollama demarre apres l'ouverture de la page est donc vu
        // en 5 s au pire, sans que l'utilisateur ait rien a cliquer, et sans
        // lancer 200 ms de sous-processus Docker toutes les deux secondes.
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
            # L'etat se recalcule tout seul : le client n'a rien a cliquer.
            # La sonde part en tache de fond, la reponse est immediate et
            # porte son propre horodatage.
            ensure_fresh_status()
            self.send_json(status_payload())
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
                compose_key = data.get("compose_key", "default")
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
            self.send_json(status_payload())
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
