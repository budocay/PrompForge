# Configuration Projet - Data Analyst

## Mon Profil

**Métier** : Data Analyst / BI Analyst / Analytics Engineer
**Niveau** : [Junior / Confirmé / Senior / Lead]
**Spécialisation** : [Product Analytics / Marketing Analytics / Finance / Operations]

---

## Stack Technique

### Langages & Outils

| Technologie | Niveau | Usage |
|-------------|--------|-------|
| **SQL** | Expert | Requêtes, analyses |
| **Python** | [Niveau] | Pandas, scripts |
| **R** | [Niveau] | Stats, visualisations |
| **Excel/Sheets** | [Niveau] | Reporting rapide |

### Outils BI

| Outil | Usage |
|-------|-------|
| **Looker** / **Tableau** / **Power BI** / **Metabase** | Dashboards |
| **dbt** | Transformation |
| **Airflow** | Orchestration |
| **Jupyter** | Exploration |

### Data Warehouse

| Composant | Technologie |
|-----------|-------------|
| **DWH** | BigQuery / Snowflake / Redshift |
| **ETL** | Fivetran / Airbyte / Stitch |
| **Orchestration** | Airflow / Dagster |

---

## Sources de Données

### Principales Sources

| Source | Type | Refresh |
|--------|------|---------|
| **Production DB** | PostgreSQL | Real-time |
| **Analytics** | Amplitude / Mixpanel | Daily |
| **Marketing** | Google Ads, Meta | Daily |
| **CRM** | Salesforce / HubSpot | Hourly |
| **Finance** | Stripe / Chargebee | Daily |

### Schéma Simplifié

```
raw_data/          # Données brutes
├── production/    # DB applicative
├── amplitude/     # Events analytics
├── google_ads/    # Ads data
└── stripe/        # Paiements

staging/           # Données nettoyées
├── stg_users
├── stg_events
└── stg_transactions

marts/             # Modèles métier
├── dim_users
├── dim_products
├── fct_orders
└── fct_sessions
```

---

## KPIs Suivis

### Métriques Principales

| Domaine | KPI | Définition |
|---------|-----|------------|
| **Acquisition** | CAC | Coût acquisition client |
| **Activation** | Activation Rate | % users qui complètent onboarding |
| **Retention** | D7/D30 Retention | % users revenus après 7/30 jours |
| **Revenue** | MRR, ARPU, LTV | Métriques revenue |
| **Engagement** | DAU/MAU, Sessions | Activité users |

### Dashboards Existants

| Dashboard | Audience | Refresh |
|-----------|----------|---------|
| **Executive Summary** | C-level | Weekly |
| **Product Metrics** | Product team | Daily |
| **Marketing Performance** | Marketing | Daily |
| **Finance Overview** | Finance | Monthly |

---

## Conventions SQL

### Style Guide

```sql
-- Utiliser des CTEs pour lisibilité
WITH active_users AS (
    SELECT 
        user_id,
        DATE(created_at) AS signup_date,
        COUNT(*) AS total_actions
    FROM events
    WHERE event_type = 'action'
      AND created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY 1, 2
),

user_segments AS (
    SELECT
        user_id,
        CASE 
            WHEN total_actions >= 10 THEN 'power_user'
            WHEN total_actions >= 3 THEN 'regular'
            ELSE 'casual'
        END AS segment
    FROM active_users
)

SELECT * FROM user_segments;
```

### Naming Conventions

| Élément | Convention | Exemple |
|---------|------------|---------|
| **Tables dim** | `dim_` prefix | `dim_users` |
| **Tables fact** | `fct_` prefix | `fct_orders` |
| **Staging** | `stg_` prefix | `stg_events` |
| **Colonnes date** | `_at` suffix | `created_at` |
| **Colonnes bool** | `is_` prefix | `is_active` |

---

## Contraintes & Règles

### Data Quality

- Pas de données PII non masquées
- Tests dbt sur les modèles critiques
- Documentation des transformations
- Versioning des requêtes

### Performance

- Partitionnement par date sur grandes tables
- Éviter SELECT * en prod
- Index sur colonnes de jointure
- Monitoring des coûts requêtes

---

## Instructions pour le LLM

Quand je demande des analyses ou du SQL :

1. **Pour les requêtes SQL** :
   - Utiliser des CTEs (pas de sous-requêtes imbriquées)
   - Commenter la logique complexe
   - Optimiser pour [BigQuery/Snowflake/...]
   - Inclure les edge cases (NULL handling)

2. **Pour les analyses** :
   - Définir clairement les métriques utilisées
   - Mentionner les limites des données
   - Proposer des visualisations adaptées
   - Conclure avec des recommandations actionnables

3. **Pour les dashboards** :
   - Structurer par audience (exec vs opérationnel)
   - Hiérarchiser les métriques (North Star en haut)
   - Inclure des filtres pertinents
   - Proposer des alertes si besoin

4. **Format attendu** :
   - Code SQL formaté et commenté
   - Explications de la logique
   - Résultats attendus / interprétation

---

*Template Data Analyst pour PromptForge*
