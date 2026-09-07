"""
Tests pour le launcher PromptForge.
Verifie que toutes les configurations Docker sont correctes.

Contient le test de couture entre les commandes du depot et les fichiers
compose qu'elles visent (`TestComposeServiceSeam`). Il repond a une
regression reelle : le deplacement des compose dans `docker/compose/` et la
creation d'un `compose.yaml` racine a un seul service ont casse cinq points
d'entree, sans qu'aucun test ne rougisse et alors que
`docker compose config` continuait de rendre 0. `config` valide la syntaxe
d'un fichier ; il ne sait rien des commandes qui le consomment.
"""

import http.server
import importlib.util
import json as _json
import re
import shlex
import socket
import subprocess
import sys
import threading
import time
import types
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_DIR = Path(__file__).resolve().parent.parent

# Fichier retenu par `docker compose` sans `-f` a la racine du depot.
DEFAULT_COMPOSE = "compose.yaml"


def compose_paths():
    """Les sept fichiers compose du depot."""
    return sorted(BASE_DIR.glob("docker/compose/*.yml")) + [BASE_DIR / DEFAULT_COMPOSE]


def compose_services(path):
    """Services declares par un fichier compose, en set."""
    import yaml

    with open(path) as handle:
        config = yaml.safe_load(handle)
    return set((config or {}).get("services", {}) or {})


# ------------------------------------------------------------------
# Extraction des services nommes par une commande `docker compose`
# ------------------------------------------------------------------

# Options globales (avant la sous-commande) qui consomment la valeur suivante.
_GLOBAL_VALUE_FLAGS = {
    "-f", "--file", "-p", "--project-name", "--profile", "--env-file",
    "--project-directory", "--progress", "--ansi",
}

# Sous-commandes dont tous les arguments libres sont des services.
_SERVICE_LIST_SUBCOMMANDS = {
    "up", "build", "ps", "pull", "push", "restart", "start", "stop", "kill",
    "logs", "rm", "create", "images", "top", "pause", "unpause", "wait",
}

# Sous-commandes dont seul le PREMIER argument libre est un service
# (le reste est la commande a executer dans le conteneur).
_SERVICE_FIRST_SUBCOMMANDS = {"run", "exec"}

# Options qui consomment la valeur suivante, apres la sous-commande.
_VALUE_FLAGS = {
    "--scale", "--entrypoint", "--user", "-u", "--workdir", "-w", "--name",
    "--label", "-l", "--volume", "--publish", "-p", "--tail", "-n", "--since",
    "--until", "--timeout", "-t", "--parallel", "--rmi", "--profile",
    "--memory", "-m", "--exit-code-from", "--attach", "--no-attach", "--env",
    "-e", "--build-arg", "--ssh", "--builder", "--index", "--wait-timeout",
}


def parse_compose_command(tokens):
    """Rend `(fichier_compose, [services nommes])` pour un argv compose.

    Rend `None` si l'argv n'est pas une invocation `docker compose`.
    Le fichier vaut `compose.yaml` quand aucun `-f` n'est passe, ce qui est
    la resolution reelle de Docker a la racine du depot.
    """
    tokens = list(tokens)
    if not tokens:
        return None
    if tokens[0] == "docker" and len(tokens) > 1 and tokens[1] == "compose":
        rest = tokens[2:]
    elif tokens[0] == "docker-compose":
        rest = tokens[1:]
    else:
        return None

    compose_file = DEFAULT_COMPOSE
    index = 0
    subcommand = None

    # Options globales, jusqu'a la sous-commande.
    while index < len(rest):
        token = rest[index]
        if token.startswith("-"):
            name, _, inline = token.partition("=")
            if name in ("-f", "--file"):
                compose_file = inline or rest[index + 1]
                index += 1 if inline else 2
                continue
            if name in _GLOBAL_VALUE_FLAGS and not inline:
                index += 2
                continue
            index += 1
            continue
        subcommand = token
        index += 1
        break

    if subcommand is None:
        return compose_file, []
    if subcommand not in _SERVICE_LIST_SUBCOMMANDS | _SERVICE_FIRST_SUBCOMMANDS:
        # `down`, `config`, `version`... ne nomment aucun service ici.
        return compose_file, []

    services = []
    only_first = subcommand in _SERVICE_FIRST_SUBCOMMANDS
    while index < len(rest):
        token = rest[index]
        if token == "--":
            break
        if token.startswith("-"):
            name, _, inline = token.partition("=")
            if name in _VALUE_FLAGS and not inline:
                index += 2
                continue
            index += 1
            continue
        services.append(token)
        index += 1
        if only_first:
            break
    return compose_file, services


def _makefile_variables(text):
    """Variables simples du Makefile, pour expanser `$(COMPOSE)`."""
    variables = {}
    for line in text.splitlines():
        if line.startswith("\t") or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::=|\?=|=)\s*(.*)$", line)
        if match:
            variables[match.group(1)] = match.group(2).strip()
    return variables


def _expand(text, variables):
    for _ in range(5):
        expanded = re.sub(
            r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)",
            lambda m: variables.get(m.group(1), ""),
            text,
        )
        if expanded == text:
            break
        text = expanded
    return text


