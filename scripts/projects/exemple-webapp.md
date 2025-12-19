# Mon Application Web

## Description
Application web de gestion de tâches avec authentification utilisateur.

## Stack Technique

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy (ORM)
- PostgreSQL
- Pydantic pour la validation

### Frontend
- React 18
- TypeScript
- TailwindCSS
- React Query

### Infrastructure
- Docker / Docker Compose
- Nginx (reverse proxy)
- GitHub Actions (CI/CD)

## Structure du Projet

```
project/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
└── docker-compose.yml
```

## Conventions de Code

### Python
- Type hints obligatoires sur toutes les fonctions
- Docstrings Google style
- Black pour le formatage (line-length: 100)
- Tests avec pytest (coverage > 80%)
- Nommage: snake_case pour fonctions/variables, PascalCase pour classes

### TypeScript/React
- Composants fonctionnels avec hooks
- Props typées avec interfaces
- Prettier + ESLint
- Tests avec Vitest + Testing Library

### API
- REST avec versioning (/api/v1/)
- Réponses JSON standardisées
- Gestion d'erreurs centralisée
- Documentation OpenAPI automatique

## Patterns Utilisés
- Repository pattern pour l'accès aux données
- Dependency injection via FastAPI
- Service layer pour la logique métier
- DTOs (schemas Pydantic) pour les transferts

## Règles Métier Importantes
- Un utilisateur peut avoir plusieurs projets
- Les tâches appartiennent à un projet
- Soft delete sur toutes les entités
- Audit trail sur les modifications

## Notes
- Toujours valider les entrées utilisateur
- Utiliser des transactions pour les opérations multiples
- Logger les erreurs avec contexte suffisant
