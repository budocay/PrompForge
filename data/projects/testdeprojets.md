# EventMigo - Configuration de Contexte pour Prompts

> Document de référence complet pour l'optimisation des prompts et le contexte projet.
> **Version**: 1.13.3+62 | **Mise à jour**: 2025-12-09

---

## 1. Identité du Projet

| Attribut | Valeur |
|----------|--------|
| **Nom** | EventMigo |
| **Type** | Plateforme SaaS Multi-Tenant |
| **Domaine** | Gestion d'événements (festivals, conférences, séminaires, salons) |
| **Architecture** | Monorepo (Flutter + Node.js + React) |

### Description

EventMigo est une plateforme SaaS multi-tenant complète permettant de gérer et diffuser des événements. Elle comprend:
- **Application mobile Flutter** pour les participants (iOS, Android, Web)
- **Backend API Node.js** robuste avec analytics et système de sync
- **Backoffice React** pour les organisateurs d'événements

Le système supporte l'isolation complète des données par événement avec gestion des rôles (super-admin, admin, client) et permissions granulaires.

---

## 2. Stack Technique Détaillée

### 2.1 Application Mobile (Flutter)

| Catégorie | Technologies |
|-----------|--------------|
| **Framework** | Flutter >= 3.4, Dart >= 3.4.4 |
| **State Management** | Provider (ConfigProvider, FavoritesProvider, ThemeProvider, StageColorProvider) |
| **Calendar** | Syncfusion Calendar (syncfusion_flutter_calendar: ^31.2.2) |
| **Notifications** | flutter_local_notifications: ^19.0.0, workmanager: ^0.9.0 |
| **HTTP** | http: ^1.2.2 |
| **WebView** | flutter_inappwebview: ^6.1.5, webview_flutter: ^4.10.0 |
| **Cache Images** | CachedArtistImageProvider (pre-cache, zero-flicker) |
| **Storage** | shared_preferences: ^2.5.2, path_provider: ^2.1.5 |
| **UI Extras** | flutter_speed_dial, shimmer, google_fonts, flutter_svg |
| **Crypto** | crypto: ^3.0.3 (checksums MD5) |
| **Connectivity** | connectivity_plus: ^7.0.0 |
| **Device Info** | device_info_plus: ^12.1.0, package_info_plus: ^9.0.0 |
| **Localisation** | intl, flutter_localizations |

**Version App**: 1.13.3+62

### 2.2 Backend API (Node.js)

| Catégorie | Technologies |
|-----------|--------------|
| **Runtime** | Node.js >= 18 |
| **Framework** | Express.js ^4.18.2 |
| **Langage** | TypeScript ^5.3.3 |
| **Database** | MongoDB 7.0 (mongoose: ^8.0.3) |
| **Cache** | Redis 7 (TTL 60s sur 11 endpoints) |
| **Auth** | JWT (jsonwebtoken: ^9.0.2), bcryptjs: ^2.4.3 |
| **Security** | helmet: ^7.1.0, express-rate-limit: ^7.1.5, cors: ^2.8.5 |
| **Validation** | express-validator: ^7.0.1 |
| **Upload** | multer: ^2.0.2, sharp: ^0.34.5 (WebP conversion) |
| **Email** | nodemailer: ^6.9.7 |
| **Archive** | archiver: ^7.0.1 |
| **HTTP Client** | axios: ^1.13.1 |
| **Process Manager** | PM2 (cluster mode, 4 instances) |
| **Tests** | Jest ^29.7.0, Supertest ^6.3.3, mongodb-memory-server |

**Port**: 3000

### 2.3 Backoffice Admin (React)

