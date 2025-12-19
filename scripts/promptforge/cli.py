#!/usr/bin/env python3
"""
CLI de PromptForge - Interface en ligne de commande.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .core import PromptForge


def get_forge(base_path: Optional[str] = None) -> PromptForge:
    """Crée une instance PromptForge avec le bon chemin de base."""
    if base_path:
        return PromptForge(base_path)
    
    # Cherche un fichier promptforge.db en remontant l'arborescence
    current = Path.cwd()
    while current != current.parent:
        if (current / "promptforge.db").exists():
            return PromptForge(str(current))
        current = current.parent
    
    # Sinon, utilise le répertoire courant
    return PromptForge()


def cmd_init(args):
    """Initialise un nouveau projet."""
    forge = get_forge(args.path)
    success, message = forge.init_project(args.name, args.config)
    
    if success:
        print(f"✓ {message}")
        # Active automatiquement si c'est le premier projet
        if len(forge.list_projects()) == 1:
            forge.use_project(args.name)
            print(f"✓ Projet '{args.name}' activé automatiquement")
    else:
        print(f"✗ {message}", file=sys.stderr)
        sys.exit(1)
    
    forge.close()


def cmd_use(args):
    """Active un projet."""
    forge = get_forge(args.path)
    success, message = forge.use_project(args.name)
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}", file=sys.stderr)
        sys.exit(1)
    
    forge.close()


def cmd_list(args):
    """Liste les projets disponibles."""
    forge = get_forge(args.path)
    projects = forge.list_projects()
    
    if not projects:
        print("Aucun projet configuré.")
        print("Utilisez 'promptforge init <nom> --config <fichier.md>' pour en créer un.")
    else:
        print("Projets disponibles:\n")
        for p in projects:
            marker = "→" if p.is_active else " "
            print(f"  {marker} {p.name}")
            print(f"      Config: {p.config_path}")
            print(f"      Créé: {p.created_at[:10]}")
            print()
    
    forge.close()


def cmd_delete(args):
    """Supprime un projet."""
    forge = get_forge(args.path)
    
    if not args.force:
        confirm = input(f"Supprimer le projet '{args.name}' et son historique ? [y/N] ")
        if confirm.lower() != 'y':
            print("Annulé.")
            forge.close()
            return
    
    success, message = forge.delete_project(args.name)
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}", file=sys.stderr)
        sys.exit(1)
    
    forge.close()


def cmd_format(args):
    """Reformate un prompt."""
    forge = get_forge(args.path)
    
    # Configure le modèle si spécifié
    if args.model:
        forge.configure_ollama(model=args.model)
    
    # Récupère le prompt
    if args.prompt:
        raw_prompt = args.prompt
    else:
        # Mode interactif
        print("Entrez votre prompt (terminez par une ligne vide):")
        lines = []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except EOFError:
                break
        raw_prompt = "\n".join(lines)
    
    if not raw_prompt.strip():
        print("✗ Prompt vide", file=sys.stderr)
        forge.close()
        sys.exit(1)
    
    print("⏳ Reformatage en cours...\n")
    
    success, message, formatted = forge.format_prompt(raw_prompt, args.project)
    
    if success:
        print("=" * 60)
        print("PROMPT REFORMATÉ")
        print("=" * 60)
        print(formatted)
        print("=" * 60)
        print(f"\n✓ Sauvegardé dans: {message}")
        
        # Copie dans le presse-papier si demandé
        if args.copy:
            from .utils import copy_to_clipboard, get_clipboard_tool
            
            if copy_to_clipboard(formatted):
                print("✓ Copié dans le presse-papier")
            else:
                tool = get_clipboard_tool()
                if tool is None:
                    print("⚠ Presse-papier non disponible (installez xclip sur Linux)")
    else:
        print(f"✗ {message}", file=sys.stderr)
        sys.exit(1)
    
    forge.close()


def cmd_history(args):
    """Affiche l'historique des prompts."""
    forge = get_forge(args.path)
    history = forge.get_history(args.project, args.limit)
    
    if not history:
        print("Aucun historique.")
    else:
        print(f"Derniers prompts ({len(history)} résultats):\n")
        for h in history:
            print(f"  [{h.created_at[:16]}] {h.file_path}")
            preview = h.raw_prompt[:60].replace('\n', ' ')
            print(f"      → {preview}...")
            print()
    
    forge.close()


def cmd_status(args):
    """Affiche le statut du système."""
    forge = get_forge(args.path)
    status = forge.check_status()
    
    print("Status PromptForge\n")
    
    # Ollama
    if status["ollama_available"]:
        print(f"  ✓ Ollama: Disponible")
        print(f"      Modèle actif: {status['current_model']}")
        print(f"      Modèles installés: {', '.join(status['ollama_models'][:5])}")
    else:
        print(f"  ✗ Ollama: Non disponible")
        print(f"      Lancez 'ollama serve' pour démarrer")
    
    print()
    
    # Projet
    if status["active_project"]:
        print(f"  ✓ Projet actif: {status['active_project']}")
    else:
        print(f"  ⚠ Aucun projet actif")
    
    print(f"      Total projets: {status['total_projects']}")
    
    print()
    print(f"  📁 DB: {status['db_path']}")
    print(f"  📁 History: {status['history_path']}")
    
    forge.close()


