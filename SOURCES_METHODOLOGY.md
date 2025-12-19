# 📊 PromptForge - Sources des Benchmarks & Méthodologie

Ce document détaille les sources utilisées pour les recommandations de modèles et explique la méthodologie de calcul des scores.

---

## 📚 Sources Officielles

### Anthropic (Claude)

| Source | URL | Date |
|--------|-----|------|
| Claude Opus 4.5 Announcement | https://www.anthropic.com/news/claude-opus-4-5 | Nov 2025 |
| Claude Opus 4.5 Model Card | https://www.anthropic.com/claude/opus | Nov 2025 |

**Benchmarks clés:**
- **SWE-bench Verified:** 80.9% (leader industrie)
- **Terminal-Bench 2.0:** 59.3%
- **OSWorld (computer use):** 66.3%
- **Safety:** ASL-3 (Advanced Safety Level 3)

---

### OpenAI (GPT-5)

| Source | URL | Date |
|--------|-----|------|
| Introducing GPT-5 | https://openai.com/index/introducing-gpt-5/ | Août 2025 |
| HealthBench Paper | https://arxiv.org/abs/2505.08775 | Mai 2025 |
| HealthBench Announcement | https://openai.com/index/healthbench/ | Mai 2025 |

**Benchmarks clés:**
- **HealthBench Hard:** 46.2% (SOTA médical)
- **Hallucinations:** -45% vs GPT-4
- **AIME 2025:** 94.6% (sans tools)
- **GPQA Diamond:** 88.4%

**HealthBench - Méthodologie:**
- 5,000 conversations médicales réalistes
- 262 médecins de 60 pays
- 48,562 critères d'évaluation uniques

---

### Google (Gemini 3)

| Source | URL | Date |
|--------|-----|------|
| Gemini 3 Announcement | https://blog.google/products/gemini/gemini-3/ | Nov 2025 |
| Gemini 3 Pro Model Card | https://deepmind.google/models/gemini/pro/ | Nov 2025 |

**Benchmarks clés:**
- **GPQA Diamond:** 91.9% (leader PhD-level)
- **AIME 2025:** 95-100%
- **MathArena Apex:** 23.4% (leader)
- **Contexte:** 1M tokens
- **LMArena Leaderboard:** 1501 Elo

---

## 🏆 Benchmarks de Référence

### SWE-bench Verified (Code)

**Description:** Évalue la capacité à résoudre de vrais bugs provenant de repositories GitHub populaires.

**Source:** https://www.swebench.com/

**Scores (Novembre 2025):**

| Modèle | Score |
|--------|-------|
| Claude Opus 4.5 | **80.9%** 👑 |
| GPT-5.1 Codex Max | 77.9% |
| Claude Sonnet 4.5 | 77.2% |
| GPT-5.1 | 76.3% |
| Gemini 3 Pro | 76.2% |

**Pourquoi c'est pertinent:** Ce benchmark mesure la capacité réelle à corriger du code dans des contextes professionnels, pas juste à générer du code isolé.

---

### GPQA Diamond (Recherche/Science)

**Description:** Questions de niveau doctorat en physique, chimie et biologie.

**Source:** https://arxiv.org/abs/2311.12022

**Scores (Novembre 2025):**

| Modèle | Score |
|--------|-------|
| Gemini 3 Pro | **91.9%** 👑 |
| GPT-5.1 | 88.1% |
| Claude Sonnet 4.5 | 83.4% |

**Pourquoi c'est pertinent:** Mesure la compréhension scientifique profonde nécessaire pour la recherche avancée.

---

### HealthBench Hard (Médical)

**Description:** Évaluation médicale rigoureuse basée sur 5,000 conversations réalistes, évaluées par 262 médecins de 60 pays.

**Source:** https://arxiv.org/abs/2505.08775

**Scores (Août 2025):**

| Modèle | Score |
|--------|-------|
| GPT-5 | **46.2%** 👑 |
| o3 | 31.6% |
| GPT-4o | 32.0% |

**Pourquoi c'est pertinent:** Premier benchmark médical vraiment rigoureux avec validation par des professionnels de santé.

