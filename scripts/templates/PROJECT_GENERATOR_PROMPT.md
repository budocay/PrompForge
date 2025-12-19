# 🎯 Génère ta configuration projet avec ton IA

Ce prompt est conçu pour aider Claude, ChatGPT ou toute autre IA à générer un fichier de configuration complet pour PromptForge.

---

## 📋 Prompt à copier-coller

Envoie ce prompt à ton IA préférée :

```
Je veux créer un fichier de configuration pour documenter mon projet. Ce fichier servira de contexte pour optimiser mes futurs prompts.

Pose-moi ces questions UNE PAR UNE et attends ma réponse avant de continuer :

**QUESTIONS ESSENTIELLES :**

1. **Nom du projet** : Quel est le nom de ton projet ?

2. **Description** : En 2-3 phrases, que fait ce projet ? Quel problème résout-il ?

3. **Stack technique complète** :
   - Langage(s) de programmation ?
   - Framework(s) backend ?
   - Framework(s) frontend ?
   - Base de données ?
   - ORM / Query builder ?
   - Outils de build / bundler ?
   - Autres services (cache, queue, search...) ?

4. **Structure du projet** : Décris l'organisation des dossiers principaux, ou colle le résultat de `tree -L 2` ou `ls -la`

5. **Conventions de code** :
   - Nommage (camelCase, snake_case, PascalCase) ?
   - Formatage (Black, Prettier, ESLint...) ?
   - Style de documentation (Docstrings Google/NumPy, JSDoc...) ?
   - Gestion des erreurs ?

6. **Tests** :
   - Framework de test (pytest, Jest, JUnit...) ?
   - Couverture minimale attendue ?
   - Types de tests (unit, integration, e2e) ?

7. **Patterns et architecture** :
   - Architecture globale (MVC, Clean Architecture, Hexagonal...) ?
   - Design patterns utilisés (Repository, Factory, Singleton...) ?
   - Gestion d'état (Redux, Zustand, Pinia...) ?

8. **Règles métier importantes** : Y a-t-il des règles spécifiques que le code doit respecter ?

9. **Contraintes techniques** :
   - Performance (temps de réponse, mémoire...) ?
   - Sécurité (authentification, autorisation...) ?
   - Accessibilité ?
   - Compatibilité (navigateurs, versions...) ?

10. **Environnement de développement** :
    - Version control (Git flow, trunk-based...) ?
    - CI/CD ?
    - Conteneurisation (Docker) ?

**FORMAT DE SORTIE :**

Une fois toutes mes réponses collectées, génère un fichier Markdown avec cette structure :

---

# [Nom du Projet]

## Description
[Description détaillée]

## Stack Technique

### Backend
- [Technologie]: [Version si pertinent]

### Frontend
- [Technologie]: [Version si pertinent]

### Base de données
- [Technologie]

### Outils
- [Outil]: [Usage]

## Structure du Projet

```
[Arborescence des dossiers]
```

### Description des dossiers
- `[dossier]/`: [Rôle]

## Conventions de Code

### [Langage]
- Nommage: [Convention]
- Formatage: [Outil]
- Documentation: [Style]

### Gestion des erreurs
- [Approche]

## Tests
- Framework: [Nom]
- Couverture: [Objectif]
- Types: [Liste]

## Architecture et Patterns
- Architecture: [Type]
- Patterns: [Liste]

## Règles Métier
- [Règle 1]
- [Règle 2]

## Contraintes
- Performance: [Détails]
- Sécurité: [Détails]

## Environnement
- Git: [Workflow]
- CI/CD: [Outil]
- Docker: [Oui/Non]

## Notes Importantes
[Toute information supplémentaire utile]

---
```

---

## 💡 Conseils pour de meilleurs résultats

### Sois précis sur ta stack
❌ "J'utilise Python"
✅ "J'utilise Python 3.12 avec FastAPI 0.109, SQLAlchemy 2.0, et Pydantic v2"

### Décris ta structure
❌ "J'ai des dossiers pour le code"
✅ ```
src/
├── api/routes/      # Endpoints REST
├── core/            # Config, sécurité
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic DTOs
└── services/        # Business logic
```

### Explique tes conventions
❌ "Je fais du clean code"
✅ "Type hints obligatoires, docstrings Google style, max 100 chars/ligne, tests pytest avec fixtures"

### Mentionne les règles métier
❌ (rien)
✅ "Un utilisateur peut avoir max 5 projets actifs. Les tâches archivées sont supprimées après 30 jours."

---

## 🔄 Mettre à jour ta config

Quand ton projet évolue, relance le prompt avec :

```
Mon projet a évolué. Voici les changements :
- [Changement 1]
- [Changement 2]

Met à jour ma configuration existante :

[Colle ta config actuelle]
```

---

## 📁 Où sauvegarder le fichier ?

1. Sauvegarde le Markdown généré dans un fichier `mon-projet.md`
2. Dans PromptForge :
   - **CLI** : `promptforge init mon-projet --config ./mon-projet.md`
   - **Web** : Onglet "Projets" → Upload ou coller le contenu
