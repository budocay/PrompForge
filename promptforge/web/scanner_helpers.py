"""
Scanner helper functions for PromptForge web interface.
Handles project scanning and configuration generation from the UI.
"""

import gradio as gr
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from ..scanner import ProjectScanner, ScanResult
from .ollama_helpers import get_forge
from .project_helpers import get_projects_list, normalize_name


def scan_directory_for_ui(
    path_str: str,
    project_name: str,
    description: Optional[str] = None,
    depth: int = 3
) -> tuple[str, str, str]:
    """
    Scan a directory and return results for UI display.

    Args:
        path_str: Path to the directory to scan
        project_name: Name for the project
        description: Optional description override
        depth: Scan depth

    Returns:
        tuple: (status_message, scan_summary, generated_config)
    """
    if not path_str.strip():
        return "❌ Entrez un chemin de répertoire", "", ""

    if not project_name.strip():
        return "❌ Entrez un nom de projet", "", ""

    path = Path(path_str).expanduser()

    if not path.exists():
        return f"❌ Le chemin '{path}' n'existe pas", "", ""

    if not path.is_dir():
        return f"❌ '{path}' n'est pas un répertoire", "", ""

    try:
        scanner = ProjectScanner(max_depth=depth)
        result = scanner.scan(path)

        # Generate summary
        summary = format_scan_summary(result)

        # Generate config
        config = scanner.generate_config(
            result,
            project_name.strip(),
            description.strip() if description else None
        )

        status = f"✅ Scan terminé: {result.files_scanned} fichiers en {result.scan_duration_ms}ms"

        return status, summary, config

    except Exception as e:
        return f"❌ Erreur lors du scan: {e}", "", ""


def format_scan_summary(result: ScanResult) -> str:
    """Format scan results as Markdown summary."""
    lines = ["## 📊 Résumé du Scan\n"]

    # Languages
    if result.languages:
        lines.append("### Langages détectés")
        lines.append("")
        for lang in result.languages[:5]:
            version_str = f" ({lang.version})" if lang.version else ""
            lines.append(
                f"- **{lang.name}**{version_str}: {lang.file_count} fichiers ({lang.percentage}%)"
            )
        lines.append("")

    # Frameworks
    if result.frameworks:
        lines.append("### Frameworks et Librairies")
        lines.append("")
        by_category: dict[str, list] = {}
        for fw in result.frameworks:
            by_category.setdefault(fw.category, []).append(fw)

        category_labels = {
            "backend": "🔧 Backend",
            "frontend": "🎨 Frontend",
            "orm": "🗄️ ORM/DB",
            "ui": "💅 UI/Styling",
            "state": "📦 State",
            "mobile": "📱 Mobile",
            "other": "📌 Autres",
        }

        for cat, fws in by_category.items():
            label = category_labels.get(cat, f"📌 {cat.title()}")
            fw_names = ", ".join(f"**{f.name}**" for f in fws)
            lines.append(f"- {label}: {fw_names}")
        lines.append("")

    # Databases
    if result.databases:
        lines.append("### Base de données")
        lines.append("")
        for db in result.databases:
            orm_str = f" (ORM: {db.orm})" if db.orm else ""
            lines.append(f"- **{db.name}**{orm_str} - détecté dans {db.detected_from}")
        lines.append("")

    # Tests
    if result.tests:
        lines.append("### Tests")
        lines.append("")
        for test in result.tests:
            dirs_str = f" ({', '.join(test.test_dirs)})" if test.test_dirs else ""
            lines.append(f"- **{test.framework}**{dirs_str}")
        lines.append("")

    # Conventions
    if result.conventions:
        conv = result.conventions
        if conv.formatter or conv.linter:
            lines.append("### Conventions")
            lines.append("")
            if conv.formatter:
                lines.append(f"- Formatter: **{conv.formatter}**")
            if conv.linter:
                lines.append(f"- Linter: **{conv.linter}**")
            if conv.typechecker:
                lines.append(f"- Type checker: **{conv.typechecker}**")
            if conv.line_length:
                lines.append(f"- Longueur ligne: {conv.line_length}")
            lines.append("")

    # Docker
    if result.docker and (result.docker.has_dockerfile or result.docker.has_compose):
        lines.append("### 🐳 Docker")
        lines.append("")
        if result.docker.has_dockerfile:
            lines.append("- ✅ Dockerfile présent")
        if result.docker.has_compose:
            services_str = ", ".join(result.docker.services[:5]) if result.docker.services else ""
            lines.append(f"- ✅ Docker Compose: {result.docker.compose_file}")
            if services_str:
                lines.append(f"- Services: {services_str}")
        lines.append("")

    # CI/CD
    if result.cicd and result.cicd.provider:
        lines.append("### 🔄 CI/CD")
        lines.append("")
        lines.append(f"- Provider: **{result.cicd.provider}**")
        if result.cicd.workflows:
            lines.append(f"- Workflows: {', '.join(result.cicd.workflows[:5])}")
        lines.append("")

    # Structure info
    if result.structure:
        lines.append("### 📁 Structure")
        lines.append("")
        lines.append(f"- Répertoires: {result.structure.total_dirs}")
        lines.append(f"- Fichiers: {result.structure.total_files}")
        if result.structure.directories:
            top_dirs = ", ".join(result.structure.directories[:8])
            lines.append(f"- Dossiers racine: {top_dirs}")
        lines.append("")

    # Errors
    if result.errors:
        lines.append("### ⚠️ Avertissements")
        lines.append("")
        for error in result.errors[:3]:
            lines.append(f"- {error}")
        lines.append("")

    return "\n".join(lines)


