# PromptForge - Assets Graphiques

## Vue d'ensemble

L'iconographie de PromptForge représente une **forge moderne** où les prompts sont "forgés" et transformés. Le design combine :
- 🔨 **Marteau** : L'outil de transformation
- ⚒️ **Enclume** : La base solide du processus
- 🔥 **Étincelles** : L'énergie créative et l'amélioration
- `<>` **Chevrons** : Le symbole du code/prompt

---

## Fichiers disponibles

### Icônes principales

| Fichier | Taille | Usage |
|---------|--------|-------|
| `icon.svg` | 512×512 | Icône principale vectorielle |
| `favicon.svg` | 64×64 | Favicon et petits formats |
| `logo-full.svg` | 512×512 | Logo complet avec texte |

### Formats recommandés à générer

```
assets/
├── icon.svg           # Source vectorielle
├── favicon.svg        # Favicon source
├── logo-full.svg      # Logo avec texte
├── icon-512.png       # PNG haute résolution
├── icon-256.png       # PNG moyenne résolution
├── icon-128.png       # PNG pour apps
├── icon-64.png        # PNG pour petits usages
├── icon-32.png        # Favicon PNG
├── favicon.ico        # Favicon multi-résolution
└── logo-banner.png    # Bannière pour README
```

---

## Palette de couleurs

### Couleurs principales

| Nom | HEX | RGB | Usage |
|-----|-----|-----|-------|
| **Forge Orange** | `#FF6B35` | rgb(255, 107, 53) | Accent principal, feu |
| **Spark Yellow** | `#FFDD00` | rgb(255, 221, 0) | Étincelles |
| **Ember Orange** | `#FF4D00` | rgb(255, 77, 0) | Base du feu |
| **Glow Gold** | `#FFB347` | rgb(255, 179, 71) | Lueur chaude |

### Couleurs métalliques

| Nom | HEX | RGB | Usage |
|-----|-----|-----|-------|
| **Steel Dark** | `#1F1F1F` | rgb(31, 31, 31) | Ombres marteau |
| **Steel Medium** | `#3D3D3D` | rgb(61, 61, 61) | Corps enclume |
| **Steel Light** | `#5A5A5A` | rgb(90, 90, 90) | Highlights |
| **Steel Bright** | `#7A7A7A` | rgb(122, 122, 122) | Reflets |

### Couleurs de fond

| Nom | HEX | RGB | Usage |
|-----|-----|-----|-------|
| **Night Blue** | `#1A1A2E` | rgb(26, 26, 46) | Fond principal |
| **Deep Blue** | `#16213E` | rgb(22, 33, 62) | Fond dégradé |
| **Pure White** | `#FFFFFF` | rgb(255, 255, 255) | Texte, étincelles |

---

## Spécifications techniques

### Structure des couches (icon.svg)

```
1. forge-glow     - Lueur de fond (ellipses orangées)
2. anvil          - Enclume (path + rect)
3. prompt-element - Chevrons <> sur l'enclume
4. hammer         - Marteau (rotation -35°)
5. sparks         - Étincelles et traînées
```

### Effets appliqués

- **Glow filter** : Flou gaussien (3px) sur les étincelles
- **Drop shadow** : Ombre portée (dx:2, dy:4, blur:4)
- **Gradients** : Dégradés linéaires pour profondeur

### Accessibilité

- Ratio de contraste texte/fond : **7.2:1** ✓ (AAA)
- Ratio de contraste icône/fond : **5.1:1** ✓ (AA)
- Lisible jusqu'à 16×16 pixels (favicon simplifié)

---

## Génération des PNG

### Option 1 : Avec Inkscape (recommandé)

```bash
# Installation
# Ubuntu: sudo apt install inkscape
# Mac: brew install inkscape
# Windows: https://inkscape.org/release/

# Génération des PNG
inkscape assets/icon.svg --export-type=png --export-filename=assets/icon-512.png -w 512 -h 512
inkscape assets/icon.svg --export-type=png --export-filename=assets/icon-256.png -w 256 -h 256
inkscape assets/icon.svg --export-type=png --export-filename=assets/icon-128.png -w 128 -h 128
inkscape assets/icon.svg --export-type=png --export-filename=assets/icon-64.png -w 64 -h 64
inkscape assets/icon.svg --export-type=png --export-filename=assets/icon-32.png -w 32 -h 32

# Logo complet
inkscape assets/logo-full.svg --export-type=png --export-filename=assets/logo-banner.png -w 1024 -h 1024
```

### Option 2 : Avec Python (cairosvg)

```bash
pip install cairosvg Pillow

python scripts/generate_icons.py
```

### Option 3 : En ligne

1. Ouvrir le SVG sur [svgtopng.com](https://svgtopng.com/)
2. Sélectionner les tailles souhaitées
3. Télécharger les PNG

---

## Utilisation

### Dans le README

```markdown
<p align="center">
  <img src="assets/logo-full.svg" alt="PromptForge" width="400">
</p>
```

### Comme favicon HTML

```html
<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="assets/icon-32.png">
```

### Dans le launcher Python

```python
# Encodage base64 du SVG pour intégration
import base64

with open("assets/favicon.svg", "r") as f:
    svg_content = f.read()
    b64 = base64.b64encode(svg_content.encode()).decode()
    data_uri = f"data:image/svg+xml;base64,{b64}"
```

---

## Variantes suggérées

### Mode clair (non implémenté)
- Fond : `#F5F5F5`
- Métaux : Plus clairs
- Étincelles : Identiques

### Monochrome
- Tout en blanc sur fond transparent
- Pour watermarks et impressions

### Animé (CSS)
- Étincelles qui scintillent
- Marteau qui frappe (keyframes)

---

## Licence

Les assets graphiques de PromptForge sont sous licence **MIT**, comme le reste du projet.
Vous pouvez les utiliser, modifier et redistribuer librement.

---

## Crédits

Icône conçue pour le projet PromptForge
Design : Moderne, minimaliste, tech-forge
