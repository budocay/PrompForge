"""
Assets for PromptForge web interface.
Contains SVG logos, CSS styles, and visual constants.
"""

# Logo SVG inline pour l'interface
LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="40" height="40" style="vertical-align: middle; margin-right: 10px;">
  <defs>
    <linearGradient id="fire" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" style="stop-color:#ff4d00"/>
      <stop offset="100%" style="stop-color:#ffb347"/>
    </linearGradient>
    <linearGradient id="metal" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#5a5a5a"/>
      <stop offset="100%" style="stop-color:#2d2d2d"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="12" fill="#1a1a2e"/>
  <ellipse cx="32" cy="50" rx="18" ry="6" fill="#ff6b35" opacity="0.4"/>
  <path d="M18 48 L22 40 L42 40 L46 48 Z" fill="url(#metal)"/>
  <rect x="20" y="36" width="24" height="6" rx="1" fill="#4a4a4a"/>
  <path d="M26 38 L22 42 L26 46" stroke="#ff6b35" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M38 38 L42 42 L38 46" stroke="#ff6b35" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <g transform="rotate(-40, 40, 24)">
    <rect x="36" y="18" width="4" height="24" rx="1" fill="#3d3d3d"/>
    <rect x="30" y="12" width="16" height="8" rx="2" fill="#4a4a4a"/>
  </g>
  <circle cx="28" cy="30" r="2" fill="#ffdd00"/>
  <circle cx="36" cy="28" r="2" fill="#ffaa00"/>
  <circle cx="24" cy="34" r="1.5" fill="#ff8800"/>
  <circle cx="40" cy="32" r="1.5" fill="#ffcc00"/>