| Catégorie | Technologies |
|-----------|--------------|
| **Framework** | React 19 |
| **Langage** | TypeScript ~5.9.3 |
| **Build Tool** | Vite 7 |
| **Styling** | TailwindCSS 4 |
| **HTTP Client** | Axios ^1.13.1 |
| **State** | @tanstack/react-query ^5.90.6 |
| **Forms** | react-hook-form ^7.66.0, @hookform/resolvers ^5.2.2 |
| **Validation** | zod ^4.1.12 |
| **Routing** | react-router-dom ^7.9.5 |
| **i18n** | i18next ^25.6.2, react-i18next ^16.3.0 |
| **Charts** | recharts ^3.3.0 |
| **Animations** | framer-motion ^12.23.24 |
| **Maps** | leaflet ^1.9.4, react-leaflet ^5.0.0 |
| **Drag & Drop** | @dnd-kit/core ^6.3.1, @dnd-kit/sortable ^10.0.0 |
| **Icons** | lucide-react ^0.552.0 |
| **QR Code** | qrcode.react ^4.2.0 |
| **Color Picker** | react-colorful ^5.6.1 |
| **Utilities** | date-fns ^4.1.0, clsx ^2.1.1, tailwind-merge ^3.3.1 |

**Port**: 5173

### 2.4 Infrastructure & DevOps

| Catégorie | Détails |
|-----------|---------|
| **Serveur Production** | api.eventmigo.com (195.35.29.9) |
| **OS** | Ubuntu 22.04 LTS |
| **Process Manager** | PM2 cluster (4 instances) |
| **Reverse Proxy** | Nginx |
| **SSL** | Let's Encrypt |
| **CI/CD** | GitLab CI (structure modulaire `ci/*.yml`) |
| **Publication** | Fastlane (Android/iOS) |
| **Docker** | Flutter Web Preview builds |
| **Cache** | Redis 7 |
| **Database** | MongoDB 7.0 |
| **Assets** | `/var/www/eventmigo-assets/` |
| **Previews** | `/var/www/eventmigo-previews/builds/{eventId}/` |

---

## 3. Architecture des Dossiers

