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


class TestEntryPoints:
    """Points d'entree du produit, apres le nettoyage DEC-011.

    Treize scripts de lancement redondants ont ete supprimes : ils
    dupliquaient, en `.bat`, `.ps1` et `.sh`, ce que deux entrees
    multiplateformes font deja. Ces tests verrouillent le fait qu'ils ne
    reviennent pas, et que les deux entrees restantes existent.
    """

    RETIRES = [
        "Launcher.bat", "Start.bat", "launcher.ps1", "launcher.sh", "start.sh",
        "run-web.bat", "run-web.ps1", "run-web.sh", "run.ps1",
        "start-amd.ps1", "start-nvidia.ps1", "update.ps1", "update.sh",
    ]

    def test_cross_platform_entry_points_exist(self):
        """Les deux entrees multiplateformes sont presentes."""
        base_dir = Path(__file__).parent.parent
        for name in ("launcher.py", "start.py"):
            assert (base_dir / name).exists(), f"{name} n'existe pas"

    def test_no_platform_specific_launcher_returns(self):
        """Aucun script de lancement specifique a une plateforme a la racine.

        Le produit doit rester multiplateforme et pilote par Docker : un
        `.bat` ou un `.ps1` de lancement a la racine signale une regression
        vers un chemin Windows dedie.
        """
        base_dir = Path(__file__).parent.parent
        revenus = [name for name in self.RETIRES if (base_dir / name).exists()]
        assert not revenus, f"scripts de lancement redondants revenus : {revenus}"

    def test_makefile_is_the_documented_update_path(self):
        """`update.sh` et `update.ps1` sont remplaces par une cible Makefile."""
        makefile = (Path(__file__).parent.parent / "Makefile").read_text()
        assert "update:" in makefile, "la cible `make update` a disparu"


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
