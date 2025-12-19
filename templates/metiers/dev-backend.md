# Configuration Projet - Développeur Backend

## Mon Profil

**Métier** : Développeur Backend
**Niveau** : [Junior / Confirmé / Senior / Lead]
**Spécialisation** : [API REST / Microservices / Data Engineering / DevOps]

---

## Stack Technique

### Langages & Frameworks

| Technologie | Version | Usage |
|-------------|---------|-------|
| **Python** | 3.11+ | API, Scripts, ML |
| **FastAPI** | 0.100+ | API REST principale |
| **SQLAlchemy** | 2.0+ | ORM |
| **PostgreSQL** | 15+ | Base principale |
| **Redis** | 7+ | Cache, Sessions |
| **Docker** | 24+ | Conteneurisation |
| [Ajouter] | ... | ... |

### Infrastructure

| Service | Provider | Usage |
|---------|----------|-------|
| **Cloud** | AWS / GCP / Azure | Hébergement |
| **CI/CD** | GitHub Actions / GitLab CI | Pipeline |
| **Monitoring** | Datadog / Prometheus | Observabilité |
| **Logs** | ELK / CloudWatch | Centralisation |

---

## Architecture Projet

### Type d'Architecture

- [ ] Monolithe modulaire
- [ ] Microservices
- [ ] Serverless
- [ ] Event-driven

### Patterns Utilisés

| Pattern | Implémentation |
|---------|----------------|
| **Repository** | Abstraction accès données |
| **Service Layer** | Logique métier |
| **Dependency Injection** | FastAPI Depends |
| **CQRS** | Si applicable |

### Structure des Dossiers

```
src/
├── api/           # Routes et endpoints
├── core/          # Config, security, deps
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas
├── services/      # Business logic
├── repositories/  # Data access
└── tests/         # Pytest
```

---

## Conventions de Code

### Style

| Règle | Valeur |
|-------|--------|
| **Formatter** | Black (line-length=100) |
| **Linter** | Ruff |
| **Type hints** | Obligatoires |
| **Docstrings** | Google style |
| **Commits** | Conventional commits |

### Naming

| Élément | Convention |
|---------|------------|
| **Classes** | PascalCase |
| **Fonctions** | snake_case |
| **Constantes** | UPPER_SNAKE_CASE |
| **Variables** | snake_case |
| **Endpoints** | kebab-case |

---

## Contraintes Projet

### Performance

- Temps de réponse API : < 200ms (p95)
- Requêtes DB : < 50ms
- Rate limiting : 100 req/min par user

### Sécurité

- Authentication : JWT / OAuth2
- Pas de secrets en dur
- Validation input stricte (Pydantic)
- CORS configuré

### Tests

- Coverage minimum : 80%
- Tests unitaires : pytest
- Tests intégration : pytest + testcontainers
- Tests E2E : si applicable

---

## Instructions pour le LLM

Quand je demande du code backend :

1. **Toujours inclure** :
   - Type hints complets
   - Docstrings Google style
   - Gestion d'erreurs (try/except, HTTPException)
   - Validation Pydantic

2. **Structure attendue** :
   - Séparer routes / services / repositories
   - Injection de dépendances FastAPI
   - Schemas Pydantic pour I/O

3. **Sécurité** :
   - Pas de SQL raw (utiliser ORM)
   - Valider tous les inputs
   - Logger les erreurs (pas les secrets)

4. **Format de réponse** :
   - Code complet et fonctionnel
   - Tests unitaires associés
   - Instructions de déploiement si pertinent

---

*Template Développeur Backend pour PromptForge*