```
EventMigo/
│
├── lib/                              # Flutter Mobile App
│   ├── models/                       # Data models
│   │   ├── groupes_model.dart        # Artistes/groupes
│   │   ├── speaker_model.dart        # Speakers (conférences)
│   │   ├── partnershipModel.dart     # Partenaires
│   │   ├── feedback_model.dart       # Feedback sessions
│   │   ├── sync_metadata.dart        # Sync checksums
│   │   ├── visual_assets_config.dart # Assets visuels
│   │   ├── navigation_item.dart      # Navigation dynamique
│   │   └── linkInfo.dart             # Liens sociaux
│   │
│   ├── providers/                    # State Management (Provider)
│   │   ├── config_provider.dart      # Configuration événement
│   │   ├── favorites_provider.dart   # Favoris utilisateur
│   │   ├── theme_provider.dart       # Thème personnalisé
│   │   └── stage_color_provider.dart # Couleurs des scènes
│   │
│   ├── pages/                        # Screens/Views
│   │   ├── home_page_state.dart      # Page d'accueil
│   │   ├── calendarPage.dart         # Calendrier Syncfusion
│   │   ├── group_details.dart        # Détails artiste/speaker
│   │   ├── partnership.dart          # Liste partenaires
│   │   ├── festivalMap.dart          # Carte interactive
│   │   ├── practical_page.dart       # Infos pratiques
│   │   ├── profile_page.dart         # Profil utilisateur
│   │   ├── ticketPage.dart           # Billetterie
│   │   ├── cashless.dart             # Cashless
│   │   └── vssPage.dart              # Violences sexistes
│   │
│   ├── services/                     # Business Logic
│   │   ├── sync_service.dart         # Synchronisation données
│   │   ├── analytics_service.dart    # Tracking analytics
│   │   ├── analytics_batch_manager.dart # Batch analytics
│   │   ├── feedback_service.dart     # Feedback sessions
│   │   ├── feedback_batch_manager.dart # Batch feedback
│   │   ├── smart_notifications_service.dart # Notifications
│   │   ├── sync_notification_service.dart # Sync notifications
│   │   ├── background_sync_manager.dart # Sync background
│   │   ├── image_cache_service.dart  # Cache images
│   │   ├── image_cache_service_mobile.dart
│   │   ├── image_cache_service_web.dart
│   │   ├── visual_assets_service.dart # Assets visuels
│   │   ├── preview_config_service.dart # Config preview
│   │   ├── webview_service.dart      # WebView
│   │   └── error_service.dart        # Gestion erreurs
│   │
│   ├── widgets/                      # Composants réutilisables
│   └── main.dart                     # Entry point
│
├── backend/                          # Node.js API
│   └── src/
│       ├── models/                   # Mongoose Schemas (12 fichiers)
│       │   ├── Event.model.ts        # Événement (multi-tenant root)
│       │   ├── ContentItem.model.ts  # Contenu unifié (artist/speaker/session)
│       │   ├── Partner.model.ts      # Partenaires
│       │   ├── User.model.ts         # Utilisateurs
│       │   ├── Analytics.model.ts    # Analytics events
│       │   ├── Feedback.model.ts     # Feedback sessions
│       │   ├── ActivityLog.model.ts  # Audit trail
│       │   ├── SyncMetadata.model.ts # Métadonnées sync
│       │   ├── FestivalData.model.ts # Données festival
│       │   ├── PreviewCache.model.ts # Cache preview
│       │   ├── PreviewToken.ts       # Tokens preview
│       │   └── PasswordResetToken.model.ts
│       │
│       ├── routes/                   # Express Routes (17 fichiers)
│       │   ├── api.routes.ts         # Routes Mobile (metadata, data, diff)
│       │   ├── auth.routes.ts        # Authentification
│       │   ├── event.routes.ts       # Événements + Stages
│       │   ├── artist.routes.ts      # Artistes
│       │   ├── speaker.routes.ts     # Speakers
│       │   ├── session.routes.ts     # Sessions
│       │   ├── partner.routes.ts     # Partenaires
│       │   ├── analytics.routes.ts   # Analytics
│       │   ├── feedback.routes.ts    # Feedback
│       │   ├── activity-log.routes.ts # Activity Logs
│       │   ├── preview.routes.ts     # Preview System
│       │   ├── flutter-export.routes.ts # Export Flutter
│       │   ├── upload.routes.ts      # Upload images
│       │   ├── visual-assets.routes.ts # Assets visuels
│       │   ├── admin.routes.ts       # Administration
│       │   ├── nominatim.routes.ts   # Geocoding proxy
│       │   └── contentItem.routes.ts # ContentItem générique
│       │
│       ├── middleware/               # Middleware Chain (7 fichiers)
│       │   ├── auth.middleware.ts    # JWT + API Key verification
│       │   ├── permissions.middleware.ts # RBAC
│       │   ├── audit.middleware.ts   # Activity logging
│       │   ├── rateLimit.middleware.ts # Rate limiting
│       │   ├── upload.middleware.ts  # File upload handling
│       │   ├── imageConverter.middleware.ts # WebP conversion
│       │   └── errorHandler.middleware.ts
│       │
│       ├── services/                 # Business Services (5 fichiers)
│       │   ├── sync.service.ts       # Sync + checksums
│       │   ├── checksum.service.ts   # MD5 checksums
│       │   ├── email.service.ts      # SMTP emails
│       │   ├── preview-rebuild.service.ts
│       │   └── logger.service.ts
│       │
│       ├── controllers/              # Route Handlers
│       └── server.ts                 # Entry point
│
├── backoffice/                       # React Admin Dashboard
│   └── src/
│       ├── pages/                    # Pages/Views (27 fichiers)
│       │   ├── Dashboard.tsx
│       │   ├── Analytics.tsx
│       │   ├── SponsorsAnalytics.tsx
│       │   ├── Login.tsx
│       │   ├── ForgotPassword.tsx
│       │   ├── ResetPassword.tsx
│       │   ├── Artists/ (ArtistsList, ArtistForm)
│       │   ├── Speakers/ (SpeakersList, SpeakerForm)
│       │   ├── Sessions/ (SessionsList, SessionForm)
│       │   ├── Partners/ (PartnersList, PartnerForm)
│       │   ├── Stages/ (StagesList, StageForm, StageFormPage)
│       │   ├── Events/ (EventsList, EventForm, EventConfigPage)
│       │   ├── Users/ (UsersList, UserForm)
│       │   ├── Preview/ (PreviewPage, PublicPreviewPage)
│       │   ├── Activity/ (ActivityPage, ActivityPageV2)
│       │   └── Feedback/ (FeedbackDashboard)
│       │
│       ├── hooks/                    # Custom Hooks (16 fichiers)
│       │   ├── useAuth.ts, useEvents.ts, useArtists.ts
│       │   ├── useSpeakers.ts, useSessions.ts, usePartners.ts
│       │   ├── useStages.ts, useUsers.ts, useAnalytics.ts
│       │   ├── useFeedback.ts, useActivityLogs.ts
│       │   ├── usePreviewBuild.ts, useRoles.ts, useTheme.ts
│       │   ├── useEventTerminology.ts, useKeyboardShortcut.ts
│       │
│       ├── services/                 # API Services (14 fichiers)
│       │   ├── api.ts (Axios instance)
│       │   ├── auth, events, artists, speakers, sessions
│       │   ├── partners, stages, users, analytics
│       │   ├── feedback, activity-log, preview, upload
│       │
│       ├── contexts/                 # React Contexts (4 fichiers)
│       │   ├── EventContext.tsx
│       │   ├── ThemeContext.tsx
│       │   ├── DarkModeContext.tsx
│       │   └── ToastContext.tsx
│       │
│       ├── config/theme.config.ts    # Design tokens
│       ├── i18n/locales/ (fr.json, en.json - 1577 lignes chacun)
│       └── types/ (index.ts, session.types.ts)
│
├── ci/                               # GitLab CI/CD Modulaire (7 fichiers)
│   ├── stages.yml, variables.yml
│   ├── flutter.yml, backend-tests.yml, backend-deploy.yml
│   └── backoffice-tests.yml, backoffice-deploy.yml
│
├── android/fastlane/, ios/fastlane/  # Fastlane configs
├── .claude/agents/                   # 6 agents spécialisés
├── docs/                             # Documentation complète
├── CLAUDE.md                         # Instructions Claude Code
└── PROMPT_CONTEXT.md                 # Ce fichier
```