def cmd_reload(args):
    """Recharge la configuration d'un projet depuis son fichier."""
    forge = get_forge(args.path)
    
    project = forge.db.get_project(args.name)
    if not project:
        print(f"✗ Projet '{args.name}' introuvable", file=sys.stderr)
        forge.close()
        sys.exit(1)
    
    success, message = forge.init_project(args.name, project.config_path)
    
    if success:
        print(f"✓ Configuration rechargée pour '{args.name}'")
    else:
        print(f"✗ {message}", file=sys.stderr)
        sys.exit(1)
    
    forge.close()


def cmd_web(args):
    """Lance l'interface web."""
    try:
        from .web import launch_web
    except ImportError:
        print("✗ Gradio n'est pas installé.", file=sys.stderr)
        print("  Installez-le avec: pip install promptforge[web]", file=sys.stderr)
        sys.exit(1)
    
    print(f"🚀 Lancement de l'interface web sur http://{args.host}:{args.port}")
    if args.share:
        print("📡 Mode partage activé (lien public Gradio)")
    
    launch_web(host=args.host, port=args.port, share=args.share)


def cmd_template(args):
    """Affiche le template de prompt pour générer une config projet."""
    template_path = Path(__file__).parent.parent / "templates" / "PROJECT_GENERATOR_PROMPT.md"
    
    if template_path.exists():
        content = template_path.read_text(encoding="utf-8")
        print(content)
    else:
        # Fallback si le fichier n'existe pas
        print("""
# 🎯 Génère ta configuration projet

Copie ce prompt et envoie-le à Claude/ChatGPT :

---

Je veux créer un fichier de configuration pour mon projet.
Pose-moi ces questions une par une :

1. Nom du projet ?
2. Description (2-3 phrases) ?
3. Stack technique (langages, frameworks, DB) ?
4. Structure des dossiers ?
5. Conventions de code ?
6. Tests utilisés ?
7. Patterns/architecture ?
8. Règles métier importantes ?
9. Contraintes (perf, sécu) ?

Puis génère un fichier Markdown structuré avec toutes ces infos.

---

Sauvegarde le résultat dans un fichier .md et utilise:
  promptforge init mon-projet --config ./mon-projet.md
""")
    
    if args.output:
        output_path = Path(args.output)
        if template_path.exists():
            output_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\n✓ Template sauvegardé dans: {args.output}")


def main():
    parser = argparse.ArgumentParser(
        prog="promptforge",
        description="Reformateur intelligent de prompts avec contexte projet"
    )
    parser.add_argument(
        "--path", "-p",
        help="Chemin vers le répertoire PromptForge",
        default=None
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    
    # init
    init_parser = subparsers.add_parser("init", help="Initialiser un nouveau projet")
    init_parser.add_argument("name", help="Nom du projet")
    init_parser.add_argument("--config", "-c", required=True, help="Fichier .md de configuration")
    init_parser.set_defaults(func=cmd_init)
    
    # use
    use_parser = subparsers.add_parser("use", help="Activer un projet")
    use_parser.add_argument("name", help="Nom du projet à activer")
    use_parser.set_defaults(func=cmd_use)
    
    # list
    list_parser = subparsers.add_parser("list", help="Lister les projets")
    list_parser.set_defaults(func=cmd_list)
    
    # delete
    delete_parser = subparsers.add_parser("delete", help="Supprimer un projet")
    delete_parser.add_argument("name", help="Nom du projet à supprimer")
    delete_parser.add_argument("--force", "-f", action="store_true", help="Sans confirmation")
    delete_parser.set_defaults(func=cmd_delete)
    
    # format (commande principale)
    format_parser = subparsers.add_parser("format", help="Reformater un prompt")
    format_parser.add_argument("prompt", nargs="?", help="Prompt à reformater (interactif si omis)")
    format_parser.add_argument("--project", help="Projet à utiliser (défaut: actif)")
    format_parser.add_argument("--model", "-m", help="Modèle Ollama à utiliser")
    format_parser.add_argument("--copy", "-c", action="store_true", help="Copier dans le presse-papier")
    format_parser.set_defaults(func=cmd_format)
    
    # history
    history_parser = subparsers.add_parser("history", help="Voir l'historique")
    history_parser.add_argument("--project", help="Filtrer par projet")
    history_parser.add_argument("--limit", "-n", type=int, default=10, help="Nombre de résultats")
    history_parser.set_defaults(func=cmd_history)
    
    # status
    status_parser = subparsers.add_parser("status", help="Statut du système")
    status_parser.set_defaults(func=cmd_status)
    
    # reload
    reload_parser = subparsers.add_parser("reload", help="Recharger la config d'un projet")
    reload_parser.add_argument("name", help="Nom du projet")
    reload_parser.set_defaults(func=cmd_reload)
    
    # web
    web_parser = subparsers.add_parser("web", help="Lancer l'interface web")
    web_parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute (défaut: 127.0.0.1)")
    web_parser.add_argument("--port", "-p", type=int, default=7860, help="Port (défaut: 7860)")
    web_parser.add_argument("--share", "-s", action="store_true", help="Créer un lien public Gradio")
    web_parser.set_defaults(func=cmd_web)
    
    # template
    template_parser = subparsers.add_parser("template", help="Afficher le template de génération de config")
    template_parser.add_argument("--output", "-o", help="Sauvegarder dans un fichier")
    template_parser.set_defaults(func=cmd_template)
    
    # Parsing
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()
