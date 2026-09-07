# Contribuer à PromptForge

Merci de l'intérêt. Ce document dit comment monter l'environnement, ce qui est
vérifié et ce qui ne l'est pas.

---

## Monter l'environnement

```bash
git clone https://github.com/budocay/PrompForge.git
cd PrompForge
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -e ".[all]"
```

`[all]` installe Gradio (interface web), tiktoken (comptage de tokens) et les
outils de dev (pytest, pytest-cov, black, ruff).

Vérifie :

```bash
python start.py --check
```

**Active toujours le venv avant d'utiliser le Makefile.** Les cibles appellent
`pytest`, `ruff`, `black` et `pip` sans préfixe. Sans venv actif, `make test` et
`make lint` échouent sur `No such file or directory` — ce n'est pas un bug du
dépôt.

---

## Lancer les tests

```bash
make test                      # toute la suite
pytest tests/ -q               # idem, en plus court
pytest tests/test_core.py -v   # un fichier
make test-cov                  # couverture, rapport HTML
```

Les tests unitaires simulent Ollama et sont rapides. Les tests d'intégration de
`tests/test_ollama_integration.py` appellent un vrai modèle : ils sont ignorés
si Ollama ne répond pas, et allongent nettement la suite s'il répond.

**Un test rouge bloque.** Si tu ne peux pas exécuter un test dans ton
environnement, dis-le explicitement dans la PR avec la commande à lancer,
plutôt que d'annoncer qu'il passe.

---

## Style de code

- Formateur : **black**, `line-length = 100`
- Linter : **ruff**, règles `E, F, W, I, N, UP`
- Python 3.10, 3.11, 3.12
- Docstrings : style Google
- Annotations de type : encouragées, pas imposées

```bash
make format         # black, réécrit
make lint           # ruff
make format-check   # black en lecture seule
```

### Dette de style existante

`make lint` et `make format-check` **ne sont pas verts aujourd'hui** sur la base
existante. C'est une dette connue et tracée, pas un défaut de ta PR, et
`make check` (qui enchaîne lint + format-check + test) est rouge pour la même
raison.

Conséquence pratique : **ne reformate pas tout le dépôt dans une PR de
fonctionnalité.** Un `black .` global noierait ta modification dans des milliers
de lignes de diff cosmétique et la rendrait irrelisable. Formate uniquement les
fichiers que tu touches.

---

## Pas d'intégration continue

Ce dépôt n'a **aucune CI** : il n'y a pas de `.github/workflows/`, rien ne
s'exécute automatiquement sur une PR. Toutes les vérifications sont locales et
reposent sur toi.

Avant de proposer une modification, lance au minimum :

```bash
make test
```

et indique dans la PR ce que tu as exécuté, avec la sortie.

---

## Organisation du code

```
promptforge/
├── core.py          orchestration, CRUD projets, format_prompt()
├── providers.py     client HTTP Ollama, conversion Markdown ↔ XML
├── database.py      SQLite
├── profiles.py      9 profils de modèles cibles
├── cli.py           interface argparse
├── tokens.py        estimation de tokens (tiktoken ou heuristique)
├── scanner.py       scanner de projets
├── security.py      CVE via OSV.dev, règles de sécurité
├── models_catalog.py  catalogue des modèles Ollama locaux
├── hardware.py      mesure de la machine
└── web/             paquet de l'interface Gradio, découpé par responsabilité

tests/               pytest
docker/              Dockerfile, Dockerfile.web, compose/ (6 variantes GPU)
compose.yaml         compose par défaut, à la racine
scripts/             outils de build
docs/                documentation
```

`promptforge/web/` est un paquet découpé par responsabilité : `interface.py`
assemble l'UI, les autres modules portent la logique (`analysis.py`,
`recommendations.py`, `scanner_helpers.py`, `onboarding.py`...).

---

## Quelques pièges

**Ajouter un profil de modèle** ne se limite pas à `profiles.py`. Il faut aussi :

- `web/profiles_ui.py::PROFILE_DESCRIPTIONS` — les clés sont couplées par chaîne
  à `PRESET_PROFILES`, et `get_profile()` retombe **silencieusement** sur
  `universel`. Un décalage sert le mauvais prompt sans lever d'erreur.
- `web/recommendations.py::DOMAIN_EXPERTISE` — chaque membre de `TargetModel` y
  est câblé au niveau module. Une entrée manquante lève un `KeyError` à
  l'exécution et casse l'import de tout le paquet `web`.

**Les sept fichiers compose doivent rester cohérents.** Modifier une seule
variante en laissant les six autres derrière crée une divergence silencieuse.
`promptforge-web` est le seul service commun aux sept ; le fichier par défaut ne
déclare **que** celui-là. Aucune commande du dépôt ne doit nommer `ollama` ou
`promptforge` sans passer un `-f` vers une variante qui les déclare.
`tests/test_launcher.py::TestComposeServiceSeam` verrouille ce point.

**Les images de base sont épinglées** sur une version exacte
(`python:3.12-slim`). Ne jamais passer à `latest`.

**Aucun secret en clair**, jamais, dans un compose, un Dockerfile ou un script.
PromptForge n'a besoin d'aucune clé d'API pour fonctionner : si tu en ajoutes
une, c'est probablement un signe que la conception dérive.

---

## Ouvrir une pull request

1. Branche depuis `main`.
2. Un sujet par PR.
3. Tests inclus, couvrant les cas d'erreur et les limites, pas seulement le
   chemin nominal.
4. `make test` vert.
5. Dans la description : ce que tu as changé, **les commandes que tu as
   exécutées et leur sortie**, et ce que tu n'as pas pu vérifier avec la raison.

Une vérification impossible dans ton environnement se déclare comme telle. Elle
ne se déclare pas comme réussie.

---

## Licence

En contribuant, tu acceptes que ta contribution soit publiée sous licence MIT,
comme le reste du projet. Voir [LICENSE](LICENSE).