---

## 4. Agents Spécialisés Claude Code

### 4.1 Tableau Récapitulatif

| Agent | Fichier | Domaine | Cas d'usage |
|-------|---------|---------|-------------|
| **Flutter Expert** | `flutter-festival-expert.md` | Mobile | Code Dart, Provider, Calendar, Sync, Analytics |
| **Node.js Architect** | `nodejs-api-architect.md` | Backend | API REST, MongoDB, Redis, JWT, Audit Trail |
| **React Backoffice** | `react-backoffice-expert.md` | Admin | Interface, CRUD, Preview, Feedback |
| **React UI/UX** | `react-ui-ux-expert.md` | Design | Animations, Accessibilité, Dark mode |
| **React Responsive** | `react-responsive-expert.md` | Layout | 320px→8K, TailwindCSS, Grilles |
| **GitLab CI/CD** | `gitlab-cicd-expert.md` | DevOps | Pipelines, Deploy, Fastlane |

### 4.2 Guide de Sélection

```
📱 Flutter App              → flutter-festival-expert
🖥️ Backend API              → nodejs-api-architect
💻 Backoffice React         → react-backoffice-expert
🎨 UI/UX Design             → react-ui-ux-expert
📐 Responsive Design        → react-responsive-expert
🚀 CI/CD Pipeline           → gitlab-cicd-expert
```

---

## 5. API Endpoints Complets

