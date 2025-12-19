# EventMigo - Configuration de Contexte pour Prompts

## 1. Nom du Projet
**EventMigo** - Plateforme SaaS Multi-Tenant

---

## 2. Description

EventMigo est une plateforme SaaS multi-tenant permettant de gérer et diffuser des événements (festivals, conférences). Elle offre une application mobile Flutter pour les participants, un backend API Node.js robuste avec analytics, et un backoffice React pour les organisateurs. Le système supporte l'isolation complète des données par événement avec gestion des rôles et permissions.

---

## 3. Stack Technique

### Frontend Mobile
- **Framework**: Flutter (Dart)
- **State Management**: Provider
- **UI**: Material Design
- **Version**: 1.13.3+62

### Backend API
- **Runtime**: Node.js
- **Framework**: Express.js
- **Database**: MongoDB (Mongoose ODM)
- **Cache**: Redis
- **Auth**: JWT (7 jours)
- **Port**: 3000

### Backoffice Admin
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **HTTP Client**: Axios
- **Port**: 5173

### Infrastructure
- **Serveur**: api.eventmigo.com (195.35.29.9)
- **Process Manager**: PM2
- **Reverse Proxy**: Nginx
- **Flutter Previews**: Build Web par event

---

## 4. Structure des Dossiers

```
EventMigo/
├── lib/                          # Flutter Mobile App
│   ├── models/                   # Data models (Event, Groupe, Partner, Speaker)
│   ├── providers/                # State management (Provider pattern)
│   ├── pages/                    # Screens/Views
│   ├── services/                 # Business logic (Sync, Analytics, API)
│   ├── widgets/                  # Reusable UI components
│   └── main.dart                 # Entry point
│
├── backend/                      # Node.js API
│   └── src/
│       ├── models/               # Mongoose models (Event, User, ContentItem, Analytics)
│       ├── controllers/          # Route handlers & business logic
│       ├── routes/               # Express routes definition
│       ├── middleware/           # Auth, Cache, Audit, CORS
│       ├── services/             # Email, Sync, Checksum
│       ├── utils/                # Helpers
│       └── server.ts             # Entry point
│
├── backoffice/                   # React Admin Dashboard
│   └── src/
│       ├── pages/                # Dashboard, Analytics, Artists, Partners, Speakers
│       ├── components/           # Reusable React components
│       ├── hooks/                # Custom hooks (CRUD, Auth, Export)
│       ├── services/             # API clients (Axios)
│       ├── context/              # React Context (Auth)
│       └── App.tsx               # Entry point
│
├── scripts/                      # Automation & deployment scripts
│   ├── admin/                    # Admin creation scripts
│   ├── preview/                  # Flutter preview build scripts
│   └── migration/                # Data migration scripts
│
└── docs/                         # Documentation complète
    ├── INDEX.md                  # Navigation principale
    ├── ARCHITECTURE.md           # Architecture technique
    ├── API_REFERENCE.md          # API endpoints complets
    ├── DEPLOYMENT.md             # Guide déploiement
    └── WORKFLOWS.md              # Workflows utilisateur
```

---

## 5. Conventions de Code

### Général
- **Langue**: Code et commentaires en anglais, documentation en français
- **Indentation**: 2 espaces
- **Quotes**: Single quotes pour JS/TS, double quotes pour Dart
- **Semicolons**: Obligatoires en TypeScript, optionnels en Dart

### Naming Conventions
- **Variables/Functions**: camelCase (`getUserById`, `eventData`)
- **Classes/Models**: PascalCase (`ContentItem`, `EventProvider`)
- **Constants**: UPPER_SNAKE_CASE (`API_BASE_URL`, `MAX_RETRY_COUNT`)
- **Files**: kebab-case pour composants (`event-card.tsx`), PascalCase pour models (`ContentItem.model.ts`)
- **API Routes**: kebab-case (`/api/activity-logs`)

### TypeScript
- Types explicites pour paramètres et retours de fonction
- Interfaces pour objets complexes (préfixe `I` optionnel)
- Eviter `any`, utiliser `unknown` si nécessaire

### React
- Functional components + Hooks
- Props destructuring
- Custom hooks préfixés par `use` (`useEvents`, `useAuth`)

### Flutter/Dart
- Widgets en PascalCase
- Private members préfixés par `_`
- Async/await pour opérations asynchrones

---

## 6. Tests Utilisés

### Backend
- **Framework**: Jest
- **Coverage**: 17 suites, 352 tests passing
- **Types**: Unit tests, Integration tests
- **Command**: `npm test`

### Frontend (Backoffice)
- **Framework**: Vitest (configuré mais tests à compléter)
- **Command**: `npm run test`

### Flutter
- **Framework**: Flutter Test
- **Command**: `flutter test`

### Tests d'API
- Postman collections disponibles
- Tests manuels via curl

---

## 7. Patterns & Architecture

### Architecture Globale
- **Pattern**: Multi-Tier (Mobile → API → Database)
- **Communication**: REST API (JSON)
- **Auth**: JWT Bearer Token

### Backend
- **Pattern**: MVC-like (Routes → Controllers → Models)
- **Middleware Chain**: Auth → Audit → Cache → Controller
- **Repository Pattern**: Mongoose models as repositories
- **Service Layer**: Business logic séparée (EmailService, SyncService)

### Frontend (Backoffice)
- **Pattern**: Component-based architecture
- **State Management**: React Context (Auth) + Local state
- **Custom Hooks**: Data fetching & CRUD operations
- **API Layer**: Centralisé dans `services/`