def save_scanned_config(
    project_name: str,
    config_content: str,
    auto_activate: bool = True
) -> tuple[str, gr.update, gr.update]:
    """
    Save the generated config and register as project.

    Args:
        project_name: Name for the project
        config_content: Generated Markdown configuration
        auto_activate: Whether to auto-activate the project

    Returns:
        tuple: (status_message, projects_dropdown_update, scan_projects_dropdown_update)
    """
    if not project_name.strip():
        return "❌ Nom de projet requis", gr.update(), gr.update()

    if not config_content.strip():
        return "❌ Configuration vide - scannez d'abord", gr.update(), gr.update()

    forge = get_forge()
    normalized_name = normalize_name(project_name.strip())

    # Save config file
    config_path = forge.projects_path / f"{normalized_name}.md"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content, encoding="utf-8")

    # Register project
    success, msg = forge.init_project(normalized_name, str(config_path))

    if success and auto_activate:
        forge.use_project(normalized_name)

    # Get updated project list
    projects = get_projects_list()

    if success:
        status = f"✅ Projet '{normalized_name}' créé et activé"
    else:
        status = f"❌ Erreur: {msg}"

    return (
        status,
        gr.update(choices=projects, value=normalized_name if success else None),
        gr.update(choices=projects)
    )


def get_default_scan_path() -> str:
    """Get a sensible default path for scanning."""
    # Check if /hostfs exists (Docker with mounted volume)
    hostfs = Path("/hostfs")
    if hostfs.exists() and hostfs.is_dir():
        return "/hostfs"
    return str(Path.cwd())


def scan_uploaded_zip(
    zip_file,
    project_name: str,
    description: Optional[str] = None,
    depth: int = 3
) -> tuple[str, str, str]:
    """
    Scan an uploaded ZIP file containing a project.

    Args:
        zip_file: Uploaded file object from Gradio
        project_name: Name for the project
        description: Optional description override
        depth: Scan depth

    Returns:
        tuple: (status_message, scan_summary, generated_config)
    """
    if zip_file is None:
        return "❌ Uploadez un fichier ZIP de votre projet", "", ""

    if not project_name.strip():
        return "❌ Entrez un nom de projet", "", ""

    # Get the file path from Gradio upload
    zip_path = Path(zip_file.name if hasattr(zip_file, 'name') else zip_file)

    if not zip_path.exists():
        return "❌ Fichier non trouvé", "", ""

    if not zipfile.is_zipfile(zip_path):
        return "❌ Le fichier n'est pas un ZIP valide", "", ""

    temp_dir = None
    try:
        # Create temp directory for extraction
        temp_dir = tempfile.mkdtemp(prefix="promptforge_scan_")
        extract_path = Path(temp_dir) / "project"

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_path)

        # Check if ZIP contains a single root folder
        contents = list(extract_path.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            # Use the single folder as project root
            project_path = contents[0]
        else:
            # Use extract_path directly
            project_path = extract_path

        # Scan the extracted project
        scanner = ProjectScanner(max_depth=depth)
        result = scanner.scan(project_path)

        # Generate summary
        summary = format_scan_summary(result)

        # Generate config
        config = scanner.generate_config(
            result,
            project_name.strip(),
            description.strip() if description else None
        )

        status = f"✅ Scan terminé: {result.files_scanned} fichiers en {result.scan_duration_ms}ms"

        return status, summary, config

    except zipfile.BadZipFile:
        return "❌ Fichier ZIP corrompu ou invalide", "", ""
    except Exception as e:
        return f"❌ Erreur lors du scan: {e}", "", ""
    finally:
        # Cleanup temp directory
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
