# ✨ PromptForge

**Transforme tes prompts basiques en prompts d'expert.**

> "trouve moi des mots clés" (38 chars) → Prompt enrichi (1,857 chars) = **x48 d'enrichissement**

---

## 🚀 Installation Rapide (Mode Natif)

### Prérequis
- **Python 3.10+** ([télécharger](https://python.org))
- **Ollama** ([télécharger](https://ollama.ai)) - pour le reformatage intelligent

### Lancement

**Windows:**
```batch
# Double-cliquer sur Start.bat
# Ou dans le terminal:
python start.py
```

**Mac/Linux:**
```bash
./start.sh
# Ou: python3 start.py
```

### Commandes

```bash
python start.py           # Lance l'interface web
python start.py --install # Installe les dépendances
python start.py --check   # Vérifie l'installation
```

L'interface s'ouvre sur **http://localhost:7860**

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