### Mobile (Flutter)
- **Pattern**: Provider pattern (State management)
- **Architecture**: Services → Providers → Pages → Widgets
- **Offline-First**: Local data sync avec backend

### Key Design Patterns
- **Multi-Tenant Isolation**: Toutes les queries filtrées par `eventId`
- **Unified Content Model**: `ContentItem` (type: artist/partner/speaker)
- **Audit Logging**: Middleware automatique sur routes CRUD
- **Caching Strategy**: Redis pour events & content items
- **Batch Analytics**: Envoi intelligent selon connectivité

---

## 8. Règles Métier Importantes

### Multi-Tenancy
- **Isolation stricte** par `eventId` sur TOUS les modèles
- Chaque requête DOIT filtrer par `eventId`
- Validation côté backend pour empêcher accès cross-event

### Rôles & Permissions
```
super-admin:
  - Accès à TOUS les events
  - Gestion utilisateurs
  - Configuration globale

admin:
  - Accès à SON event uniquement
  - CRUD sur artists/partners/speakers de son event
  - Vue analytics de son event

client:
  - Lecture seule
  - Consultation de son event
```

### ContentItem Unifié
- **Plus de collections séparées** Artist/Partner/Speaker
- **Un seul modèle**: `ContentItem` avec champ `type`
- Migration complète effectuée
- Endpoints distincts (`/api/artists`, `/api/partners`) mais même collection

### Analytics
- **10 types d'events** trackés (app_open, favorite_add, page_view, etc.)
- **Batch intelligent**: 30min WiFi, 1h mobile data
- Stockage MongoDB avec indexes sur eventId + timestamp
- Export CSV disponible

### Preview System
- Build Flutter Web par event
- Un build = un dossier `/var/www/eventmigo-previews/builds/{eventId}/`
- Accessible via `api.eventmigo.com/preview/{eventId}/`
- Service Worker cache (vider si données incorrectes)

### Sync & Data Integrity
- Checksum validation sur sync mobile
- Timestamps `createdAt` / `updatedAt` automatiques
- Soft delete avec champ `isActive`

---

## 9. Contraintes

### Performance
- **Cache Redis**: TTL 1h pour events/content items
- **Indexes MongoDB**: eventId, type, timestamps
- **Analytics Batch**: Réduction appels API mobile (30min min)
- **Lazy Loading**: Pagination sur listes longues (artists, logs)
- **Service Worker**: Cache agressif sur preview builds

### Sécurité
- **JWT**: Expiration 7 jours, secret robuste
- **CORS**: Whitelist strict (backoffice + production domains)
- **Input Validation**: Joi schemas sur toutes les routes
- **XSS Protection**: Sanitization des inputs utilisateur
- **Rate Limiting**: Protection contre brute force (à implémenter)
- **MongoDB Injection**: Mongoose sanitization automatique
- **Audit Trail**: Logs de toutes actions CRUD

### Scalabilité
- **Multi-Tenant**: Isolation complète par event
- **Stateless API**: Horizontal scaling possible
- **Redis Cache**: Réduction charge MongoDB
- **PM2 Cluster**: Multiple workers en production
- **Preview Isolation**: Builds séparés par event

### Disponibilité
- **PM2**: Auto-restart on crash
- **Nginx**: Load balancing + reverse proxy
- **Health Checks**: `/api/health` endpoint
- **Logs**: PM2 logs + Winston (à configurer)
- **Backup**: MongoDB daily backups (à vérifier)

### Contraintes Techniques
- **Flutter Build**: Utilisateur `alina` avec sudo, path custom
- **CORS Nginx**: Regex location doit inclure TOUS les endpoints
- **MongoDB ObjectId**: Validation stricte des IDs
- **Preview Cache**: Invalidation manuelle nécessaire parfois

---

## Commandes Rapides

```bash
# Backend
cd backend && npm run dev          # Dev mode (port 3000)
cd backend && npm test             # Run tests
cd backend && npm run build        # Production build

# Backoffice
cd backoffice && npm run dev       # Dev mode (port 5173)
cd backoffice && npm run build     # Production build

# Flutter
flutter pub get                    # Install deps
flutter run                        # Run on device
flutter build apk                  # Android build
flutter build web --release        # Web build

# Production
ssh root@eventmigo.com
pm2 status
pm2 logs eventmigo-api --lines 100
pm2 restart eventmigo-api

# Database
mongosh eventmigo
redis-cli KEYS "*"
```

---

## Endpoints API Critiques

```
POST   /api/auth/login
POST   /api/auth/forgot-password
GET    /api/events
GET    /api/artists?eventId=X
GET    /api/partners?eventId=X
GET    /api/speakers?eventId=X
POST   /api/analytics/batch
GET    /api/analytics/stats/:eventId
GET    /api/activity-logs
GET    /api/flutter/export/:eventId
```

---

## Notes pour Prompts Futurs

1. **Toujours spécifier l'eventId** dans les queries
2. **ContentItem est unifié** - ne pas créer de collections séparées
3. **Preview cache** - penser à invalider Service Worker
4. **Multi-tenant** - vérifier isolation sur toute nouvelle feature
5. **Audit logs** - ajouter middleware `auditLog()` sur routes CRUD
6. **Tests** - maintenir coverage sur nouvelles features
7. **CORS Nginx** - mettre à jour regex si nouveau endpoint
8. **Documentation** - mettre à jour docs/ après changements majeurs

---

**Dernière mise à jour**: 2025-12-08
**Version**: 1.13.3+62