### 5.1 Auth (`/api/auth`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/register` | - | Inscription |
| POST | `/login` | - | Connexion → JWT |
| POST | `/request-password-reset` | - | Demande reset |
| POST | `/reset-password` | - | Reset password |
| GET | `/verify-reset-token` | - | Vérifier token |
| GET | `/me` | JWT | Utilisateur courant |
| PATCH | `/me` | JWT | Modifier profil |
| POST | `/create-client` | JWT+Admin | Créer client |

### 5.2 Events (`/api/events`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/` | JWT | Créer |
| GET | `/` | JWT | Liste |
| GET | `/:id` | JWT | Détails |
| GET | `/slug/:slug` | JWT | Par slug |
| PUT | `/:id` | JWT | Modifier |
| DELETE | `/:id` | JWT | Supprimer |
| POST | `/:id/stages` | JWT | Ajouter scène |
| PUT | `/:id/stages/:stageName` | JWT | Modifier scène |
| DELETE | `/:id/stages/:stageName` | JWT | Supprimer scène |

### 5.3 Artists (`/api/artists`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/` | JWT | Créer |
| GET | `/` | JWT | Liste (?eventId=X) |
| GET | `/by-stage` | JWT | Par scène |
| GET | `/by-date` | JWT | Par date |
| GET | `/:id` | JWT | Détails |
| PUT | `/:id` | JWT | Modifier |
| DELETE | `/:id` | JWT | Supprimer |

### 5.4 Speakers (`/api/speakers`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/` | JWT | Créer |
| GET | `/` | JWT | Liste (?eventId=X) |
| GET | `/by-location` | JWT | Par salle |
| GET | `/by-date` | JWT | Par date |
| GET | `/:id` | JWT | Détails |
| PUT | `/:id` | JWT | Modifier |
| DELETE | `/:id` | JWT | Supprimer |

### 5.5 Sessions (`/api/sessions`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/` | JWT | Créer |
| GET | `/` | JWT | Liste (?eventId=X) |
| GET | `/by-room` | JWT | Par salle |
| GET | `/by-track` | JWT | Par track |
| GET | `/by-date` | JWT | Par date |
| GET | `/:id` | JWT | Détails |
| PUT | `/:id` | JWT | Modifier |
| DELETE | `/:id` | JWT | Supprimer |

### 5.6 Partners (`/api/partners`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/` | JWT | Créer |
| GET | `/` | JWT | Liste (?eventId=X) |
| GET | `/by-category` | JWT | Par catégorie |
| GET | `/:id` | JWT | Détails |
| PUT | `/:id` | JWT | Modifier |
| DELETE | `/:id` | JWT | Supprimer |

### 5.7 Analytics (`/api/analytics`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/track` | API Key | Track événement |
| POST | `/batch` | API Key | Track batch |
| GET | `/stats/:eventId` | JWT | Stats KPIs |
| GET | `/sponsors/:eventId` | JWT | Stats sponsors |
| GET | `/export/:eventId` | JWT | Export CSV |
| DELETE | `/event/:eventId` | JWT+SuperAdmin | Supprimer |

### 5.8 Feedback (`/api/feedback`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/track` | API Key | Soumettre |
| POST | `/batch` | API Key | Batch |
| GET | `/stats/:eventId` | JWT | Stats NPS |
| GET | `/list/:eventId` | JWT | Liste paginée |
| GET | `/export/:eventId` | JWT | Export CSV |

### 5.9 Activity Logs (`/api/activity-logs`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/` | JWT+Admin | Liste paginée |
| GET | `/stats` | JWT+Admin | Statistiques |
| GET | `/export` | JWT+Admin | Export CSV |
| GET | `/entity/:entityType/:entityId` | JWT+Admin | Historique entité |
| GET | `/user/:userId` | JWT+Admin | Activité user |
| DELETE | `/:id` | JWT+SuperAdmin | Soft delete |

