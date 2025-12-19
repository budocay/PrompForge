"""
Système d'onboarding guidé pour PromptForge.
Guide l'utilisateur étape par étape pour créer son contexte projet.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class QuestionType(Enum):
    """Types de questions pour le questionnaire."""
    TEXT = "text"           # Champ texte simple
    TEXTAREA = "textarea"   # Zone de texte multiligne
    SELECT = "select"       # Liste déroulante
    MULTISELECT = "multiselect"  # Sélection multiple
    NUMBER = "number"       # Nombre
    SLIDER = "slider"       # Curseur


@dataclass
class Question:
    """Une question du questionnaire."""
    id: str
    label: str
    question_type: QuestionType
    placeholder: str = ""
    help_text: str = ""
    required: bool = False
    options: list[str] = field(default_factory=list)  # Pour SELECT/MULTISELECT
    default: str = ""
    min_value: int = 0      # Pour NUMBER/SLIDER
    max_value: int = 100    # Pour NUMBER/SLIDER


@dataclass  
class OnboardingStep:
    """Une étape du questionnaire."""
    title: str
    description: str
    questions: list[Question]
    icon: str = "📝"


# ============================================
# QUESTIONNAIRES PAR MÉTIER
# ============================================

ONBOARDING_FLOWS = {
    # ==========================================
    # SEO SPECIALIST
    # ==========================================
    "seo-specialist": {
        "name": "🔍 SEO Specialist",
        "welcome": "Créons ensemble votre profil SEO pour des prompts ultra-ciblés !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Quelques infos sur vous",
                icon="👤",
                questions=[
                    Question("level", "Votre niveau en SEO", QuestionType.SELECT,
                            options=["Débutant", "Confirmé (1-3 ans)", "Senior (3-5 ans)", "Expert (5+ ans)"],
                            required=True),
                    Question("specialization", "Votre spécialisation", QuestionType.MULTISELECT,
                            options=["SEO Technique", "SEO Content", "SEO Local", "E-commerce SEO", "International SEO"],
                            help_text="Sélectionnez une ou plusieurs spécialisations"),
                ]
            ),
            OnboardingStep(
                title="Votre Site/Client",
                description="Parlons de votre projet actuel",
                icon="🌐",
                questions=[
                    Question("site_url", "URL du site", QuestionType.TEXT,
                            placeholder="ex: mon-site.fr", required=True),
                    Question("site_type", "Type de site", QuestionType.SELECT,
                            options=["Blog", "E-commerce", "Site vitrine", "SaaS", "Média/News", "Marketplace", "Autre"]),
                    Question("site_niche", "Thématique/Niche", QuestionType.TEXT,
                            placeholder="ex: Jardinage, Finance, Tech...", required=True),
                    Question("site_age", "Âge du site", QuestionType.SELECT,
                            options=["Nouveau (< 6 mois)", "Jeune (6-12 mois)", "Établi (1-3 ans)", "Mature (3+ ans)"]),
                ]
            ),
            OnboardingStep(
                title="Métriques Actuelles",
                description="Où en êtes-vous ?",
                icon="📊",
                questions=[
                    Question("domain_rating", "Domain Rating (DR/DA)", QuestionType.NUMBER,
                            placeholder="ex: 25", help_text="Ahrefs DR ou Moz DA", min_value=0, max_value=100),
                    Question("monthly_traffic", "Trafic mensuel estimé", QuestionType.SELECT,
                            options=["< 1K", "1K - 10K", "10K - 50K", "50K - 100K", "100K - 500K", "500K+"]),
                    Question("indexed_pages", "Pages indexées", QuestionType.SELECT,
                            options=["< 50", "50-200", "200-500", "500-1000", "1000+"]),
                ]
            ),
            OnboardingStep(
                title="Concurrence",
                description="Qui sont vos concurrents ?",
                icon="🎯",
                questions=[
                    Question("competitors", "Concurrents principaux (1 par ligne)", QuestionType.TEXTAREA,
                            placeholder="concurrent1.fr\nconcurrent2.com\nconcurrent3.fr",
                            help_text="Les 3-5 sites que vous voulez dépasser"),
                    Question("competitor_model", "Concurrent modèle (atteignable)", QuestionType.TEXT,
                            placeholder="ex: site-similaire.fr",
                            help_text="Un site de taille similaire qui réussit bien"),
                ]
            ),
            OnboardingStep(
                title="Outils & Contraintes",
                description="Vos moyens et limites",
                icon="🔧",
                questions=[
                    Question("seo_tools", "Outils SEO disponibles", QuestionType.MULTISELECT,
                            options=["Ahrefs", "SEMrush", "Moz", "Screaming Frog", "Google Search Console", 
                                    "Google Analytics", "Surfer SEO", "Clearscope", "Autre"]),
                    Question("content_budget", "Budget contenu (articles/semaine)", QuestionType.SELECT,
                            options=["1 article", "2 articles", "3-5 articles", "5-10 articles", "10+ articles"]),
                    Question("kd_max", "KD maximum réaliste pour vous", QuestionType.SLIDER,
                            min_value=5, max_value=50, default="25",
                            help_text="Keyword Difficulty max que vous pouvez cibler"),
                ]
            ),
            OnboardingStep(
                title="Objectifs",
                description="Où voulez-vous aller ?",
                icon="🚀",
                questions=[
                    Question("main_goal", "Objectif principal", QuestionType.SELECT,
                            options=["Augmenter le trafic organique", "Améliorer les conversions", 
                                    "Renforcer l'autorité (backlinks)", "Dominer une niche", "Lancer un nouveau site"]),
                    Question("target_dr", "DR cible à 12 mois", QuestionType.NUMBER,
                            min_value=0, max_value=100, placeholder="ex: 40"),
                    Question("focus_intent", "Intent à privilégier", QuestionType.MULTISELECT,
                            options=["Informationnelle (how-to, guides)", "Transactionnelle (acheter, prix)", 
                                    "Navigationnelle (marque)", "Commerciale (comparatifs, avis)"]),
                ]
            ),
        ]
    },

    # ==========================================
    # MARKETING DIGITAL
    # ==========================================
    "marketing-digital": {
        "name": "📢 Marketing Digital",
        "welcome": "Configurons votre profil marketing pour des campagnes performantes !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Votre expérience marketing",
                icon="👤",
                questions=[
                    Question("level", "Votre niveau", QuestionType.SELECT,
                            options=["Junior", "Confirmé", "Senior", "Head of / Manager"],
                            required=True),
                    Question("specialization", "Spécialisations", QuestionType.MULTISELECT,
                            options=["Acquisition Paid", "Growth Hacking", "Content Marketing", 
                                    "Email Marketing", "Social Media", "Marketing Automation", "CRO"]),
                ]
            ),
            OnboardingStep(
                title="Votre Entreprise",
                description="Contexte business",
                icon="🏢",
                questions=[
                    Question("company_name", "Nom de l'entreprise/produit", QuestionType.TEXT, required=True),
                    Question("business_type", "Type de business", QuestionType.SELECT,
                            options=["B2B SaaS", "B2C App", "E-commerce", "Marketplace", "Services", "Agence"]),
                    Question("company_stage", "Stade de l'entreprise", QuestionType.SELECT,
                            options=["Pre-seed / Idée", "Seed / MVP", "Série A / PMF", "Scale-up", "Entreprise établie"]),
                    Question("value_prop", "Proposition de valeur (1 phrase)", QuestionType.TEXT,
                            placeholder="ex: Nous aidons les PME à automatiser leur comptabilité"),
                ]
            ),
            OnboardingStep(
                title="Cible & Persona",
                description="À qui vendez-vous ?",
                icon="🎯",
                questions=[
                    Question("target_audience", "Cible principale", QuestionType.TEXT,
                            placeholder="ex: DRH de PME 50-200 employés, France"),
                    Question("persona_pain", "Pain point #1 de votre cible", QuestionType.TEXT,
                            placeholder="ex: Passe 2h/jour sur des tâches administratives"),
                    Question("buyer_journey", "Durée du cycle d'achat", QuestionType.SELECT,
                            options=["Impulsif (< 1 jour)", "Court (1-7 jours)", "Moyen (1-4 semaines)", 
                                    "Long (1-3 mois)", "Très long (3+ mois)"]),
                ]
            ),
            OnboardingStep(
                title="Canaux & Budget",
                description="Vos leviers marketing",
                icon="💰",
                questions=[
                    Question("channels", "Canaux utilisés", QuestionType.MULTISELECT,
                            options=["Google Ads", "Meta Ads (Facebook/Instagram)", "LinkedIn Ads", 
                                    "TikTok Ads", "Email", "SEO", "Content", "Influenceurs", "Affiliation"]),
                    Question("monthly_budget", "Budget mensuel ads", QuestionType.SELECT,
                            options=["< 1K€", "1K - 5K€", "5K - 20K€", "20K - 50K€", "50K - 100K€", "100K€+"]),
                    Question("main_kpi", "KPI principal", QuestionType.SELECT,
                            options=["CAC (Coût d'Acquisition)", "ROAS", "MQL/SQL", "Conversion Rate", 
                                    "LTV", "MRR/ARR", "Engagement"]),
                ]
            ),
            OnboardingStep(
                title="Outils",
                description="Votre stack marketing",
                icon="🔧",
                questions=[
                    Question("tools", "Outils utilisés", QuestionType.MULTISELECT,
                            options=["HubSpot", "Salesforce", "Google Analytics", "Mixpanel", "Amplitude",
                                    "Mailchimp", "Brevo (Sendinblue)", "ActiveCampaign", "Notion", "Airtable"]),
                    Question("crm", "CRM principal", QuestionType.SELECT,
                            options=["HubSpot", "Salesforce", "Pipedrive", "Zoho", "Notion", "Excel/Sheets", "Autre"]),
                ]
            ),
        ]
    },

    # ==========================================
    # DÉVELOPPEUR BACKEND
    # ==========================================
    "dev-backend": {
        "name": "⚙️ Dev Backend",
        "welcome": "Configurons votre environnement de développement !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Votre expérience dev",
                icon="👤",
                questions=[
                    Question("level", "Niveau", QuestionType.SELECT,
                            options=["Junior (0-2 ans)", "Confirmé (2-5 ans)", "Senior (5-8 ans)", "Staff/Lead (8+ ans)"],
                            required=True),
                    Question("main_language", "Langage principal", QuestionType.SELECT,
                            options=["Python", "JavaScript/TypeScript", "Java", "Go", "Rust", "C#", "PHP", "Ruby"],
                            required=True),
                ]
            ),
            OnboardingStep(
                title="Stack Technique",
                description="Vos technologies",
                icon="🛠️",
                questions=[
                    Question("framework", "Framework principal", QuestionType.SELECT,
                            options=["FastAPI", "Django", "Flask", "Express.js", "NestJS", "Spring Boot", 
                                    "ASP.NET", "Laravel", "Ruby on Rails", "Gin (Go)", "Actix (Rust)"]),
                    Question("database", "Base de données principale", QuestionType.SELECT,
                            options=["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "DynamoDB", "Firestore"]),
                    Question("orm", "ORM/ODM", QuestionType.SELECT,
                            options=["SQLAlchemy", "Django ORM", "Prisma", "TypeORM", "Sequelize", 
                                    "Mongoose", "Entity Framework", "Aucun (SQL raw)"]),
                    Question("other_tech", "Autres technologies", QuestionType.MULTISELECT,
                            options=["Docker", "Kubernetes", "Redis", "RabbitMQ", "Kafka", "GraphQL", 
                                    "gRPC", "WebSockets", "Celery", "AWS Lambda"]),
                ]
            ),
            OnboardingStep(
                title="Infrastructure",
                description="Où déployez-vous ?",
                icon="☁️",
                questions=[
                    Question("cloud", "Cloud provider", QuestionType.SELECT,
                            options=["AWS", "GCP", "Azure", "DigitalOcean", "Heroku", "Vercel", "Railway", "Self-hosted"]),
                    Question("ci_cd", "CI/CD", QuestionType.SELECT,
                            options=["GitHub Actions", "GitLab CI", "Jenkins", "CircleCI", "ArgoCD", "Autre"]),
                    Question("monitoring", "Monitoring/Observabilité", QuestionType.MULTISELECT,
                            options=["Datadog", "Prometheus/Grafana", "New Relic", "Sentry", "ELK Stack", 
                                    "CloudWatch", "Honeycomb"]),
                ]
            ),
            OnboardingStep(
                title="Conventions",
                description="Vos standards de code",
                icon="📏",
                questions=[
                    Question("formatter", "Formatter", QuestionType.SELECT,
                            options=["Black", "Prettier", "gofmt", "rustfmt", "Aucun spécifique"]),
                    Question("linter", "Linter", QuestionType.SELECT,
                            options=["Ruff", "ESLint", "Pylint", "Flake8", "golangci-lint", "Clippy"]),
                    Question("testing", "Framework de test", QuestionType.SELECT,
                            options=["pytest", "Jest", "JUnit", "Go test", "RSpec", "PHPUnit"]),
                    Question("coverage_target", "Couverture de tests cible", QuestionType.SLIDER,
                            min_value=0, max_value=100, default="80"),
                ]
            ),
            OnboardingStep(
                title="Projet Actuel",
                description="Sur quoi travaillez-vous ?",
                icon="📁",
                questions=[
                    Question("project_type", "Type de projet", QuestionType.SELECT,
                            options=["API REST", "Microservices", "Monolithe", "Serverless", "CLI", "Background jobs"]),
                    Question("project_desc", "Description courte du projet", QuestionType.TEXTAREA,
                            placeholder="ex: API de gestion d'inventaire pour e-commerce"),
                    Question("team_size", "Taille de l'équipe dev", QuestionType.SELECT,
                            options=["Solo", "2-3 devs", "4-6 devs", "7-10 devs", "10+ devs"]),
                ]
            ),
        ]
    },

    # ==========================================
    # PRODUCT MANAGER
    # ==========================================
    "product-manager": {
        "name": "🎯 Product Manager",
        "welcome": "Créons votre contexte produit pour des specs au top !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Votre expérience PM",
                icon="👤",
                questions=[
                    Question("level", "Niveau", QuestionType.SELECT,
                            options=["APM / Junior", "PM", "Senior PM", "Lead PM / Group PM", "Head of Product / CPO"],
                            required=True),
                    Question("pm_type", "Type de PM", QuestionType.SELECT,
                            options=["Product Manager", "Product Owner", "Technical PM", "Growth PM", "Platform PM"]),
                ]
            ),
            OnboardingStep(
                title="Votre Produit",
                description="Le produit sur lequel vous travaillez",
                icon="📱",
                questions=[
                    Question("product_name", "Nom du produit", QuestionType.TEXT, required=True),
                    Question("product_type", "Type de produit", QuestionType.SELECT,
                            options=["B2B SaaS", "B2C App", "Marketplace", "Internal Tool", "API/Platform", "Hardware"]),
                    Question("product_stage", "Stade du produit", QuestionType.SELECT,
                            options=["Discovery / Idéation", "MVP", "Product-Market Fit", "Scale", "Mature"]),
                    Question("product_mission", "Mission du produit (1 phrase)", QuestionType.TEXT,
                            placeholder="ex: Aider les équipes RH à recruter 2x plus vite"),
                ]
            ),
            OnboardingStep(
                title="Vos Users",
                description="Qui utilise votre produit ?",
                icon="👥",
                questions=[
                    Question("primary_persona", "Persona principal", QuestionType.TEXT,
                            placeholder="ex: Sophie, 35 ans, DRH de PME"),
                    Question("user_count", "Nombre d'utilisateurs actifs", QuestionType.SELECT,
                            options=["< 100", "100-1K", "1K-10K", "10K-100K", "100K-1M", "1M+"]),
                    Question("main_pain_point", "Pain point #1 des users", QuestionType.TEXT,
                            placeholder="ex: Processus de recrutement trop long et manuel"),
                ]
            ),
            OnboardingStep(
                title="Métriques",
                description="Comment mesurez-vous le succès ?",
                icon="📊",
                questions=[
                    Question("north_star", "North Star Metric", QuestionType.TEXT,
                            placeholder="ex: Weekly Active Users, Transactions/mois"),
                    Question("key_metrics", "Autres métriques clés", QuestionType.MULTISELECT,
                            options=["DAU/MAU", "Activation Rate", "Retention (D7/D30)", "NPS", "Revenue (MRR/ARR)",
                                    "Conversion Rate", "Time to Value", "Feature Adoption"]),
                    Question("okr_framework", "Framework d'objectifs", QuestionType.SELECT,
                            options=["OKR", "KPI", "North Star + Input Metrics", "Pas de framework formel"]),
                ]
            ),
            OnboardingStep(
                title="Équipe & Process",
                description="Comment travaillez-vous ?",
                icon="👨‍👩‍👧‍👦",
                questions=[
                    Question("team_size", "Taille de l'équipe produit", QuestionType.SELECT,
                            options=["Solo PM", "2-3 PM", "4-6 PM", "7+ PM"]),
                    Question("dev_team_size", "Devs dans votre squad", QuestionType.SELECT,
                            options=["1-2 devs", "3-5 devs", "6-8 devs", "8+ devs"]),
                    Question("methodology", "Méthodologie", QuestionType.SELECT,
                            options=["Scrum", "Kanban", "Shape Up", "Waterfall", "Hybride"]),
                    Question("sprint_length", "Durée des sprints", QuestionType.SELECT,
                            options=["1 semaine", "2 semaines", "3 semaines", "4 semaines", "Pas de sprints"]),
                    Question("tools", "Outils PM", QuestionType.MULTISELECT,
                            options=["Jira", "Linear", "Asana", "Notion", "Productboard", "Amplitude", 
                                    "Mixpanel", "Figma", "Miro"]),
                ]
            ),
            OnboardingStep(
                title="Priorisation",
                description="Comment priorisez-vous ?",
                icon="⚖️",
                questions=[
                    Question("prioritization", "Framework de priorisation", QuestionType.SELECT,
                            options=["RICE", "ICE", "MoSCoW", "Value vs Effort", "Kano", "Opportunity Scoring", "Intuition"]),
                    Question("decision_makers", "Qui décide des priorités ?", QuestionType.MULTISELECT,
                            options=["PM seul", "PM + Tech Lead", "Trio (PM/Design/Tech)", "Leadership", "Data-driven"]),
                ]
            ),
        ]
    },

    # ==========================================
    # COMMERCIAL / SALES
    # ==========================================
    "commercial-sales": {
        "name": "💼 Commercial / Sales",
        "welcome": "Configurons votre profil commercial pour closer plus de deals !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Votre rôle commercial",
                icon="👤",
                questions=[
                    Question("role", "Votre rôle", QuestionType.SELECT,
                            options=["SDR/BDR", "Account Executive", "Account Manager", "Sales Manager", "VP Sales"],
                            required=True),
                    Question("experience", "Expérience en vente", QuestionType.SELECT,
                            options=["< 1 an", "1-3 ans", "3-5 ans", "5-10 ans", "10+ ans"]),
                    Question("sales_type", "Type de vente", QuestionType.SELECT,
                            options=["Inside Sales", "Field Sales", "Hybrid", "Channel/Partners"]),
                ]
            ),
            OnboardingStep(
                title="Votre Offre",
                description="Ce que vous vendez",
                icon="📦",
                questions=[
                    Question("product_name", "Nom du produit/service", QuestionType.TEXT, required=True),
                    Question("value_prop", "Proposition de valeur", QuestionType.TEXT,
                            placeholder="ex: Réduisez vos coûts RH de 40%"),
                    Question("price_range", "Fourchette de prix", QuestionType.SELECT,
                            options=["< 1K€", "1K - 10K€", "10K - 50K€", "50K - 100K€", "100K€+"]),
                    Question("sales_cycle", "Durée moyenne du cycle", QuestionType.SELECT,
                            options=["< 1 semaine", "1-4 semaines", "1-3 mois", "3-6 mois", "6+ mois"]),
                ]
            ),
            OnboardingStep(
                title="Votre Cible",
                description="À qui vendez-vous ?",
                icon="🎯",
                questions=[
                    Question("target_market", "Marché cible", QuestionType.SELECT,
                            options=["TPE (< 10)", "PME (10-250)", "ETI (250-5000)", "Grands comptes (5000+)", "Mix"]),
                    Question("target_sectors", "Secteurs cibles", QuestionType.TEXT,
                            placeholder="ex: Tech, Finance, Retail"),
                    Question("decision_maker", "Décideur type", QuestionType.TEXT,
                            placeholder="ex: DRH, DSI, CEO de PME"),
                    Question("buying_committee", "Taille du comité d'achat", QuestionType.SELECT,
                            options=["1 personne", "2-3 personnes", "4-6 personnes", "6+ personnes"]),
                ]
            ),
            OnboardingStep(
                title="Objections & Concurrence",
                description="Les freins à la vente",
                icon="🛡️",
                questions=[
                    Question("top_objection", "Objection #1", QuestionType.TEXT,
                            placeholder="ex: C'est trop cher"),
                    Question("competitors", "Concurrents principaux", QuestionType.TEXTAREA,
                            placeholder="Concurrent1\nConcurrent2\nConcurrent3"),
                    Question("differentiator", "Votre différenciateur clé", QuestionType.TEXT,
                            placeholder="ex: Seul à offrir une intégration native avec SAP"),
                ]
            ),
            OnboardingStep(
                title="Outils & Objectifs",
                description="Vos moyens et cibles",
                icon="🔧",
                questions=[
                    Question("crm", "CRM", QuestionType.SELECT,
                            options=["Salesforce", "HubSpot", "Pipedrive", "Zoho", "Close", "Excel/Sheets"]),
                    Question("outreach_tools", "Outils de prospection", QuestionType.MULTISELECT,
                            options=["LinkedIn Sales Navigator", "Apollo", "Lusha", "Lemlist", 
                                    "Outreach", "Salesloft", "Aircall", "Gong"]),
                    Question("monthly_target", "Objectif mensuel (€)", QuestionType.TEXT,
                            placeholder="ex: 50000"),
                    Question("meetings_target", "Objectif RDV/semaine", QuestionType.NUMBER,
                            min_value=0, max_value=50, placeholder="ex: 10"),
                ]
            ),
        ]
    },

    # ==========================================
    # RH / RECRUTEUR
    # ==========================================
    "rh-recruteur": {
        "name": "👥 RH / Recruteur",
        "welcome": "Configurons votre profil RH pour recruter les meilleurs talents !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Votre rôle RH",
                icon="👤",
                questions=[
                    Question("role", "Votre rôle", QuestionType.SELECT,
                            options=["Chargé(e) de recrutement", "Talent Acquisition Manager", "RRH", 
                                    "DRH", "Recruteur freelance/cabinet"],
                            required=True),
                    Question("specialization", "Spécialisation recrutement", QuestionType.MULTISELECT,
                            options=["Tech/IT", "Sales", "Marketing", "Finance", "RH", "Exec Search", "Volume"]),
                ]
            ),
            OnboardingStep(
                title="Votre Entreprise",
                description="Le contexte de recrutement",
                icon="🏢",
                questions=[
                    Question("company_name", "Nom de l'entreprise", QuestionType.TEXT, required=True),
                    Question("company_size", "Taille de l'entreprise", QuestionType.SELECT,
                            options=["Startup (< 20)", "Scale-up (20-100)", "PME (100-500)", 
                                    "ETI (500-5000)", "Grand groupe (5000+)"]),
                    Question("company_sector", "Secteur", QuestionType.SELECT,
                            options=["Tech/SaaS", "E-commerce", "Finance", "Industrie", "Services", "Santé", "Autre"]),
                    Question("culture_keywords", "3 mots pour décrire la culture", QuestionType.TEXT,
                            placeholder="ex: Innovation, Bienveillance, Performance"),
                ]
            ),
            OnboardingStep(
                title="EVP (Employee Value Proposition)",
                description="Ce que vous offrez aux candidats",
                icon="🎁",
                questions=[
                    Question("remote_policy", "Politique remote", QuestionType.SELECT,
                            options=["Full remote", "Hybride (2-3j bureau)", "Présentiel flexible", "Présentiel obligatoire"]),
                    Question("salary_position", "Positionnement salaires", QuestionType.SELECT,
                            options=["Top of market (+20%)", "Au-dessus du marché (+10%)", 
                                    "Dans le marché", "En-dessous du marché"]),
                    Question("key_benefits", "Avantages clés", QuestionType.MULTISELECT,
                            options=["Equity/BSPCE", "Formation continue", "Congés supplémentaires", 
                                    "Mutuelle premium", "Sport/Bien-être", "Matériel au choix"]),
                ]
            ),
            OnboardingStep(
                title="Recrutements en Cours",
                description="Vos besoins actuels",
                icon="📋",
                questions=[
                    Question("open_positions", "Nombre de postes ouverts", QuestionType.SELECT,
                            options=["1-5", "5-10", "10-20", "20-50", "50+"]),
                    Question("priority_roles", "Postes prioritaires", QuestionType.TEXTAREA,
                            placeholder="ex:\nSenior Backend Developer\nProduct Manager\nHead of Sales"),
                    Question("time_to_hire", "Time-to-hire moyen actuel", QuestionType.SELECT,
                            options=["< 30 jours", "30-45 jours", "45-60 jours", "60-90 jours", "90+ jours"]),
                ]
            ),
            OnboardingStep(
                title="Outils & Process",
                description="Comment recrutez-vous ?",
                icon="🔧",
                questions=[
                    Question("ats", "ATS utilisé", QuestionType.SELECT,
                            options=["Lever", "Greenhouse", "Workable", "Welcome to the Jungle", 
                                    "Recruitee", "TeamTailor", "Excel/Notion"]),
                    Question("sourcing_channels", "Canaux de sourcing", QuestionType.MULTISELECT,
                            options=["LinkedIn Recruiter", "Welcome to the Jungle", "Indeed", 
                                    "Cooptation", "Écoles/Bootcamps", "Jobboards spécialisés", "Chasse"]),
                    Question("interview_steps", "Nombre d'étapes d'entretien", QuestionType.SELECT,
                            options=["2 étapes", "3 étapes", "4 étapes", "5+ étapes"]),
                ]
            ),
        ]
    },

    # ==========================================
    # DATA ANALYST
    # ==========================================
    "data-analyst": {
        "name": "📊 Data Analyst",
        "welcome": "Configurons votre environnement data !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Votre expérience data",
                icon="👤",
                questions=[
                    Question("level", "Niveau", QuestionType.SELECT,
                            options=["Junior (0-2 ans)", "Confirmé (2-5 ans)", "Senior (5+ ans)", "Lead/Manager"],
                            required=True),
                    Question("specialization", "Spécialisation", QuestionType.SELECT,
                            options=["Product Analytics", "Marketing Analytics", "Finance Analytics", 
                                    "BI/Reporting", "Data Engineering", "Data Science"]),
                ]
            ),
            OnboardingStep(
                title="Stack Data",
                description="Vos outils techniques",
                icon="🛠️",
                questions=[
                    Question("sql_level", "Niveau SQL", QuestionType.SELECT,
                            options=["Basique (SELECT, WHERE)", "Intermédiaire (JOINs, GROUP BY)", 
                                    "Avancé (Window functions, CTEs)", "Expert (Optimisation, procédures)"]),
                    Question("warehouse", "Data Warehouse", QuestionType.SELECT,
                            options=["BigQuery", "Snowflake", "Redshift", "Databricks", "PostgreSQL", "Autre"]),
                    Question("bi_tool", "Outil BI principal", QuestionType.SELECT,
                            options=["Looker", "Tableau", "Power BI", "Metabase", "Mode", "Preset", "Autre"]),
                    Question("other_tools", "Autres outils", QuestionType.MULTISELECT,
                            options=["Python/Pandas", "R", "dbt", "Airflow", "Fivetran", "Airbyte", 
                                    "Jupyter", "Excel avancé"]),
                ]
            ),
            OnboardingStep(
                title="Sources de Données",
                description="D'où viennent vos données ?",
                icon="🗄️",
                questions=[
                    Question("data_sources", "Sources principales", QuestionType.MULTISELECT,
                            options=["Base de production (PostgreSQL, MySQL...)", "Analytics (Amplitude, Mixpanel)", 
                                    "Marketing (Google Ads, Meta)", "CRM (Salesforce, HubSpot)", 
                                    "Finance (Stripe, Chargebee)", "Support (Zendesk, Intercom)"]),
                    Question("data_volume", "Volume de données", QuestionType.SELECT,
                            options=["< 1GB", "1-100 GB", "100 GB - 1 TB", "1-10 TB", "10+ TB"]),
                ]
            ),
            OnboardingStep(
                title="Métriques & KPIs",
                description="Que mesurez-vous ?",
                icon="📈",
                questions=[
                    Question("main_metrics", "Métriques principales", QuestionType.MULTISELECT,
                            options=["Revenue (MRR, ARR)", "Acquisition (CAC, Leads)", "Activation", 
                                    "Retention (Churn)", "Engagement (DAU/MAU)", "NPS/CSAT"]),
                    Question("reporting_frequency", "Fréquence des rapports", QuestionType.SELECT,
                            options=["Real-time", "Daily", "Weekly", "Monthly"]),
                    Question("main_stakeholders", "Stakeholders principaux", QuestionType.MULTISELECT,
                            options=["C-level/Direction", "Product", "Marketing", "Sales", "Finance", "Tech"]),
                ]
            ),
        ]
    },

    # ==========================================
    # SUPPORT CLIENT
    # ==========================================
    "support-client": {
        "name": "🎧 Support Client",
        "welcome": "Configurons votre profil support pour des clients satisfaits !",
        "steps": [
            OnboardingStep(
                title="Votre Profil",
                description="Votre rôle support",
                icon="👤",
                questions=[
                    Question("role", "Votre rôle", QuestionType.SELECT,
                            options=["Agent Support", "Support Senior", "Team Lead", "Customer Success Manager", "Head of Support"],
                            required=True),
                    Question("support_type", "Type de support", QuestionType.SELECT,
                            options=["Support technique", "Support généraliste", "Customer Success", "Onboarding specialist"]),
                ]
            ),
            OnboardingStep(
                title="Votre Produit",
                description="Ce que vous supportez",
                icon="📱",
                questions=[
                    Question("product_name", "Nom du produit", QuestionType.TEXT, required=True),
                    Question("product_complexity", "Complexité du produit", QuestionType.SELECT,
                            options=["Simple (app B2C)", "Moyenne (SaaS)", "Complexe (Enterprise)", "Très technique (API/Dev)"]),
                    Question("user_type", "Type d'utilisateurs", QuestionType.SELECT,
                            options=["Grand public (B2C)", "Professionnels (B2B)", "Développeurs", "Mix"]),
                ]
            ),
            OnboardingStep(
                title="Canaux & Volume",
                description="Comment gérez-vous les demandes ?",
                icon="📬",
                questions=[
                    Question("channels", "Canaux de support", QuestionType.MULTISELECT,
                            options=["Email/Tickets", "Chat live", "Téléphone", "Réseaux sociaux", "Forum/Communauté"]),
                    Question("daily_volume", "Volume quotidien de tickets", QuestionType.SELECT,
                            options=["< 20", "20-50", "50-100", "100-200", "200+"]),
                    Question("sla_response", "SLA temps de première réponse", QuestionType.SELECT,
                            options=["< 1h", "1-4h", "4-8h", "24h", "48h+"]),
                ]
            ),
            OnboardingStep(
                title="Problèmes Fréquents",
                description="Les demandes récurrentes",
                icon="❓",
                questions=[
                    Question("top_issues", "Top 3 des problèmes fréquents", QuestionType.TEXTAREA,
                            placeholder="1. Problème de connexion\n2. Question sur la facturation\n3. Bug de l'app"),
                    Question("escalation_rate", "Taux d'escalade", QuestionType.SELECT,
                            options=["< 5%", "5-10%", "10-20%", "20%+"]),
                ]
            ),
            OnboardingStep(
                title="Ton & Outils",
                description="Comment communiquez-vous ?",
                icon="🔧",
                questions=[
                    Question("tone", "Ton de communication", QuestionType.SELECT,
                            options=["Très formel", "Professionnel", "Friendly pro", "Décontracté", "Fun/Décalé"]),
                    Question("helpdesk", "Outil helpdesk", QuestionType.SELECT,
                            options=["Zendesk", "Intercom", "Freshdesk", "Crisp", "HubSpot", "Autre"]),
                    Question("kpis", "KPIs suivis", QuestionType.MULTISELECT,
                            options=["CSAT", "NPS", "First Response Time", "Resolution Time", 
                                    "First Contact Resolution", "Ticket Volume"]),
                ]
            ),
        ]
    },
}


def get_available_professions() -> list[tuple[str, str]]:
    """Retourne la liste des métiers disponibles pour l'onboarding."""
    return [(flow["name"], key) for key, flow in ONBOARDING_FLOWS.items()]


