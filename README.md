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

## 🛠️ Mode Docker (optionnel)

```bash
python launcher.py  # Lance le launcher Docker GUI
```

---

## 📄 Licence

MIT
