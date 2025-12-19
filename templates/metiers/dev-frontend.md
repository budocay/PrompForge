# Configuration Projet - Développeur Frontend

## Mon Profil

**Métier** : Développeur Frontend
**Niveau** : [Junior / Confirmé / Senior / Lead]
**Spécialisation** : [React / Vue / Angular / Mobile / Design System]

---

## Stack Technique

### Framework & Libraries

| Technologie | Version | Usage |
|-------------|---------|-------|
| **React** | 18+ | Framework principal |
| **TypeScript** | 5+ | Typage statique |
| **Next.js** | 14+ | SSR/SSG |
| **TailwindCSS** | 3+ | Styling |
| **Zustand/Redux** | - | State management |
| **React Query** | 5+ | Data fetching |
| **Zod** | - | Validation schemas |
| [Ajouter] | ... | ... |

### Outils de Dev

| Outil | Usage |
|-------|-------|
| **Vite** | Build tool |
| **ESLint** | Linting |
| **Prettier** | Formatting |
| **Vitest** | Tests unitaires |
| **Playwright** | Tests E2E |
| **Storybook** | Documentation composants |

---

## Architecture Projet

### Structure des Dossiers

```
src/
├── app/              # Routes (Next.js App Router)
├── components/       # Composants réutilisables
│   ├── ui/          # Composants primitifs (Button, Input...)
│   └── features/    # Composants métier
├── hooks/           # Custom hooks
├── lib/             # Utilitaires, API client
├── stores/          # State management
├── types/           # TypeScript types/interfaces
└── styles/          # CSS global, tokens
```

### Patterns Utilisés

| Pattern | Usage |
|---------|-------|
| **Compound Components** | Composants complexes |
| **Render Props** | Logique partagée |
| **Custom Hooks** | Réutilisation logique |
| **Container/Presentational** | Séparation concerns |

---

## Design System

### Tokens

| Token | Valeur |
|-------|--------|
| **Primary** | #[couleur] |
| **Secondary** | #[couleur] |
| **Spacing** | 4px base (4, 8, 12, 16, 24, 32, 48) |
| **Border radius** | 4px, 8px, 12px, full |
| **Font** | Inter / System |

### Composants UI

| Composant | Variantes |
|-----------|-----------|
| **Button** | primary, secondary, ghost, danger |
| **Input** | text, password, search, textarea |
| **Card** | default, elevated, outlined |
| **Modal** | default, fullscreen, drawer |

---

## Conventions de Code

### TypeScript

```typescript
// Interfaces pour les props
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}

// Types pour les données
type User = {
  id: string;
  email: string;
  name: string;
};
```

### Naming

| Élément | Convention | Exemple |
|---------|------------|---------|
| **Composants** | PascalCase | `UserCard.tsx` |
| **Hooks** | camelCase + use | `useAuth.ts` |
| **Utils** | camelCase | `formatDate.ts` |
| **Types** | PascalCase | `User`, `ApiResponse` |
| **CSS classes** | kebab-case | `user-card-header` |

---

## Contraintes Projet

### Performance

- LCP < 2.5s
- FID < 100ms
- CLS < 0.1
- Bundle size < 200KB (initial)

### Accessibilité

- WCAG 2.1 AA minimum
- Navigation clavier
- Labels ARIA
- Contraste suffisant

### Responsive

| Breakpoint | Taille |
|------------|--------|
| **Mobile** | < 640px |
| **Tablet** | 640px - 1024px |
| **Desktop** | > 1024px |

---

## Instructions pour le LLM

Quand je demande du code frontend :

1. **Toujours inclure** :
   - TypeScript strict (pas de `any`)
   - Props typées avec interface
   - Accessibilité (aria-*, rôles)
   - Responsive par défaut

2. **Structure composant** :
   ```typescript
   // 1. Imports
   // 2. Types/Interfaces
   // 3. Composant
   // 4. Sous-composants si compound
   // 5. Export
   ```

3. **Styling** :
   - TailwindCSS classes
   - Variants avec CVA si complexe
   - Dark mode support

4. **Format de réponse** :
   - Code complet et fonctionnel
   - Exemple d'utilisation
   - Tests si demandés

---

*Template Développeur Frontend pour PromptForge*
