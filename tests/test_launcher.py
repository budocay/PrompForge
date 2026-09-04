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

import importlib.util
import re
import shlex
import sys
import types
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
