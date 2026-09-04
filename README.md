# ✨ PromptForge

**Transforme tes prompts basiques en prompts d'expert.**

> "trouve moi des mots clés" (38 chars) → Prompt enrichi (1,857 chars) = **x48 d'enrichissement**

---

## 🚀 Installation

PromptForge est **multiplateforme et pilote par Docker** : la meme commande sur
Windows, macOS et Linux.

### Prerequis

- **Docker** ([telecharger](https://docs.docker.com/get-docker/))
- **Ollama** ([telecharger](https://ollama.com/download)) — installe sur la
  machine hote, pas dans un conteneur

> **Pourquoi Ollama reste natif.** C'est le seul composant qui a besoin du GPU.
> Docker Desktop ne donne pas acces a Metal sur macOS, et l'acces GPU sous
> Windows depend du pilote : un Ollama conteneurise y perdrait l'acceleration
> materielle. Le conteneur PromptForge le joint sur l'hote. Sur Linux avec un
> GPU expose a Docker, Ollama peut aussi tourner en conteneur.

### Lancement

```bash
docker compose up
```

L'interface s'ouvre sur **http://localhost:7860**.

### Sans Docker

Le mode natif reste disponible sur les trois systemes :

```bash
python start.py           # Lance l'interface web
python start.py --install # Installe les dependances
python start.py --check   # Verifie l'installation
```

### Launcher graphique

```bash
python launcher.py        # Interface de controle Docker + Ollama
```

---

## Ligne de commande

PromptForge est aussi un CLI. Onze commandes, installables par
`pip install -e .` :

```bash
promptforge init <nom> --config <fichier.md>  # Creer un projet
promptforge use <nom>                          # Activer un projet
promptforge list                               # Lister les projets
promptforge delete <nom>                       # Supprimer un projet
promptforge reload <nom>                       # Recharger sa config
promptforge scan <chemin> --name <nom>         # Scanner un projet existant
promptforge format [prompt]                    # Reformater un prompt
promptforge history [--limit N]                # Consulter l'historique
promptforge status                             # Statut du systeme
promptforge template                           # Afficher le template de config
promptforge web [--port 7860]                  # Lancer l'interface web
```

Le coeur du CLI n'utilise que la bibliotheque standard : Gradio et tiktoken
sont optionnels, et `promptforge` fonctionne sans eux.

---

## 📖 Comment ça marche

### 1. Crée ton projet (une seule fois)
- Ouvre l'interface web
- Clique sur "⚙️ Configuration"
- Va dans "🚀 Créer un projet"
- Réponds aux questions du wizard (2-3 min)

### 2. Reformate tes prompts
- Sélectionne ton projet dans le menu déroulant
- Entre ton prompt basique
- Clique sur **"🚀 Reformater"**
- Copie le résultat enrichi !

---

## 🎯 Exemple

**Entrée (38 caractères):**
```
trouve moi des mots clés pour mon site
```

**Sortie enrichie:**
```xml
<context>
# Profil SEO
- Site: jardin-facile.fr (DR 15)
- Niche: Jardinage débutant
- Objectif: DR 30 en 12 mois
</context>

<task>
trouve moi des mots clés pour mon site
</task>

<output_requirements>
- Réponse structurée et actionnable
- Utilise le contexte fourni
</output_requirements>
```

---

## 📝 Métiers supportés

| Métier | Description |
|--------|-------------|
| 🔍 SEO Specialist | Mots-clés, backlinks, technique |
| 📈 Marketing Digital | Acquisition, growth, automation |
| 💻 Dev Backend/Frontend | Code, APIs, frameworks |
| 📊 Data Analyst | SQL, BI, dashboards |
| 🎯 Product Manager | Roadmap, OKRs, specs |
| 💼 Commercial | Prospection, CRM |
| 👥 RH / Recruteur | Sourcing, entretiens |
| 📞 Support Client | Tickets, CSAT |

---

## 🛠️ Variantes Docker

Le chemin par defaut (`docker compose up`) fait tourner l'interface en
conteneur et joint l'Ollama natif de l'hote. C'est le seul chemin proposé sur
macOS : Docker Desktop n'y passe pas le GPU aux conteneurs.

Sur Linux avec un GPU expose a Docker, Ollama peut aussi tourner en conteneur :

```bash
docker compose -f docker/compose/docker-compose.yml up      # NVIDIA
docker compose -f docker/compose/docker-compose.amd.yml up  # AMD ROCm
docker compose -f docker/compose/docker-compose.cpu.yml up  # sans GPU
```

Les cibles `make` visent le compose par defaut, surchargeable :

```bash
make docker-start                                                   # compose.yaml
make docker-start COMPOSE_FILE=docker/compose/docker-compose.cpu.yml
```

---

## 📄 Licence

MIT