</svg>'''

# Favicon base64 pour l'onglet du navigateur
FAVICON_B64 = "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4KICA8ZGVmcz4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZmlyZSIgeDE9IjAlIiB5MT0iMTAwJSIgeDI9IjAlIiB5Mj0iMCUiPgogICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdHlsZT0ic3RvcC1jb2xvcjojZmY0ZDAwIi8+CiAgICAgIDxzdG9wIG9mZnNldD0iMTAwJSIgc3R5bGU9InN0b3AtY29sb3I6I2ZmYjM0NyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0ibWV0YWwiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4KICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3R5bGU9InN0b3AtY29sb3I6IzVhNWE1YSIvPgogICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiMyZDJkMmQiLz4KICAgIDwvbGluZWFyR3JhZGllbnQ+CiAgPC9kZWZzPgogIDxyZWN0IHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgcng9IjEyIiBmaWxsPSIjMWExYTJlIi8+CiAgPGVsbGlwc2UgY3g9IjMyIiBjeT0iNTAiIHJ4PSIxOCIgcnk9IjYiIGZpbGw9IiNmZjZiMzUiIG9wYWNpdHk9IjAuNCIvPgogIDxwYXRoIGQ9Ik0xOCA0OCBMMjIgNDAgTDQyIDQwIEw0NiA0OCBaIiBmaWxsPSJ1cmwoI21ldGFsKSIvPgogIDxyZWN0IHg9IjIwIiB5PSIzNiIgd2lkdGg9IjI0IiBoZWlnaHQ9IjYiIHJ4PSIxIiBmaWxsPSIjNGE0YTRhIi8+CiAgPHBhdGggZD0iTTI2IDM4IEwyMiA0MiBMMjYgNDYiIHN0cm9rZT0iI2ZmNmIzNSIgc3Ryb2tlLXdpZHRoPSIyLjUiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgogIDxwYXRoIGQ9Ik0zOCAzOCBMNDIgNDIgTDM4IDQ2IiBzdHJva2U9IiNmZjZiMzUiIHN0cm9rZS13aWR0aD0iMi41IiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KICA8ZyB0cmFuc2Zvcm09InJvdGF0ZSgtNDAsIDQwLCAyNCkiPgogICAgPHJlY3QgeD0iMzYiIHk9IjE4IiB3aWR0aD0iNCIgaGVpZ2h0PSIyNCIgcng9IjEiIGZpbGw9IiMzZDNkM2QiLz4KICAgIDxyZWN0IHg9IjMwIiB5PSIxMiIgd2lkdGg9IjE2IiBoZWlnaHQ9IjgiIHJ4PSIyIiBmaWxsPSIjNGE0YTRhIi8+CiAgPC9nPgogIDxjaXJjbGUgY3g9IjI4IiBjeT0iMzAiIHI9IjIiIGZpbGw9IiNmZmRkMDAiLz4KICA8Y2lyY2xlIGN4PSIzNiIgY3k9IjI4IiByPSIyIiBmaWxsPSIjZmZhYTAwIi8+CiAgPGNpcmNsZSBjeD0iMjQiIGN5PSIzNCIgcj0iMS41IiBmaWxsPSIjZmY4ODAwIi8+CiAgPGNpcmNsZSBjeD0iNDAiIGN5PSIzMiIgcj0iMS41IiBmaWxsPSIjZmZjYzAwIi8+Cjwvc3ZnPg=="

# CSS personnalisé pour le header et le rendu Markdown
CUSTOM_CSS = """
.logo-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}
.logo-header h1 {
    margin: 0;
    background: linear-gradient(90deg, #ffffff, #ff6b35);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.logo-header svg {
    flex-shrink: 0;
}

/* Amélioration du rendu Markdown */
.prose h1, .prose h2, .prose h3, .prose h4 {
    color: #ff6b35 !important;
    margin-top: 1em !important;
    margin-bottom: 0.5em !important;
}
.prose h1 { font-size: 1.8em !important; border-bottom: 2px solid #ff6b35; padding-bottom: 0.3em; }
.prose h2 { font-size: 1.5em !important; border-bottom: 1px solid rgba(255,107,53,0.3); padding-bottom: 0.2em; }
.prose h3 { font-size: 1.2em !important; }

.prose ul, .prose ol {
    margin-left: 1.5em !important;
    margin-bottom: 1em !important;
}
.prose li {
    margin-bottom: 0.3em !important;
}

.prose code {
    background: rgba(255,107,53,0.15) !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 0.9em !important;
}

.prose pre {
    background: rgba(0,0,0,0.3) !important;
    border: 1px solid rgba(255,107,53,0.2) !important;
    border-radius: 8px !important;
    padding: 1em !important;
    overflow-x: auto !important;
}

.prose table {
    width: 100% !important;
    border-collapse: collapse !important;
    margin: 1em 0 !important;
}
.prose th, .prose td {
    border: 1px solid rgba(255,255,255,0.2) !important;
    padding: 8px 12px !important;
    text-align: left !important;
}
.prose th {
    background: rgba(255,107,53,0.2) !important;
    font-weight: bold !important;
}
.prose tr:nth-child(even) {
    background: rgba(255,255,255,0.05) !important;
}

.prose blockquote {
    border-left: 4px solid #ff6b35 !important;
    padding-left: 1em !important;
    margin-left: 0 !important;
    color: #aaa !important;
    font-style: italic !important;
}

.prose hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, #ff6b35, transparent) !important;
    margin: 1.5em 0 !important;
}

.prose strong {
    color: #ff6b35 !important;
}
"""

# Constante pour identifier l'option "sans projet"
SANS_PROJET = "🔧 Sans projet (prompt seul)"

# Template pour générer une configuration projet
PROJECT_GENERATOR_PROMPT = '''# 🎯 Génère ta configuration projet

Copie ce prompt et envoie-le à **Claude**, **ChatGPT** ou ton IA préférée :

```
Je veux créer un fichier de configuration pour mon projet.
Ce fichier servira de contexte pour optimiser mes futurs prompts.

Pose-moi ces questions UNE PAR UNE :

1. Nom du projet ?
2. Description (2-3 phrases) ?
3. Stack technique (langages, frameworks, DB) ?
4. Structure des dossiers ?
5. Conventions de code ?
6. Tests utilisés ?
7. Patterns/architecture ?
8. Règles métier importantes ?
9. Contraintes (perf, sécu) ?

Puis génère un fichier Markdown structuré.
```

💡 **Astuce** : Plus tu donnes de détails, meilleur sera le reformatage !
'''
