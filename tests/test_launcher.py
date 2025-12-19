"""
Tests pour le launcher PromptForge.
Vérifie que toutes les configurations Docker sont correctes.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDockerComposeFiles:
    """Tests pour les fichiers docker-compose."""

    def test_all_compose_files_exist(self):
        """Vérifie que tous les fichiers docker-compose existent."""
        base_dir = Path(__file__).parent.parent
        
        expected_files = [
            'docker-compose.yml',           # NVIDIA
            'docker-compose.cpu.yml',       # CPU
            'docker-compose.amd.yml',       # Linux AMD
            'docker-compose.amd-max.yml',   # Linux AMD MAX
            'docker-compose.win-nvidia.yml', # Windows NVIDIA
            'docker-compose.win-amd.yml',   # Windows AMD
        ]
        
        for filename in expected_files:
            filepath = base_dir / filename
            assert filepath.exists(), f"Fichier manquant: {filename}"

    def test_compose_files_valid_yaml(self):
        """Vérifie que les fichiers docker-compose sont du YAML valide."""
        import yaml
        
        base_dir = Path(__file__).parent.parent
        compose_files = list(base_dir.glob('docker-compose*.yml'))
        
        for filepath in compose_files:
            try:
                with open(filepath) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"YAML invalide dans {filepath.name}: {e}")

    def test_compose_files_have_promptforge_service(self):
        """Vérifie que les fichiers docker-compose ont le service promptforge."""
        import yaml
        
        base_dir = Path(__file__).parent.parent
        compose_files = list(base_dir.glob('docker-compose*.yml'))
        
        for filepath in compose_files:
            with open(filepath) as f:
                config = yaml.safe_load(f)
            
            services = config.get('services', {})
            # Doit avoir au moins promptforge ou promptforge-web
            has_pf = 'promptforge' in services or 'promptforge-web' in services
            assert has_pf, f"{filepath.name} n'a pas de service promptforge"


class TestLauncherConfig:
    """Tests pour la configuration du launcher."""

    def test_launcher_file_exists(self):
        """Vérifie que launcher.py existe."""
        launcher = Path(__file__).parent.parent / 'launcher.py'
        assert launcher.exists(), "launcher.py n'existe pas"

    def test_launcher_has_docker_options(self):
        """Vérifie que le launcher a toutes les options Docker."""
        launcher = Path(__file__).parent.parent / 'launcher.py'
        content = launcher.read_text()
        
        expected_options = [
            'nvidia',
            'win-nvidia-native',
            'win-amd',
            'linux-amd',
            'cpu',
        ]
        
        for option in expected_options:
            assert f'"{option}"' in content, f"Option {option} manquante dans launcher"

    def test_launcher_has_recommended_models(self):
        """Vérifie que le launcher a les modèles recommandés."""
        launcher = Path(__file__).parent.parent / 'launcher.py'
        content = launcher.read_text()
        
        # Doit avoir des modèles recommandés pour chaque type de GPU
        assert 'qwen3' in content.lower() or 'phi4' in content.lower()
        assert 'RECOMMENDED_MODELS' in content


class TestDockerfiles:
    """Tests pour les Dockerfiles."""

    def test_dockerfile_exists(self):
        """Vérifie que Dockerfile existe."""
        dockerfile = Path(__file__).parent.parent / 'Dockerfile'
        assert dockerfile.exists(), "Dockerfile n'existe pas"

    def test_dockerfile_web_exists(self):
        """Vérifie que Dockerfile.web existe."""
        dockerfile = Path(__file__).parent.parent / 'Dockerfile.web'
        assert dockerfile.exists(), "Dockerfile.web n'existe pas"

    def test_dockerfile_web_copies_templates(self):
        """Vérifie que Dockerfile.web copie les templates."""
        dockerfile = Path(__file__).parent.parent / 'Dockerfile.web'
        content = dockerfile.read_text()
        
        assert 'COPY templates/' in content, "Dockerfile.web ne copie pas les templates"


class TestLauncherScripts:
    """Tests pour les scripts de lancement."""

    def test_launcher_bat_exists(self):
        """Vérifie que Launcher.bat existe (Windows)."""
        script = Path(__file__).parent.parent / 'Launcher.bat'
        assert script.exists(), "Launcher.bat n'existe pas"

    def test_launcher_sh_exists(self):
        """Vérifie que launcher.sh existe (Linux/Mac)."""
        script = Path(__file__).parent.parent / 'launcher.sh'
        assert script.exists(), "launcher.sh n'existe pas"

    def test_launcher_ps1_exists(self):
        """Vérifie que launcher.ps1 existe (PowerShell)."""
        script = Path(__file__).parent.parent / 'launcher.ps1'
        assert script.exists(), "launcher.ps1 n'existe pas"


class TestStartScripts:
    """Tests pour les scripts de démarrage spécifiques GPU."""

    def test_start_nvidia_exists(self):
        """Vérifie que start-nvidia.ps1 existe."""
        script = Path(__file__).parent.parent / 'start-nvidia.ps1'
        assert script.exists(), "start-nvidia.ps1 n'existe pas"

    def test_start_amd_exists(self):
        """Vérifie que start-amd.ps1 existe."""
        script = Path(__file__).parent.parent / 'start-amd.ps1'
        assert script.exists(), "start-amd.ps1 n'existe pas"

    def test_setup_amd_windows_exists(self):
        """Vérifie que setup-amd-windows.ps1 existe."""
        script = Path(__file__).parent.parent / 'setup-amd-windows.ps1'
        assert script.exists(), "setup-amd-windows.ps1 n'existe pas"


class TestLauncherStateFixes:
    """Tests pour vérifier que l'état est correctement mis à jour."""

    def test_rebuild_updates_state(self):
        """Vérifie que rebuild_docker_images met à jour l'état."""
        launcher = Path(__file__).parent.parent / 'launcher.py'
        content = launcher.read_text()
        
        # Chercher la mise à jour de l'état dans rebuild_docker_images
        # Il doit y avoir state["promptforge_running"] = False après le docker down
        import re
        rebuild_match = re.search(
            r'def rebuild_docker_images.*?(?=def \w+|\Z)', 
            content, 
            re.DOTALL
        )
        assert rebuild_match, "Fonction rebuild_docker_images non trouvée"
        
        rebuild_code = rebuild_match.group()
        assert 'state["promptforge_running"] = False' in rebuild_code, \
            "rebuild_docker_images ne met pas à jour promptforge_running"

    def test_clean_docker_updates_state(self):
        """Vérifie que clean_docker met à jour l'état."""
        launcher = Path(__file__).parent.parent / 'launcher.py'
        content = launcher.read_text()
        
        import re
        clean_match = re.search(
            r'def clean_docker.*?(?=def \w+|\Z)', 
            content, 
            re.DOTALL
        )
        assert clean_match, "Fonction clean_docker non trouvée"
        
        clean_code = clean_match.group()
        assert 'state["promptforge_running"] = False' in clean_code, \
            "clean_docker ne met pas à jour promptforge_running"