---

### AIME 2025 (Mathématiques)

**Description:** American Invitational Mathematics Examination - compétition mathématique de niveau lycée avancé.

**Source:** https://artofproblemsolving.com/wiki/index.php/AIME

**Scores (Novembre 2025):**

| Modèle | Score (sans tools) | Score (avec tools) |
|--------|-------------------|-------------------|
| GPT-5 Pro | - | **100%** 👑 |
| Gemini 3 Pro | 95% | 100% |
| GPT-5.1 | 94.6% | - |
| Claude Sonnet 4.5 | 87% | - |

---

## 📐 Méthodologie de Calcul

### Score de Pertinence (0-100%)

Le score de pertinence par domaine est calculé ainsi:

```
Score = (Benchmark_Score × 0.7) + (Retours_Usage × 0.3)
```

**Composants:**
1. **Benchmark Score (70%):** Résultats officiels sur les benchmarks de référence
2. **Retours Usage (30%):** Feedback de la communauté et tests pratiques

### Estimation des Tokens

```python
# Tokens estimés selon le type de tâche
TOKEN_ESTIMATES = {
    'code': (800, 1500),      # (input, output)
    'legal': (1200, 2000),
    'medical': (600, 1000),
    'creative': (400, 1200),
    'research': (1000, 2500),
    'general': (500, 800),
}
```

### Coût Estimé

```
Coût = (input_tokens × prix_input / 1M) + (output_tokens × prix_output / 1M)
```

**Prix API (Décembre 2025):**

| Modèle | Input ($/1M) | Output ($/1M) |
|--------|-------------|---------------|
| Claude Opus 4.5 | $5.00 | $25.00 |
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| Claude Haiku 4.5 | $0.25 | $1.25 |
| GPT-5.1 | $1.25 | $10.00 |
| GPT-5.1 Mini | $0.25 | $2.00 |
| GPT-5 Pro | $5.00 | $20.00 |
| Gemini 3 Pro | $2.00 | $12.00 |
| Gemini 3 Flash | $0.50 | $2.00 |

### Score de Valeur

```
Valeur = Score_Pertinence / (Coût × 100 + 0.001)
```

Plus la valeur est élevée, meilleur est le rapport qualité/prix.

---

## 🔍 Sources Tierces de Comparaison

| Source | URL | Focus |
|--------|-----|-------|
| Vellum AI | https://www.vellum.ai/blog/claude-opus-4-5-benchmarks | Analyse Claude 4.5 |
| DataCamp | https://www.datacamp.com/blog/claude-opus-4-5 | Review technique |
| CounselPro | https://www.counselpro.ai/blog/chatgpt-vs-claude-vs-gemini-for-lawyers-financial-review | Legal/Finance |
| Simon Willison | https://simonwillison.net/2025/Nov/18/gemini-3/ | Tests Gemini 3 |
| MarkTechPost | https://www.marktechpost.com/ | Analyses techniques |

---

## ⚠️ Limitations

1. **Benchmarks ≠ Performance réelle:** Les benchmarks mesurent des tâches spécifiques, pas toutes les situations possibles.

2. **Évolution rapide:** Les scores peuvent changer avec les mises à jour des modèles.

3. **Contexte spécifique:** Un modèle "meilleur" en moyenne peut être moins bon pour votre cas d'usage précis.

4. **Biais de prompt:** Les résultats peuvent varier selon la façon dont les prompts sont formulés.

---

## 📅 Dernière mise à jour

**Date:** Décembre 2025

**Modèles couverts:**
- Claude Opus 4.5, Sonnet 4.5, Haiku 4.5
- GPT-5.1, GPT-5.1 Mini, GPT-5 Pro
- Gemini 3 Pro, Gemini 3 Flash

---

## 📝 Comment contribuer

Si vous trouvez des erreurs ou avez des sources plus récentes:

1. Vérifiez que la source est officielle ou peer-reviewed
2. Incluez l'URL complète et la date
3. Précisez le benchmark et le score exact

---

*Ce document est généré automatiquement par PromptForge et mis à jour régulièrement.*
