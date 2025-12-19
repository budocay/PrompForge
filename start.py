#!/usr/bin/env python3
"""
PromptForge - Launcher Natif (sans Docker)

Usage:
    python start.py          # Lance l'interface web
    python start.py --install # Installe les dépendances d'abord
    python start.py --check   # Vérifie l'installation
"""

import subprocess
import sys
import os
from pathlib import Path

# Couleurs pour le terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header():
    """Affiche le header."""
    print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║           ✨ PromptForge - Mode Natif                    ║
║      Reformateur intelligent de prompts                   ║
╚══════════════════════════════════════════════════════════╝{Colors.END}
""")

def check_python_version():
    """Vérifie la version de Python."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"{Colors.RED}❌ Python 3.10+ requis (actuel: {version.major}.{version.minor}){Colors.END}")
        return False
    print(f"{Colors.GREEN}✅ Python {version.major}.{version.minor}.{version.micro}{Colors.END}")
    return True

def check_ollama():
    """Vérifie si Ollama est installé et en cours d'exécution."""
    # Vérifier si Ollama est installé
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Ollama installé{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️  Ollama non trouvé{Colors.END}")
            return False
    except FileNotFoundError:
        print(f"{Colors.YELLOW}⚠️  Ollama non installé{Colors.END}")
        print(f"   → Télécharge-le sur: {Colors.BLUE}https://ollama.ai{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️  Erreur Ollama: {e}{Colors.END}")
        return False
    
    # Vérifier si Ollama est en cours d'exécution
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                print(f"{Colors.GREEN}✅ Ollama en cours d'exécution{Colors.END}")
                return True
    except Exception:
        print(f"{Colors.YELLOW}⚠️  Ollama n'est pas démarré{Colors.END}")
        print(f"   → Lance: {Colors.BOLD}ollama serve{Colors.END}")
        return False
    
    return True

def check_gradio():
    """Vérifie si Gradio est installé."""
    try:
        import gradio
        print(f"{Colors.GREEN}✅ Gradio {gradio.__version__}{Colors.END}")
        return True
    except ImportError:
        print(f"{Colors.YELLOW}⚠️  Gradio non installé{Colors.END}")
        return False

def check_promptforge():
    """Vérifie si PromptForge est installé."""
    try:
        import promptforge
        print(f"{Colors.GREEN}✅ PromptForge installé{Colors.END}")
        return True
    except ImportError:
        print(f"{Colors.YELLOW}⚠️  PromptForge non installé{Colors.END}")
        return False

def install_dependencies():
    """Installe les dépendances."""
    print(f"\n{Colors.BOLD}📦 Installation des dépendances...{Colors.END}\n")
    
    # S'assurer qu'on est dans le bon dossier
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Installer le package en mode éditable avec les extras web
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[web]", "--quiet"],
            check=True
        )
        print(f"{Colors.GREEN}✅ Dépendances installées avec succès !{Colors.END}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Erreur d'installation: {e}{Colors.END}")
        return False

def check_all():
    """Vérifie toutes les dépendances."""
    print(f"{Colors.BOLD}🔍 Vérification de l'environnement...{Colors.END}\n")
    
    checks = {
        "Python": check_python_version(),
        "PromptForge": check_promptforge(),
        "Gradio": check_gradio(),
        "Ollama": check_ollama(),
    }
    
    print()
    all_ok = all(checks.values())
    
    if all_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ Tout est prêt !{Colors.END}")
    else:
        missing = [k for k, v in checks.items() if not v]
        print(f"{Colors.YELLOW}⚠️  Manquant: {', '.join(missing)}{Colors.END}")
        
        if "PromptForge" in missing or "Gradio" in missing:
            print(f"\n   → Lance: {Colors.BOLD}python start.py --install{Colors.END}")
        if "Ollama" in missing:
            print(f"   → Télécharge Ollama: {Colors.BLUE}https://ollama.ai{Colors.END}")
    
    return all_ok

def start_web():
    """Lance l'interface web."""
    print(f"\n{Colors.BOLD}🚀 Lancement de PromptForge...{Colors.END}\n")
    
    # S'assurer qu'on est dans le bon dossier
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Définir le chemin des données
    data_path = script_dir / "data"
    data_path.mkdir(exist_ok=True)
    (data_path / "projects").mkdir(exist_ok=True)
    (data_path / "history").mkdir(exist_ok=True)
    
    try:
        # Importer et lancer
        from promptforge.web import launch_web, set_base_path
        
        set_base_path(str(data_path))
        
        print(f"📂 Données: {data_path}")
        print(f"🌐 Interface: {Colors.BLUE}http://localhost:7860{Colors.END}")
        print(f"\n{Colors.YELLOW}Appuie sur Ctrl+C pour arrêter{Colors.END}\n")
        
        launch_web(host="127.0.0.1", port=7860, share=False, base_path=str(data_path))
        
    except ImportError as e:
        print(f"{Colors.RED}❌ Erreur d'import: {e}{Colors.END}")
        print(f"   → Lance d'abord: {Colors.BOLD}python start.py --install{Colors.END}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 Arrêt de PromptForge{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}❌ Erreur: {e}{Colors.END}")
        sys.exit(1)

def main():
    """Point d'entrée principal."""
    print_header()
    
    # Parser les arguments
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)
    
    if "--check" in args:
        check_all()
        sys.exit(0)
    
    if "--install" in args:
        if install_dependencies():
            print(f"\n{Colors.GREEN}✅ Installation terminée !{Colors.END}")
            print(f"   → Lance maintenant: {Colors.BOLD}python start.py{Colors.END}")
        sys.exit(0)
    
    # Vérification rapide et lancement
    if not check_python_version():
        sys.exit(1)
    
    if not check_promptforge() or not check_gradio():
        print(f"\n{Colors.YELLOW}📦 Installation automatique des dépendances...{Colors.END}")
        if not install_dependencies():
            sys.exit(1)
    
    # Vérifier Ollama (warning seulement)
    check_ollama()
    
    # Lancer l'interface
    start_web()

if __name__ == "__main__":
    main()