### 5.10 Preview (`/api/preview`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/generate-share-link` | JWT | Générer lien |
| POST | `/generate/:eventId` | JWT | Générer preview |
| DELETE | `/revoke/:tokenId` | JWT | Révoquer lien |
| GET | `/links/:eventId` | JWT | Liste liens |
| GET | `/flutter-auth/:eventId` | JWT | Auth Flutter |
| GET | `/:eventId/status` | JWT | Status build |
| POST | `/:eventId/build` | JWT | Trigger build |
| DELETE | `/:eventId` | JWT | Supprimer cache |
| GET | `/public/:eventId/:shareToken` | - | Preview public |
| GET | `/flutter/:eventId/:shareToken` | - | Preview Flutter |

### 5.11 Flutter Export (`/api/flutter`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/export/:eventId` | JWT | Export ZIP |
| GET | `/export/:eventId/config` | JWT | Export config |
| GET | `/info/:eventId` | JWT | Info export |
| GET | `/internal/export/:eventId` | localhost | Export interne |
| GET | `/internal/export/:eventId/config` | localhost | Config interne |

### 5.12 Upload (`/api/upload`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/` | JWT | Upload générique |
| POST | `/artist-image` | JWT | Image artiste |
| POST | `/partner-logo` | JWT | Logo partenaire |
| POST | `/poster` | JWT | Affiche |
| POST | `/misc` | JWT | Divers |
| GET | `/:eventId/:category` | JWT | Liste fichiers |
| DELETE | `/:eventId/:category/:filename` | JWT | Supprimer |

### 5.13 Visual Assets (`/api/visual-assets`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/:eventId/:assetType/upload` | JWT+Admin | Upload asset |
| DELETE | `/:eventId/:assetType` | JWT+Admin | Supprimer |
| GET | `/:eventId/config` | - | Config (public) |
| PUT | `/:eventId/options` | JWT+Admin | Options visuelles |

### 5.14 Admin (`/api/admin`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/data` | JWT+Admin | Créer/modifier artiste |
| DELETE | `/data/:name` | JWT+Admin | Soft delete artiste |
| GET | `/data` | JWT+Admin | Liste artistes |
| GET | `/users` | JWT+Admin | Liste users |
| GET | `/users/:id` | JWT+Admin | Détails user |
| POST | `/users` | JWT+Admin | Créer user |
| PUT | `/users/:id` | JWT+Admin | Modifier user |
| DELETE | `/users/:id` | JWT+Admin | Supprimer user |

### 5.15 Mobile API (`/api`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/metadata` | API Key | Métadonnées sync |
| GET | `/data` | API Key | Données complètes |
| GET | `/diff` | API Key | Différentiel sync |
| GET | `/partners` | API Key | Partenaires |