def get_onboarding_flow(profession_key: str) -> dict:
    """Retourne le flow d'onboarding pour un métier."""
    return ONBOARDING_FLOWS.get(profession_key)


def generate_context_from_answers(profession_key: str, answers: dict) -> str:
    """Génère le fichier de contexte .md à partir des réponses."""
    flow = ONBOARDING_FLOWS.get(profession_key)
    if not flow:
        return ""
    
    lines = [f"# Configuration Projet - {flow['name'].replace('🔍 ', '').replace('📢 ', '').replace('⚙️ ', '').replace('🎯 ', '').replace('💼 ', '').replace('👥 ', '').replace('📊 ', '').replace('🎧 ', '')}"]
    lines.append("")
    lines.append(f"*Généré automatiquement par PromptForge*")
    lines.append("")
    
    for step in flow["steps"]:
        lines.append(f"## {step.icon} {step.title}")
        lines.append("")
        
        for q in step.questions:
            answer = answers.get(q.id, q.default or "Non renseigné")
            
            # Formater selon le type
            if isinstance(answer, list):
                answer = ", ".join(answer) if answer else "Non renseigné"
            elif answer == "" or answer is None:
                answer = "Non renseigné"
            
            lines.append(f"**{q.label}**: {answer}")
        
        lines.append("")
    
    # Ajouter la section Instructions pour le LLM
    lines.append("---")
    lines.append("")
    lines.append("## 🤖 Instructions pour le LLM")
    lines.append("")
    lines.append("Quand je te demande de l'aide :")
    lines.append("")
    lines.append("1. **Utilise mon contexte** ci-dessus pour personnaliser tes réponses")
    lines.append("2. **Adapte le niveau** de détail à mon expérience")
    lines.append("3. **Propose des solutions** compatibles avec mes outils")
    lines.append("4. **Respecte mes contraintes** (budget, temps, ressources)")
    lines.append("")
    
    return "\n".join(lines)