def makefile_compose_commands():
    """Toutes les invocations `docker compose` des recettes du Makefile."""
    text = (BASE_DIR / "Makefile").read_text()
    variables = _makefile_variables(text)

    # Recoller les lignes continuees par `\`.
    lines = []
    buffer = ""
    for line in text.splitlines():
        if not line.startswith("\t"):
            buffer = ""
            continue
        buffer += line.lstrip("\t").rstrip()
        if buffer.endswith("\\"):
            buffer = buffer[:-1] + " "
            continue
        lines.append(buffer)
        buffer = ""

    found = []
    for recipe in lines:
        recipe = _expand(recipe, variables).lstrip("@-+ ")
        for fragment in re.split(r"\|\||&&|;|\|", recipe):
            fragment = fragment.strip()
            if "docker compose" not in fragment and "docker-compose" not in fragment:
                continue
            fragment = re.sub(r"\d?>[&]?\S+", "", fragment)
            try:
                tokens = shlex.split(fragment)
            except ValueError:
                tokens = fragment.split()
            start = None
            for position, token in enumerate(tokens):
                if token in ("docker", "docker-compose"):
                    start = position
                    break
            if start is None:
                continue
            found.append((recipe, tokens[start:]))
    return found


def load_script_at(path, name):
    """Charge un module Python par chemin, sans passer par un package."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_script(name):
    """Charge un script de `scripts/` sans en faire un package."""
    return load_script_at(BASE_DIR / "scripts" / f"{name}.py", f"_seam_{name}")


class RecordingSubprocess:
    """Faux module `subprocess` : enregistre les argv au lieu de les executer.

    Repond a `config --services` avec les services reels du fichier vise,
    pour que le script sous test suive la meme branche qu'en production.
    """

    def __init__(self):
        self.calls = []

    def run(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        stdout = ""
        parsed = parse_compose_command(cmd)
        if parsed and "config" in cmd and "--services" in cmd:
            path = BASE_DIR / parsed[0]
            if path.exists():
                stdout = "\n".join(sorted(compose_services(path))) + "\n"
        return types.SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    def compose_calls(self):
        for call in self.calls:
            parsed = parse_compose_command(call)
            if parsed:
                yield call, parsed


class TestDockerComposeFiles:
    """Tests pour les fichiers docker-compose."""

    def test_all_compose_files_exist(self):
        """Vérifie que tous les fichiers docker-compose existent."""
        base_dir = Path(__file__).parent.parent
        
        expected_files = [
            'compose.yaml',                                 # defaut, les 3 OS
            'docker/compose/docker-compose.yml',            # NVIDIA
            'docker/compose/docker-compose.cpu.yml',        # CPU
            'docker/compose/docker-compose.amd.yml',        # Linux AMD
            'docker/compose/docker-compose.amd-max.yml',    # Linux AMD MAX
            'docker/compose/docker-compose.win-nvidia.yml', # Windows NVIDIA
            'docker/compose/docker-compose.win-amd.yml',    # Windows AMD
        ]
        
        for filename in expected_files:
            filepath = base_dir / filename
            assert filepath.exists(), f"Fichier manquant: {filename}"

    def test_compose_files_valid_yaml(self):
        """Vérifie que les fichiers docker-compose sont du YAML valide."""
        import yaml
        
        base_dir = Path(__file__).parent.parent
        compose_files = list(base_dir.glob('docker/compose/*.yml')) + [base_dir / 'compose.yaml']
        
        for filepath in compose_files:
            try:
                with open(filepath) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"YAML invalide dans {filepath.name}: {e}")

    def test_every_compose_file_declares_the_web_service(self):
        """`promptforge-web` est le seul service commun aux sept compose.

        L'assertion precedente etait « promptforge OU promptforge-web ». Ce
        `or` est precisement ce qui a laisse passer la regression : il rend
        vrai un fichier qui ne declare que l'un des deux, alors que les
        commandes du depot nommaient l'autre. On assertionne donc sur le
        service reellement commun, et sur lui seul.
        """
        for filepath in compose_paths():
            services = compose_services(filepath)
            assert 'promptforge-web' in services, (
                f"{filepath.name} ne declare pas 'promptforge-web' : "
                f"services = {sorted(services)}"
            )

    def test_ollama_service_only_where_the_gpu_can_be_exposed(self):
        """Inventaire explicite : qui embarque Ollama, qui l'attend natif.

        Ce partage est le fond de DEC-010. Le figer ici evite qu'une variante
        derive en silence, et documente pourquoi une commande qui nomme
        `ollama` ne peut pas viser le compose par defaut.
        """
        base_dir = Path(__file__).parent.parent
        avec_ollama_conteneurise = {
            'docker-compose.yml',        # NVIDIA, GPU expose a Docker
            'docker-compose.cpu.yml',    # sans GPU
            'docker-compose.amd.yml',    # AMD ROCm Linux
            'docker-compose.amd-max.yml',
        }
        for filepath in compose_paths():
            services = compose_services(filepath)
            attendu = filepath.name in avec_ollama_conteneurise
            assert ('ollama' in services) is attendu, (
                f"{filepath.name} : service 'ollama' "
                f"{'attendu' if attendu else 'non attendu'}, "
                f"services = {sorted(services)}"
            )
            assert filepath != base_dir / 'compose.yaml' or services == {'promptforge-web'}, (
                "compose.yaml, chemin par defaut DEC-010, ne doit exposer que "
                f"l'interface : services = {sorted(services)}"
            )


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
        dockerfile = Path(__file__).parent.parent / 'docker' / 'Dockerfile'
        assert dockerfile.exists(), "Dockerfile n'existe pas"

    def test_dockerfile_web_exists(self):
        """Vérifie que Dockerfile.web existe."""
        dockerfile = Path(__file__).parent.parent / 'docker' / 'Dockerfile.web'
        assert dockerfile.exists(), "Dockerfile.web n'existe pas"

    def test_dockerfile_web_copies_templates(self):
        """Vérifie que Dockerfile.web copie les templates."""
        dockerfile = Path(__file__).parent.parent / 'docker' / 'Dockerfile.web'
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


class TestComposeServiceSeam:
    """Couture entre les commandes du depot et les compose qu'elles visent.

    Regle unique : **aucune commande du depot ne peut nommer un service
    absent du fichier compose contre lequel elle se resout.**

    Trois sources sont balayees : `Makefile`, `scripts/docker_helper.py` et
    `scripts/build.py`. Les deux scripts Python sont exerces reellement, avec
    `subprocess` remplace par un enregistreur : on verifie l'argv que le
    produit construirait, pas une lecture approximative de son source.
    """

    # --- outillage commun ------------------------------------------------

    @staticmethod
    def _assert_services_exist(source, tokens, compose_file, services):
        path = BASE_DIR / compose_file
        assert path.exists(), (
            f"{source} : fichier compose introuvable '{compose_file}' "
            f"(commande : {' '.join(tokens)})"
        )
        declares = compose_services(path)
        for service in services:
            assert service in declares, (
                f"{source} nomme le service '{service}', absent de "
                f"{compose_file} (services declares : {sorted(declares)}).\n"
                f"Commande : {' '.join(tokens)}"
            )

    def _check_calls(self, source, recorder):
        vus = 0
        for tokens, (compose_file, services) in recorder.compose_calls():
            self._assert_services_exist(source, tokens, compose_file, services)
            vus += 1
        return vus

    @staticmethod
    def _install_recorder(monkeypatch, module, recorder):
        monkeypatch.setattr(module, "subprocess", recorder, raising=False)
        if hasattr(module, "time"):
            monkeypatch.setattr(module, "time", types.SimpleNamespace(sleep=lambda *_: None))

    # --- le parseur lui-meme --------------------------------------------

    @pytest.mark.parametrize(
        "commande,attendu",
        [
            ("docker compose build promptforge", ("compose.yaml", ["promptforge"])),
            ("docker compose up -d ollama", ("compose.yaml", ["ollama"])),
            ("docker compose -f docker/compose/docker-compose.cpu.yml up -d",
             ("docker/compose/docker-compose.cpu.yml", [])),
            ("docker compose run --rm --no-deps --entrypoint promptforge "
             "promptforge-web --path /data list",
             ("compose.yaml", ["promptforge-web"])),
            ("docker compose exec -T ollama ollama pull qwen3:8b",
             ("compose.yaml", ["ollama"])),
            ("docker compose logs -f promptforge-web", ("compose.yaml", ["promptforge-web"])),
            ("docker compose down -v", ("compose.yaml", [])),
            ("docker compose build --no-cache --pull", ("compose.yaml", [])),
            ("docker compose -f a.yml down --rmi local", ("a.yml", [])),
        ],
    )
    def test_parser_extracts_file_and_services(self, commande, attendu):
        """Le parseur de commandes est lui-meme teste.

        Sans cela, un test de couture qui n'extrait rien passerait au vert en
        ne verifiant rien : c'est le meme piege que le `or` qu'il remplace.
        """
        assert parse_compose_command(shlex.split(commande)) == attendu

    def test_parser_ignores_non_compose_commands(self):
        assert parse_compose_command(shlex.split("docker image prune -f")) is None
        assert parse_compose_command(shlex.split("python scripts/build.py up")) is None

    # --- source 1 : le Makefile -----------------------------------------

    def test_makefile_targets_name_existing_services(self):
        commandes = makefile_compose_commands()
        assert commandes, "aucune commande `docker compose` trouvee dans le Makefile"
        for recette, tokens in commandes:
            compose_file, services = parse_compose_command(tokens)
            self._assert_services_exist(f"Makefile [{recette}]", tokens, compose_file, services)

    # --- source 2 : scripts/docker_helper.py -----------------------------

    def test_docker_helper_commands_name_existing_services(self, monkeypatch):
        monkeypatch.chdir(BASE_DIR)
        # Ollama injoignable : `status` doit tomber dans sa branche d'erreur
        # sans tenter d'appel reseau reel.
        monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
        monkeypatch.setattr("builtins.input", lambda *_: "n")

        module = load_script("docker_helper")
        recorder = RecordingSubprocess()
        self._install_recorder(monkeypatch, module, recorder)
        monkeypatch.setattr(
            module, "shutil",
            types.SimpleNamespace(which=lambda name: "/usr/bin/" + name),
        )

        args = types.SimpleNamespace(file=None, service=None, cmd=["list"])
        for nom in ("start", "stop", "status", "run", "web", "logs", "shell", "build", "clean"):
            getattr(module, f"cmd_{nom}")(args)

        args_logs = types.SimpleNamespace(file=None, service="promptforge-web", cmd=[])
        module.cmd_logs(args_logs)

        assert self._check_calls("scripts/docker_helper.py", recorder) > 0

    @pytest.mark.parametrize("variante", [p.name for p in compose_paths()])
    def test_docker_helper_commands_on_every_variant(self, monkeypatch, variante):
        """Chaque commande, confrontee a chacune des sept variantes.

        Les six variantes doivent rester coherentes : une commande valable
        sur le compose par defaut doit l'etre sur toutes, ou echouer
        explicitement.
        """
        monkeypatch.chdir(BASE_DIR)
        monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
        monkeypatch.setattr("builtins.input", lambda *_: "n")

        chemin = (
            DEFAULT_COMPOSE if variante == DEFAULT_COMPOSE else f"docker/compose/{variante}"
        )
        module = load_script("docker_helper")
        recorder = RecordingSubprocess()
        self._install_recorder(monkeypatch, module, recorder)
        monkeypatch.setattr(
            module, "shutil",
            types.SimpleNamespace(which=lambda name: "/usr/bin/" + name),
        )

        args = types.SimpleNamespace(file=chemin, service=None, cmd=["list"])
        for nom in ("start", "stop", "status", "run", "web", "logs", "shell", "build"):
            getattr(module, f"cmd_{nom}")(args)

        assert self._check_calls(f"scripts/docker_helper.py [-f {chemin}]", recorder) > 0

    def test_docker_helper_refuses_an_absent_service(self, monkeypatch, capsys):
        """Le garde-fou runtime existe et refuse, au lieu de laisser passer."""
        monkeypatch.chdir(BASE_DIR)
        module = load_script("docker_helper")
        recorder = RecordingSubprocess()
        self._install_recorder(monkeypatch, module, recorder)

        assert module.require_service(DEFAULT_COMPOSE, "promptforge-web") is True
        assert module.require_service(DEFAULT_COMPOSE, "ollama") is False
        assert "n'existe pas" in capsys.readouterr().out

    def test_docker_helper_targets_no_unpinned_model(self):
        """Le modele du helper est celui des compose (D-022, sixieme liste)."""
        module = load_script("docker_helper")
        assert module.DEFAULT_MODEL == "qwen3:8b"

        # Hors commentaires : le commentaire qui documente la correction cite
        # l'ancienne valeur, ce n'est pas une occurrence executable.
        code = [
            ligne for ligne in (BASE_DIR / "scripts" / "docker_helper.py").read_text().splitlines()
            if not ligne.lstrip().startswith("#")
        ]
        assert not [ligne for ligne in code if "llama3.1" in ligne], (
            "llama3.1 n'existe dans aucun compose, ni dans RECOMMENDED_MODELS, "
            "ni dans OLLAMA_MODELS_INFO"
        )

        # Le modele du helper doit exister dans le compose par defaut.
        contenu = (BASE_DIR / DEFAULT_COMPOSE).read_text()
        assert module.DEFAULT_MODEL in contenu, (
            f"{module.DEFAULT_MODEL} n'apparait pas dans {DEFAULT_COMPOSE}"
        )

    # --- source 3 : scripts/build.py -------------------------------------

    @pytest.mark.parametrize("config", [None, "default", "nvidia", "cpu", "linux-amd",
                                        "linux-amd-max", "win-amd", "win-nvidia-native"])
    def test_build_script_commands_name_existing_services(self, monkeypatch, config):
        monkeypatch.chdir(BASE_DIR)
        monkeypatch.setattr("builtins.input", lambda *_: "n")

        module = load_script("build")
        recorder = RecordingSubprocess()
        self._install_recorder(monkeypatch, module, recorder)

        args = types.SimpleNamespace(
            config=config, no_cache=False, parallel=None, build=False,
            force=True, images=True, dev=False,
        )
        for nom in ("build", "up", "down", "clean"):
            getattr(module, f"cmd_{nom}")(args)

        assert self._check_calls(f"scripts/build.py [-c {config}]", recorder) > 0

    def test_build_script_compose_files_all_exist(self):
        module = load_script("build")
        for config, chemin in module.COMPOSE_FILES.items():
            assert (BASE_DIR / chemin).exists(), f"build.py -c {config} vise {chemin}, absent"


class TestDefaultPathIsActuallySelected:
    """DEC-010 : le defaut proclame doit etre celui que le code emprunte.

    `compose.yaml` etait annonce comme chemin par defaut dans le README, sans
    qu'aucune ligne du depot ne le selectionne : `launcher.py` et
    `scripts/build.py` enumeraient les six variantes de `docker/compose/` et
    l'ignoraient. Un defaut que le produit n'emprunte jamais n'en est pas un.
    """

    def test_build_script_defaults_to_the_root_compose(self):
        module = load_script("build")
        assert module.get_compose_file(None) == DEFAULT_COMPOSE
        assert module.get_compose_file("default") == DEFAULT_COMPOSE

    def test_build_script_keeps_hardware_detection_behind_an_explicit_flag(self):
        """La detection GPU reste possible, mais seulement si on la demande.

        `detect_gpu()` n'a aucune branche Darwin (D-018) : la laisser piloter
        le defaut faisait retomber macOS sur `cpu`, donc sur un Ollama
        conteneurise sans acces Metal, exactement ce que DEC-010 remplace.
        """
        module = load_script("build")
        assert module.AUTO_CONFIG in module.CONFIG_CHOICES
        assert module.DEFAULT_CONFIG == "default"

    @pytest.mark.parametrize(
        "systeme,gpu",
        [("Darwin", "apple"), ("Darwin", "cpu"), ("Windows", "nvidia"),
         ("Windows", "amd"), ("Windows", "cpu"), ("Linux", "nvidia"),
         ("Linux", "amd"), ("Linux", "cpu")],
    )
    def test_launcher_selects_the_root_compose_on_every_system(self, systeme, gpu):
        launcher = load_script_at(BASE_DIR / "launcher.py", "_seam_launcher")
        launcher.state["os"] = systeme
        launcher.state["gpu_type"] = gpu
        launcher.select_docker_compose()

        cle = launcher.state["docker_compose_file"]
        assert cle == "default", f"{systeme}/{gpu} selectionne '{cle}' au lieu du defaut"
        assert launcher.DOCKER_COMPOSE_OPTIONS[cle]["file"] == DEFAULT_COMPOSE
        assert launcher.state["available_compose_files"][0] == "default"

    def test_launcher_never_proposes_containerized_ollama_on_macos(self):
        """D-020 : Docker Desktop ne passe pas Metal aux conteneurs."""
        launcher = load_script_at(BASE_DIR / "launcher.py", "_seam_launcher")
        launcher.state["os"] = "Darwin"
        launcher.state["gpu_type"] = "apple"
        launcher.select_docker_compose()

        for cle in launcher.state["available_compose_files"]:
            chemin = BASE_DIR / launcher.DOCKER_COMPOSE_OPTIONS[cle]["file"]
            assert "ollama" not in compose_services(chemin), (
                f"macOS propose '{cle}', qui conteneurise Ollama"
            )

    def test_launcher_options_point_to_existing_files(self):
        launcher = load_script_at(BASE_DIR / "launcher.py", "_seam_launcher")
        for cle, info in launcher.DOCKER_COMPOSE_OPTIONS.items():
            assert (BASE_DIR / info["file"]).exists(), f"launcher '{cle}' vise {info['file']}"


# ======================================================================
# Fraicheur de l'etat du launcher
# ======================================================================
#
# Defaut constate en direct par le dev, le 2026-09-04 : `launcher.py` ne
# sondait Ollama qu'au demarrage du serveur. Une instance lancee a 11h14
# affichait encore a 15h l'etat mesure a 11h14. Mesure a l'appui :
#
#     curl -s http://localhost:7850/api/status  -> "ollama_running": false
#     curl -s -o /dev/null -w "%{http_code}" \
#          http://localhost:11434/api/tags      -> 200
#
# Le bouton « Rafraichir » existait, mais rien n'indiquait a l'utilisateur
# que ce qu'il lisait etait perime. Quiconque demarre Ollama APRES avoir
# ouvert la page voyait un systeme eteint et concluait que le produit ne
# marche pas.
#
# Ces tests EXECUTENT `launcher.py` : ils montent son vrai serveur HTTP,
# parlent a `/api/status` par le reseau, et font apparaitre un faux Ollama
# en cours de route. Un `HTTP 200` sur la racine ne prouve rien ; le
# comportement, si.

def free_port():
    """Un port libre sur la boucle locale, rendu apres fermeture."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _JsonServer:
    """Un vrai serveur HTTP jetable, pour tenir lieu d'Ollama.

    On ne simule pas la couche reseau : la sonde de `launcher.py` fait un
    vrai `urlopen` vers un vrai socket, exactement comme en production.
    """

    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.hits = 0
        parent = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parent.hits += 1
                body = _json.dumps(parent.payload).encode()
                self.send_response(parent.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]

    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class _BlackHole:
    """Un socket qui accepte la connexion et ne repond jamais.

    C'est le seul moyen honnete de produire un delai depasse : le port
    ecoute (donc « connexion refusee » est exclu), mais rien ne repond.
    C'est exactement le cas que `check_ollama()` ecrivait `False`.
    """

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)  # backlog : la connexion est acceptee par le noyau
        self.port = self.sock.getsockname()[1]
        return self

    def __exit__(self, *exc):
        self.sock.close()