### 5.16 Nominatim (`/api/nominatim`)
| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/search` | JWT | Recherche adresse OSM |

---

## 6. Modèles de Données Clés

### 6.1 Event
```typescript
{
  name, slug, eventType, terminology, logo,
  year, month, monthName, startDay, endDay, days[],
  location: { name, address, city, lat, lng },
  stages: [{ name, color, image, icon, description }],
  primaryColor, secondaryColor, accentColor,
  features: { enableLineUp, enableCalendar, enableMap, ... },
  notifications: { reminderMinutes, enableDailyDigest, ... },
  urls: { website, tickets, instagram, ... },
  visualAssets?: { logo, backgrounds, appBar, splashScreen },
  content?: { description, ecoContent, ... },
  apiKey, createdAt, updatedAt
}
```

### 6.2 ContentItem (Unifié)
```typescript
{
  eventId, contentType: 'artist'|'speaker'|'session'|...,
  name, description, location, startTime, endTime,
  imagePath, videoUrl,
  metadata: { artist?, speaker?, session?, ... },
  favoriteCount, viewCount, order,
  isDeleted, version, createdAt, updatedAt
}
```

### 6.3 User
```typescript
{
  name, email, password (hashed),
  role: 'super-admin'|'admin'|'client',
  eventId?, isActive, lastLogin,
  createdAt, updatedAt
}
```

### 6.4 Analytics
```typescript
{
  eventId, eventType, artistId?, partnerId?,
  deviceId, deviceOs, deviceModel, appVersion,
  sessionId, metadata, timestamp
}
```

### 6.5 ActivityLog
```typescript
{
  eventId?, userId, userName, userEmail,
  action: 'CREATE'|'UPDATE'|'DELETE',
  entityType, entityId, entityName,
  changes?, beforeState?, afterState?,
  ipAddress, userAgent, isDeleted, createdAt
}
```

---

## 7. Conventions de Code

### Naming
| Type | Convention | Exemple |
|------|------------|---------|
| Variables/Functions | camelCase | `getUserById` |
| Classes/Models | PascalCase | `ContentItem` |
| Constants | UPPER_SNAKE_CASE | `API_BASE_URL` |
| Components | PascalCase | `ArtistsList.tsx` |
| Hooks | use + camelCase | `useAuth.ts` |
| API routes | kebab-case | `/activity-logs` |

### TypeScript
- Types explicites obligatoires
- Éviter `any`, préférer `unknown`
- Strict mode activé

### React
- Functional components uniquement
- `useTranslation()` pour tout texte
- `getSectionColor()` pour couleurs
- `dark:*` classes pour dark mode

---

## 8. Variables d'Environnement

### Backend (.env)
```bash
NODE_ENV, PORT, MONGODB_URI
API_KEY, JWT_SECRET, JWT_EXPIRES_IN
CORS_ORIGIN, RATE_LIMIT_*
REDIS_HOST, REDIS_PORT
UPLOAD_BASE_PATH, CDN_BASE_URL, PREVIEWS_PATH
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
FRONTEND_URL
```

### CI/CD (GitLab)
```
SSH_PRIVATE_KEY, DEPLOY_HOST, DEPLOY_USER
KEYSTORE_BASE64, STORE_PASSWORD, KEY_PASSWORD, KEY_ALIAS
GOOGLE_PLAY_JSON_KEY
APPLE_API_KEY_ID, APPLE_API_ISSUER_ID, APPLE_API_KEY_CONTENT
APPLE_TEAM_ID, MATCH_GIT_URL, MATCH_PASSWORD
```

---

## 9. Commandes Rapides

```bash
# Backend
cd backend && npm run dev    # Dev (3000)
cd backend && npm test       # Tests (17 suites, 352 tests)
cd backend && npm run build  # Build

# Backoffice
cd backoffice && npm run dev   # Dev (5173)
cd backoffice && npm run build # Build + TypeScript

# Flutter
flutter run                    # Run
flutter build apk --release    # Android APK
flutter build web --release    # Web
flutter test                   # Tests

# Production
ssh root@eventmigo.com
pm2 status / logs / restart eventmigo-api

# Fastlane
cd android && bundle exec fastlane internal
cd ios && bundle exec fastlane testflight
```

---

## 10. Règles Critiques

1. **Multi-Tenant**: Toujours filtrer par `eventId`
2. **ContentItem unifié**: Pas de nouvelle collection séparée
3. **Audit**: `auditLog()` sur routes CRUD
4. **Traductions**: fr.json ET en.json synchronisés
5. **Theme**: `getSectionColor()` pas de couleurs hardcodées
6. **Dark mode**: `dark:*` classes sur composants visuels
7. **Tests**: Maintenir coverage
8. **CORS Nginx**: Mettre à jour regex si nouvel endpoint

---

## 11. Fichiers Clés

| Fichier | Usage |
|---------|-------|
| `CLAUDE.md` | Instructions Claude Code |
| `PROMPT_CONTEXT.md` | Ce fichier |
| `.claude/agents/*.md` | 6 agents spécialisés |
| `theme.config.ts` | Design tokens |
| `tailwind.config.js` | Config Tailwind |
| `fr.json` / `en.json` | Traductions (1577 lignes) |
| `ci/stages.yml` | GitLab CI stages |
| `docs/PUBLISHING_GUIDE.md` | Publication stores |

---

**Version**: 1.13.3+62 | **Tests**: 17 suites, 352 passing | **Traductions**: 1577 lignes
**Dernière mise à jour**: 2025-12-09