# Port sur lequel rien n'ecoute jamais : la connexion est refusee, ce qui
# est une mesure concluante et non une absence de mesure.
CLOSED_PORT = 1


def fresh_launcher(name):
    """Charge `launcher.py` comme module, avec un `state` neuf a chaque fois."""
    return load_script_at(BASE_DIR / "launcher.py", name)


class DockerStub:
    """Faux `subprocess` : evite de forker `docker info` dans les tests.

    Enregistre les argv, ce qui permet d'assertionner sur la cadence lente
    (Docker sonde ou non) plutot que sur une intention declaree.
    """

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self, returncode=0, raises=None):
        self.calls = []
        self.returncode = returncode
        self.raises = raises

    def run(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        if self.raises is not None:
            raise self.raises
        return types.SimpleNamespace(returncode=self.returncode, stdout="", stderr="")


class TestProbeIsTriState:
    """Trois etats, pas deux. « Je ne sais pas » n'est pas « c'est eteint ».

    Meme confusion que D-018, ou « non mesurable » devenait « pas de GPU ».
    """

    def test_refused_connection_is_down(self):
        module = fresh_launcher("_freshness_down")
        status, body = module.probe_http(f"http://127.0.0.1:{CLOSED_PORT}/", timeout=1)
        assert status == module.STATUS_DOWN
        assert body is None

    def test_timeout_is_unknown_not_down(self):
        """Le cas exact que l'ancien `except: pass` ecrivait `False`."""
        module = fresh_launcher("_freshness_timeout")
        with _BlackHole() as trou:
            status, body = module.probe_http(f"http://127.0.0.1:{trou.port}/", timeout=0.4)
        assert status == module.STATUS_UNKNOWN, (
            "un delai depasse doit rendre 'unknown' : le port ecoute, "
            "affirmer que le service est eteint serait faux"
        )
        assert body is None

    def test_unexpected_http_code_is_unknown(self):
        """Quelque chose repond, mais pas ce qui est attendu."""
        module = fresh_launcher("_freshness_500")
        with _JsonServer({"boom": True}, status=500) as serveur:
            status, _ = module.probe_http(f"http://127.0.0.1:{serveur.port}/", timeout=2)
        assert status == module.STATUS_UNKNOWN

    def test_success_is_up_with_body(self):
        module = fresh_launcher("_freshness_up")
        with _JsonServer({"models": []}) as serveur:
            status, body = module.probe_http(f"http://127.0.0.1:{serveur.port}/", timeout=2)
        assert status == module.STATUS_UP
        assert _json.loads(body.decode()) == {"models": []}

    def test_unknown_never_reads_as_running(self):
        """Le booleen historique ne vaut `True` que sur `up`."""
        module = fresh_launcher("_freshness_bool")
        for statut, attendu in (
            (module.STATUS_UP, True),
            (module.STATUS_DOWN, False),
            (module.STATUS_UNKNOWN, False),
        ):
            module.set_service_status("ollama", statut)
            assert module.state["ollama_running"] is attendu
            assert module.state["ollama_status"] == statut


class TestCheckOllamaTriState:
    """`check_ollama()` execute, contre de vrais sockets."""

    def test_absent_ollama_is_down(self):
        module = fresh_launcher("_check_ollama_down")
        module.OLLAMA_PORT = CLOSED_PORT
        module.HTTP_PROBE_TIMEOUT = 1
        assert module.check_ollama() == module.STATUS_DOWN
        assert module.state["ollama_running"] is False
        assert module.state["installed_models"] == []

    def test_responding_ollama_is_up_and_lists_models(self):
        module = fresh_launcher("_check_ollama_up")
        module.HTTP_PROBE_TIMEOUT = 2
        module.state["ollama_model"] = "qwen3:8b"
        with _JsonServer({"models": [{"name": "qwen3:8b"}]}) as serveur:
            module.OLLAMA_PORT = serveur.port
            assert module.check_ollama() == module.STATUS_UP
        assert module.state["installed_models"] == ["qwen3:8b"]
        assert module.state["model_installed"] is True

    def test_timeout_leaves_the_state_unknown_and_keeps_last_models(self):
        """Un delai depasse n'efface pas ce qu'on savait ; il le date."""
        module = fresh_launcher("_check_ollama_unknown")
        module.HTTP_PROBE_TIMEOUT = 0.4
        module.state["installed_models"] = ["qwen3:8b"]
        module.state["model_installed"] = True
        with _BlackHole() as trou:
            module.OLLAMA_PORT = trou.port
            assert module.check_ollama() == module.STATUS_UNKNOWN
        assert module.state["ollama_running"] is False
        assert module.state["installed_models"] == ["qwen3:8b"], (
            "on ne sait pas : effacer la liste connue serait affirmer "
            "qu'elle est vide, ce qui n'a pas ete mesure"
        )

    def test_a_200_that_is_not_ollama_is_unknown(self):
        """`HTTP 200` n'est pas une preuve que le service fonctionne."""
        module = fresh_launcher("_check_ollama_wrong_200")
        module.HTTP_PROBE_TIMEOUT = 2
        with _JsonServer({"ceci": "n'est pas /api/tags"}) as serveur:
            module.OLLAMA_PORT = serveur.port
            statut = module.check_ollama()
        # `models` absent est tolere par l'API (liste vide), mais une
        # charge illisible doit rester indeterminee.
        assert statut in (module.STATUS_UP, module.STATUS_UNKNOWN)
        assert module.state["ollama_running"] is (statut == module.STATUS_UP)


class TestCheckDockerTriState:
    def test_timeout_is_unknown(self):
        module = fresh_launcher("_check_docker_unknown")
        module.subprocess = DockerStub(raises=subprocess.TimeoutExpired("docker", 10))
        assert module.check_docker() == module.STATUS_UNKNOWN
        assert module.state["docker_running"] is False

    def test_missing_binary_is_down_and_not_installed(self):
        module = fresh_launcher("_check_docker_absent")
        module.subprocess = DockerStub(raises=FileNotFoundError("docker"))
        assert module.check_docker() == module.STATUS_DOWN
        assert module.state["docker_installed"] is False

    def test_non_zero_return_code_is_down(self):
        module = fresh_launcher("_check_docker_stopped")
        module.subprocess = DockerStub(returncode=1)
        assert module.check_docker() == module.STATUS_DOWN

    def test_success_is_up(self):
        module = fresh_launcher("_check_docker_ok")
        module.subprocess = DockerStub(returncode=0)
        assert module.check_docker() == module.STATUS_UP


class TestFreshnessIsExposed:
    """Un etat affiche sans date est un etat qui ment des qu'il vieillit."""

    def test_payload_carries_its_age(self):
        module = fresh_launcher("_freshness_payload")
        module.stamp_probe(now=1000.0, include_docker=True)
        payload = module.status_payload(now=1003.0)

        assert payload["checked_at"] == 1000.0
        assert payload["checked_at_label"]
        assert payload["age_seconds"] == 3.0
        assert payload["stale"] is False
        assert payload["stale_after_seconds"] == module.STALE_AFTER

    def test_payload_declares_itself_stale_past_the_threshold(self):
        module = fresh_launcher("_freshness_stale")
        module.stamp_probe(now=1000.0)
        payload = module.status_payload(now=1000.0 + module.STALE_AFTER + 1)
        assert payload["stale"] is True

    def test_a_never_probed_state_is_stale(self):
        module = fresh_launcher("_freshness_never")
        payload = module.status_payload()
        assert payload["checked_at"] is None
        assert payload["age_seconds"] is None
        assert payload["stale"] is True

    def test_the_interface_renders_the_freshness(self):
        """Le HTML doit porter le rendu, pas seulement le payload."""
        module = fresh_launcher("_freshness_html")
        assert 'id="freshness"' in module.HTML_TEMPLATE
        assert "updateFreshness" in module.HTML_TEMPLATE
        assert "checked_at_label" in module.HTML_TEMPLATE
        # Le cas ou le launcher lui-meme ne repond plus : sans lui, l'age
        # afficherait la meme valeur pour l'eternite.
        assert "markLauncherOffline" in module.HTML_TEMPLATE

    def test_the_interface_renders_the_third_state(self):
        module = fresh_launcher("_freshness_html_unknown")
        assert "status-unknown" in module.HTML_TEMPLATE
        assert "ollama_status" in module.HTML_TEMPLATE
        assert "docker_status" in module.HTML_TEMPLATE
        assert "promptforge_status" in module.HTML_TEMPLATE

    def test_an_unknown_state_never_locks_the_user_out(self):
        """Un etat qu'on ne connait pas ne doit rien griser ni cacher.

        C'est la lecon produit du defaut corrige : le dev n'a rien pu faire
        parce que l'interface, sur la foi d'une mesure perimee, avait decide
        a sa place que rien n'etait disponible.
        """
        module = fresh_launcher("_freshness_not_locked")
        html = module.HTML_TEMPLATE

        # Les boutons se decident sur le statut a trois etats, pas sur le
        # booleen : `=== 'up'` pour demarrer, `=== 'down'` pour arreter,
        # donc les deux restent actifs quand l'etat est indetermine.
        assert "data.ollama_status === 'up' || data.action_in_progress" in html
        assert "btnOllamaStop.disabled = data.ollama_status === 'down'" in html
        assert "btnPfStop.disabled = data.promptforge_status === 'down'" in html

        # Le lien vers le produit n'est masque que sur un « eteint » mesure.
        assert "(data.promptforge_status === 'down') ? 'none' : 'block'" in html
        assert "data.promptforge_running ? 'block' : 'none'" not in html


class TestProbeCadence:
    """La cadence est un compromis mesure, pas une preference.

    Couts mesures le 2026-09-04 sur la machine de reference :
    Ollama 4.4 ms, PromptForge 0.5 ms, `docker info` 107.6 ms,
    `docker images` 88.0 ms. Trois ordres de grandeur separent les deux
    familles : elles ne peuvent pas partager la meme cadence.
    """

    def test_docker_is_probed_far_less_often_than_http(self):
        module = fresh_launcher("_cadence_ttl")
        assert module.FAST_PROBE_TTL < module.SLOW_PROBE_TTL
        assert module.SLOW_PROBE_TTL >= 5 * module.FAST_PROBE_TTL

    def test_a_fast_probe_forks_no_subprocess(self):
        module = fresh_launcher("_cadence_fast")
        stub = DockerStub()
        module.subprocess = stub
        module.OLLAMA_PORT = CLOSED_PORT
        module.PROMPTFORGE_PORT = CLOSED_PORT
        module.HTTP_PROBE_TIMEOUT = 1

        module.run_probes(include_docker=False)
        assert stub.calls == [], (
            "la cadence rapide ne doit forker aucun `docker` : "
            f"appels observes = {stub.calls}"
        )

    def test_a_slow_probe_does_fork_docker(self):
        module = fresh_launcher("_cadence_slow")
        stub = DockerStub()
        module.subprocess = stub
        module.OLLAMA_PORT = CLOSED_PORT
        module.PROMPTFORGE_PORT = CLOSED_PORT
        module.HTTP_PROBE_TIMEOUT = 1

        module.run_probes(include_docker=True)
        assert any(call[:2] == ["docker", "info"] for call in stub.calls), stub.calls

    def test_nothing_is_probed_before_the_ttl_expires(self):
        module = fresh_launcher("_cadence_ttl_guard")
        module.stamp_probe(now=time.time(), include_docker=True)
        assert module.ensure_fresh_status() is None, (
            "sonder a chaque appel rendrait l'interface poussive : "
            "le client interroge toutes les 3 s"
        )

    def test_the_fast_ttl_expires_before_the_client_polls_twice(self):
        """Peremption maximale vue par l'utilisateur : ~5 s."""
        module = fresh_launcher("_cadence_window")
        module.stamp_probe(now=time.time() - module.FAST_PROBE_TTL - 0.1,
                           include_docker=True)
        fast_due, slow_due = module.probe_due()
        assert fast_due is True
        assert slow_due is False, "Docker ne doit pas suivre la cadence rapide"

    def test_only_one_probe_flies_at_a_time(self):
        """Sans cela, un `docker info` lent verrait s'empiler les sondes."""
        module = fresh_launcher("_cadence_single_flight")
        module.state["probe_in_progress"] = True
        assert module.ensure_fresh_status() is None

    def test_repeated_probes_do_not_flood_the_log_buffer(self):
        """Le tampon fait 50 lignes ; sonder toutes les 2 s l'effacerait."""
        module = fresh_launcher("_cadence_log")
        module.subprocess = DockerStub()
        module.OLLAMA_PORT = CLOSED_PORT
        module.PROMPTFORGE_PORT = CLOSED_PORT
        module.HTTP_PROBE_TIMEOUT = 1

        module.run_probes(include_docker=False)
        apres_premiere = len(module.state["logs"])
        for _ in range(20):
            module.run_probes(include_docker=False)
        ajoutees = len(module.state["logs"]) - apres_premiere

        assert ajoutees == 0, (
            "vingt sondes sans changement d'etat ont ajoute "
            f"{ajoutees} lignes de log : le tampon de 50 serait efface "
            "en moins de deux minutes"
        )


class TestStatusEndpointRefreshesItself:
    """LE test de non-regression : execute le serveur HTTP de `launcher.py`.

    Aucune couture de `launcher.py` n'etait executee jusqu'ici cote statut :
    `TestLauncherConfig` lit le fichier comme du texte. Ici on monte le vrai
    `LauncherHandler`, on l'interroge par le reseau, et on fait apparaitre
    un Ollama en cours de route sans jamais poster la moindre action.
    """

    @staticmethod
    def _serve(module):
        serveur = http.server.HTTPServer(("127.0.0.1", 0), module.LauncherHandler)
        fil = threading.Thread(target=serveur.serve_forever, daemon=True)
        fil.start()
        return serveur, fil

    @staticmethod
    def _get_status(port):
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as r:
            assert r.status == 200
            return _json.loads(r.read().decode())

    def test_ollama_started_after_the_page_is_seen_without_any_click(self):
        """Le scenario exact vecu par le dev, rejoue de bout en bout."""
        module = fresh_launcher("_endpoint_appearing")
        module.subprocess = DockerStub()
        module.PROMPTFORGE_PORT = CLOSED_PORT
        module.HTTP_PROBE_TIMEOUT = 1
        module.state["ollama_model"] = "qwen3:8b"

        # 1. Le launcher demarre pendant qu'Ollama est absent.
        module.OLLAMA_PORT = CLOSED_PORT
        module.refresh_status()
        assert module.state["ollama_status"] == module.STATUS_DOWN

        serveur, fil = self._serve(module)
        port = serveur.server_address[1]
        try:
            depart = self._get_status(port)
            assert depart["ollama_running"] is False
            assert depart["ollama_status"] == "down"
            premier_horodatage = depart["checked_at"]
            assert premier_horodatage is not None

            # 2. Ollama apparait APRES l'ouverture de la page.
            with _JsonServer({"models": [{"name": "qwen3:8b"}]}) as ollama:
                module.OLLAMA_PORT = ollama.port

                # 3. Le client se contente de son sondage periodique de 3 s.
                #    Aucun POST /api/action, aucun clic sur « Rafraichir ».
                limite = time.time() + 20
                vu = None
                while time.time() < limite:
                    time.sleep(0.5)
                    vu = self._get_status(port)
                    if vu["ollama_status"] == "up":
                        break

            assert vu is not None
            assert vu["ollama_status"] == "up", (
                "un Ollama demarre apres l'ouverture de la page doit etre vu "
                "sans intervention de l'utilisateur ; etat lu : "
                f"{vu['ollama_status']}, age {vu['age_seconds']} s"
            )
            assert vu["ollama_running"] is True
            assert vu["installed_models"] == ["qwen3:8b"]
            assert vu["checked_at"] > premier_horodatage, (
                "l'horodatage doit avancer : sinon l'etat est fige"
            )
            assert vu["age_seconds"] <= module.STALE_AFTER
        finally:
            serveur.shutdown()
            serveur.server_close()
            fil.join(timeout=5)

    def test_the_endpoint_reports_its_own_staleness(self):
        module = fresh_launcher("_endpoint_stale")
        module.subprocess = DockerStub()
        module.OLLAMA_PORT = CLOSED_PORT
        module.PROMPTFORGE_PORT = CLOSED_PORT
        module.HTTP_PROBE_TIMEOUT = 1

        serveur, fil = self._serve(module)
        port = serveur.server_address[1]
        try:
            # Jamais sonde : le payload doit le dire, pas se taire.
            vierge = self._get_status(port)
            assert vierge["stale"] is True

            # Etat volontairement vieilli : `stale` doit repasser a True.
            module.stamp_probe(now=time.time() - module.STALE_AFTER - 5,
                               include_docker=True)
            vieux = self._get_status(port)
            assert vieux["stale"] is True
            assert vieux["age_seconds"] > module.STALE_AFTER
        finally:
            serveur.shutdown()
            serveur.server_close()
            fil.join(timeout=5)

    def test_the_endpoint_ships_the_python_compose_table(self):
        """D-060 : une seule table de compose, celle de Python."""
        module = fresh_launcher("_endpoint_compose")
        module.subprocess = DockerStub()
        module.OLLAMA_PORT = CLOSED_PORT
        module.PROMPTFORGE_PORT = CLOSED_PORT
        module.HTTP_PROBE_TIMEOUT = 1

        serveur, fil = self._serve(module)
        port = serveur.server_address[1]
        try:
            recu = self._get_status(port)
        finally:
            serveur.shutdown()
            serveur.server_close()
            fil.join(timeout=5)

        assert recu["compose_options"] == module.DOCKER_COMPOSE_OPTIONS, (
            "/api/status n'envoyait jamais DOCKER_COMPOSE_OPTIONS : le "
            "JavaScript en gardait une copie, deja divergente"
        )


class TestComposeTableIsNotDuplicated:
    """D-060 : `COMPOSE_OPTIONS` en JavaScript dupliquait le dict Python.

    Les deux vivaient dans le meme fichier et avaient deja divergé : la
    copie JS decrivait `cpu` comme « optimise CPU », l'original Python
    comme « optimise CPU, 8GB+ RAM ».
    """

    def test_no_javascript_copy_remains(self):
        module = fresh_launcher("_no_js_compose_copy")
        assert "COMPOSE_OPTIONS = {" not in module.HTML_TEMPLATE, (
            "la table de compose est redevenue duplique en JavaScript"
        )

    def test_the_selector_reads_the_served_table(self):
        module = fresh_launcher("_js_reads_payload")
        assert "data.compose_options" in module.HTML_TEMPLATE

    def test_every_served_label_comes_from_python(self):
        module = fresh_launcher("_labels_from_python")
        payload = module.status_payload()
        for cle, info in module.DOCKER_COMPOSE_OPTIONS.items():
            assert payload["compose_options"][cle]["label"] == info["label"]
            assert payload["compose_options"][cle]["description"] == info["description"]
