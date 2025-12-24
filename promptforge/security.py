"""
PromptForge Security Module
============================

Provides security-focused features for development prompts:
- Dev context detection (languages, frameworks)
- CVE checking via OSV.dev API (free, no API key required)
- Security guidelines injection for secure code generation
"""

import json
import urllib.request
import urllib.error
import re
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)

# =============================================================================
# CONSTANTS - Dev Detection
# =============================================================================

# Programming languages keywords
DEV_LANGUAGES = {
    "python": ["python", "py", "pip", "django", "flask", "fastapi", "pytorch", "pandas"],
    "javascript": ["javascript", "js", "node", "nodejs", "npm", "react", "vue", "angular", "express"],
    "typescript": ["typescript", "ts", "tsx", "deno", "bun"],
    "rust": ["rust", "cargo", "tokio", "actix", "axum", "warp"],
    "go": ["golang", "go ", "gin", "fiber", "echo"],
    "java": ["java", "spring", "maven", "gradle", "kotlin"],
    "csharp": ["c#", "csharp", ".net", "dotnet", "asp.net", "blazor"],
    "php": ["php", "laravel", "symfony", "composer"],
    "ruby": ["ruby", "rails", "gem", "bundler"],
    "swift": ["swift", "ios", "swiftui", "cocoapods"],
}

# Security-sensitive keywords that trigger security mode
SECURITY_KEYWORDS = [
    # Auth & Identity
    "auth", "authentication", "authorization", "login", "password", "jwt", "token",
    "oauth", "session", "cookie", "credentials", "api key", "secret",
    # Data
    "database", "sql", "query", "insert", "update", "delete", "select",
    "mongodb", "postgresql", "mysql", "redis", "elasticsearch",
    # Network
    "api", "endpoint", "route", "http", "https", "request", "response",
    "webhook", "websocket", "cors", "proxy",
    # File & System
    "file", "upload", "download", "path", "command", "shell",
    "process", "subprocess", "system",
    # Crypto
    "encrypt", "decrypt", "hash", "bcrypt", "argon", "crypto", "ssl", "tls",
    # Input/Output
    "input", "form", "validate", "sanitize", "escape", "encode", "decode",
    "serialize", "deserialize", "yaml", "xml", "json",
]

# OWASP Top 10 2021 categories
OWASP_TOP_10 = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable and Outdated Components",
    "A07": "Identification and Authentication Failures",
    "A08": "Software and Data Integrity Failures",
    "A09": "Security Logging and Monitoring Failures",
    "A10": "Server-Side Request Forgery (SSRF)",
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CVEInfo:
    """Information about a CVE vulnerability."""
    id: str
    summary: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    package: str
    affected_versions: str
    fixed_version: Optional[str] = None
    references: list[str] = field(default_factory=list)


@dataclass
class SecurityContext:
    """Security context detected from prompt or project."""
    is_dev: bool = False
    languages: list[str] = field(default_factory=list)
    security_keywords_found: list[str] = field(default_factory=list)
    cves: list[CVEInfo] = field(default_factory=list)
    security_level: str = "standard"  # standard, elevated, critical


# =============================================================================
# DEV CONTEXT DETECTION
# =============================================================================

def detect_dev_context(text: str) -> SecurityContext:
    """
    Analyze text to detect if it's development-related and security-sensitive.
    """
    text_lower = text.lower()
    context = SecurityContext()

    # Detect programming languages
    for lang, keywords in DEV_LANGUAGES.items():
        for keyword in keywords:
            if keyword in text_lower:
                if lang not in context.languages:
                    context.languages.append(lang)
                break

    # Detect security-sensitive keywords
    for keyword in SECURITY_KEYWORDS:
        if keyword in text_lower:
            context.security_keywords_found.append(keyword)

    # Determine if this is dev context
    context.is_dev = len(context.languages) > 0 or len(context.security_keywords_found) >= 2

    # Determine security level
    if len(context.security_keywords_found) >= 5:
        context.security_level = "critical"
    elif len(context.security_keywords_found) >= 2:
        context.security_level = "elevated"
    else:
        context.security_level = "standard"

    return context


def detect_dependencies_from_text(text: str) -> list[tuple[str, str, str]]:
    """
    Extract package dependencies from text (requirements.txt, package.json, etc.)
    """
    dependencies = []

    # Python: package==version or package>=version
    python_pattern = r'([a-zA-Z0-9_-]+)\s*[=><]+\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)'
    for match in re.finditer(python_pattern, text):
        pkg, version = match.groups()
        if pkg.lower() not in ['python', 'pip', 'version']:
            dependencies.append(("PyPI", pkg, version))

    # npm: "package": "^version" or "package": "version"
    npm_pattern = r'"([a-zA-Z0-9@/_-]+)"\s*:\s*"[\^~]?([0-9]+\.[0-9]+(?:\.[0-9]+)?)'
    for match in re.finditer(npm_pattern, text):
        pkg, version = match.groups()
        if not pkg.startswith('@types/'):
            dependencies.append(("npm", pkg, version))

    # Cargo.toml: package = "version"
    cargo_pattern = r'([a-zA-Z0-9_-]+)\s*=\s*"([0-9]+\.[0-9]+(?:\.[0-9]+)?)"'
    for match in re.finditer(cargo_pattern, text):
        pkg, version = match.groups()
        if pkg not in ['version', 'edition', 'name']:
            dependencies.append(("crates.io", pkg, version))

    return dependencies


# =============================================================================
# OSV.DEV API - CVE CHECKING
# =============================================================================

OSV_API_URL = "https://api.osv.dev/v1/querybatch"
OSV_TIMEOUT = 10


def fetch_vuln_details(vuln_id: str) -> Optional[dict]:
    """Fetch full vulnerability details from OSV.dev."""
    try:
        url = f"https://api.osv.dev/v1/vulns/{vuln_id}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return None


def parse_cvss_vector(cvss_string: str) -> str:
    """Parse CVSS vector string to determine severity level."""
    # CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H -> CRITICAL
    # Look for impact metrics: C (Confidentiality), I (Integrity), A (Availability)
    if not cvss_string:
        return "UNKNOWN"

    cvss_upper = cvss_string.upper()

    # Count high impacts
    high_impacts = cvss_upper.count("/C:H") + cvss_upper.count("/I:H") + cvss_upper.count("/A:H")
    low_impacts = cvss_upper.count("/C:L") + cvss_upper.count("/I:L") + cvss_upper.count("/A:L")

    # Check attack complexity and privileges
    easy_attack = "/AC:L" in cvss_upper and "/PR:N" in cvss_upper

    if high_impacts >= 2 and easy_attack:
        return "CRITICAL"
    elif high_impacts >= 2 or (high_impacts >= 1 and easy_attack):
        return "HIGH"
    elif high_impacts >= 1 or low_impacts >= 2:
        return "MEDIUM"
    else:
        return "LOW"


def check_cve_osv(dependencies: list[tuple[str, str, str]]) -> list[CVEInfo]:
    """Check for known vulnerabilities using OSV.dev API."""
    if not dependencies:
        return []

    queries = []
    for ecosystem, package, version in dependencies:
        queries.append({
            "package": {"name": package, "ecosystem": ecosystem},
            "version": version
        })

    try:
        data = json.dumps({"queries": queries}).encode('utf-8')
        req = urllib.request.Request(
            OSV_API_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=OSV_TIMEOUT) as response:
            result = json.loads(response.read().decode('utf-8'))

        cves = []
        seen_ids = set()  # Avoid duplicates

        for i, result_item in enumerate(result.get("results", [])):
            vulns = result_item.get("vulns", [])
            if vulns:
                ecosystem, package, version = dependencies[i]
                for vuln in vulns[:3]:  # Limit to 3 per package to avoid too many API calls
                    vuln_id = vuln.get("id", "")
                    if vuln_id in seen_ids:
                        continue
                    seen_ids.add(vuln_id)

                    # Fetch full details for severity
                    full_vuln = fetch_vuln_details(vuln_id)
                    if full_vuln:
                        cve = parse_osv_vulnerability(full_vuln, package)
                        if cve:
                            cves.append(cve)

        logger.info(f"OSV.dev: Checked {len(dependencies)} packages, found {len(cves)} vulnerabilities")
        return cves

    except urllib.error.URLError as e:
        logger.warning(f"OSV.dev API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error checking CVE: {e}")
        return []


def parse_osv_vulnerability(vuln: dict, package: str) -> Optional[CVEInfo]:
    """Parse OSV vulnerability response into CVEInfo."""
    try:
        vuln_id = vuln.get("id", "")
        aliases = vuln.get("aliases", [])
        cve_id = next((a for a in aliases if a.startswith("CVE-")), vuln_id)

        severity = "UNKNOWN"
        if "severity" in vuln and vuln["severity"]:
            for sev in vuln["severity"]:
                if sev.get("type") == "CVSS_V3":
                    score_raw = sev.get("score", "")
                    # Score can be a CVSS vector string like "CVSS:3.1/AV:N/AC:H/..."
                    if isinstance(score_raw, str) and "CVSS" in score_raw.upper():
                        severity = parse_cvss_vector(score_raw)
                    else:
                        # Try as numeric score
                        try:
                            score = float(str(score_raw).split("/")[0])
                            if score >= 9.0:
                                severity = "CRITICAL"
                            elif score >= 7.0:
                                severity = "HIGH"
                            elif score >= 4.0:
                                severity = "MEDIUM"
                            else:
                                severity = "LOW"
                        except (ValueError, TypeError):
                            severity = parse_cvss_vector(str(score_raw))
                    break

        affected_str = "unknown"
        fixed_version = None
        if "affected" in vuln:
            for affected in vuln["affected"]:
                if affected.get("package", {}).get("name", "").lower() == package.lower():
                    ranges = affected.get("ranges", [])
                    for r in ranges:
                        events = r.get("events", [])
                        for event in events:
                            if "fixed" in event:
                                fixed_version = event["fixed"]
                                break
                    versions = affected.get("versions", [])
                    if versions:
                        affected_str = f"{versions[0]} - {versions[-1]}" if len(versions) > 1 else versions[0]

        references = [ref.get("url", "") for ref in vuln.get("references", [])[:3]]

        return CVEInfo(
            id=cve_id,
            summary=vuln.get("summary", vuln.get("details", "No description")[:200]),
            severity=severity,
            package=package,
            affected_versions=affected_str,
            fixed_version=fixed_version,
            references=references
        )
    except Exception as e:
        logger.warning(f"Error parsing vulnerability: {e}")
        return None


def check_package_cve(package: str, version: str, ecosystem: str = "PyPI") -> list[CVEInfo]:
    """Check a single package for CVEs."""
    return check_cve_osv([(ecosystem, package, version)])


# =============================================================================
# SECURITY GUIDELINES
# =============================================================================

def get_security_guidelines(context: SecurityContext) -> str:
    """Generate security guidelines based on detected context."""
    if not context.is_dev:
        return ""

    lines = []
    lines.append("\n## CONTRAINTES DE SECURITE OBLIGATOIRES\n")

    if "python" in context.languages:
        lines.append("""### Python Security
- Utiliser `secrets` au lieu de `random` pour les tokens/mots de passe
- Parametrer les requetes SQL (pas de f-string dans les queries)
- Valider les inputs avec Pydantic ou dataclasses
- Eviter les fonctions d'execution dynamique avec des donnees utilisateur
- Utiliser `bcrypt` ou `argon2` pour les mots de passe""")

    if "javascript" in context.languages or "typescript" in context.languages:
        lines.append("""### JavaScript/TypeScript Security
- Echapper les outputs HTML (XSS prevention)
- Utiliser des requetes parametrees pour les bases de donnees
- Valider les inputs cote serveur (ne jamais faire confiance au client)
- Configurer CORS correctement
- Utiliser `helmet.js` pour les headers de securite""")

    if "rust" in context.languages:
        lines.append("""### Rust Security
- Preferer les types surs (`Option`, `Result`) aux valeurs nulles
- Utiliser `sqlx` avec requetes parametrees pour SQL
- Valider les inputs avec `validator` crate
- Utiliser `argon2` pour le hashing de mots de passe
- Eviter `unsafe` sauf si absolument necessaire""")

    if "go" in context.languages:
        lines.append("""### Go Security
- Utiliser `prepared statements` pour SQL
- Echapper les templates HTML avec `html/template`
- Valider les inputs avec `go-playground/validator`
- Utiliser `golang.org/x/crypto` pour la cryptographie
- Ne jamais logger les secrets/mots de passe""")

    if "java" in context.languages:
        lines.append("""### Java Security
- Utiliser `PreparedStatement` pour toutes les requetes SQL
- Bean Validation (JSR 380) pour valider les inputs
- Spring Security pour l'authentification/autorisation
- Eviter ObjectInputStream avec des donnees non fiables (deserialisation)
- Utiliser OWASP ESAPI pour l'encodage des outputs""")

    if "csharp" in context.languages:
        lines.append("""### C# / .NET Security
- Entity Framework ou Dapper avec requetes parametrees
- ASP.NET Core Identity pour l'authentification
- Anti-forgery tokens (ValidateAntiForgeryToken) pour les formulaires
- `HtmlEncoder` pour encoder les outputs HTML
- Data Protection API pour le chiffrement des donnees sensibles""")

    if "php" in context.languages:
        lines.append("""### PHP Security
- PDO avec requetes preparees (bindParam/bindValue)
- `password_hash()` / `password_verify()` pour les mots de passe
- `htmlspecialchars()` avec ENT_QUOTES pour l'echappement HTML
- Valider les uploads: verifier le MIME reel avec finfo_file()
- Utiliser CSRF tokens avec verification cote serveur""")

    if "ruby" in context.languages:
        lines.append("""### Ruby Security
- ActiveRecord avec requetes parametrees (where avec placeholders)
- `has_secure_password` pour le hashing de mots de passe
- Strong Parameters dans Rails pour filtrer les inputs
- Protection CSRF activee par defaut dans Rails
- Eviter `eval()`, `send()` avec des inputs utilisateur""")

    if "swift" in context.languages:
        lines.append("""### Swift / iOS Security
- Keychain pour stocker les credentials (pas UserDefaults)
- App Transport Security (ATS) active
- Certificate pinning pour les connexions sensibles
- Valider les inputs avant traitement
- Eviter les donnees sensibles dans les logs""")

    if "c" in context.languages or "cpp" in context.languages:
        lines.append("""### C/C++ Security
- Eviter les fonctions non-securisees: gets, strcpy, sprintf -> utiliser fgets, strncpy, snprintf
- Toujours verifier les bornes des buffers (buffer overflow)
- Initialiser toutes les variables avant utilisation
- Utiliser RAII en C++ pour la gestion memoire
- Activer les protections: -fstack-protector, -D_FORTIFY_SOURCE=2, -fPIE
- AddressSanitizer et MemorySanitizer pour detecter les erreurs memoire""")

    if any(k in context.security_keywords_found for k in ["auth", "login", "password", "jwt", "token"]):
        lines.append("""### Authentification
- Implementer rate limiting sur les endpoints d'auth
- Utiliser HTTPS uniquement
- Tokens JWT: expiration courte, refresh tokens, signature forte (RS256)
- Stocker les mots de passe avec bcrypt/argon2 (jamais MD5/SHA1)
- Implementer la protection CSRF""")

    if any(k in context.security_keywords_found for k in ["sql", "database", "query"]):
        lines.append("""### Base de donnees
- TOUJOURS utiliser des requetes parametrees (prepared statements)
- Principe du moindre privilege pour les acces DB
- Chiffrer les donnees sensibles au repos
- Valider et sanitizer les inputs avant insertion""")

    if any(k in context.security_keywords_found for k in ["file", "upload", "path"]):
        lines.append("""### Fichiers & Uploads
- Valider le type MIME et l'extension des fichiers uploades
- Limiter la taille des uploads
- Stocker hors du webroot avec noms generes
- Scanner les fichiers pour malware si possible
- Eviter les path traversal (../../)""")

    if any(k in context.security_keywords_found for k in ["api", "endpoint", "route"]):
        lines.append("""### API Security
- Authentification sur tous les endpoints sensibles
- Rate limiting et throttling
- Validation des inputs (schema validation)
- Headers de securite (CORS, CSP, X-Frame-Options)
- Logging des acces et erreurs""")

    # Framework-specific security guidelines
    if any(k in context.security_keywords_found for k in ["react", "vue", "angular", "frontend"]):
        lines.append("""### Frontend Framework Security (React/Vue/Angular)
- Echapper les donnees avec les mecanismes natifs du framework
- Ne jamais utiliser dangerouslySetInnerHTML (React) ou v-html (Vue) avec des inputs
- Valider les URLs avant navigation/redirection
- Sanitizer les inputs rich text avec DOMPurify
- Content Security Policy (CSP) pour bloquer les scripts inline
- Eviter eval() et les constructeurs dynamiques avec des donnees utilisateur""")

    if any(k in context.security_keywords_found for k in ["django", "flask", "fastapi"]):
        lines.append("""### Python Web Framework Security
- Django: CSRF_COOKIE_SECURE=True, SESSION_COOKIE_SECURE=True
- Django: Utiliser @login_required et @permission_required
- Flask: Utiliser Flask-WTF pour la protection CSRF
- FastAPI: Utiliser Depends() pour l'injection de dependances securisee
- Pydantic pour la validation stricte des schemas
- Ne jamais desactiver DEBUG en production""")

    if any(k in context.security_keywords_found for k in ["express", "nestjs", "node", "koa"]):
        lines.append("""### Node.js Framework Security
- Express: helmet.js pour les headers de securite
- Express: express-rate-limit pour le throttling
- NestJS: Guards et Pipes pour validation/autorisation
- Utiliser express-validator ou class-validator
- Configurer CORS strictement (pas de origin: '*' en production)
- PM2 ou similar pour le process management securise""")

    if any(k in context.security_keywords_found for k in ["spring", "springboot"]):
        lines.append("""### Spring Boot Security
- Spring Security avec configuration explicite
- @PreAuthorize et @Secured pour le controle d'acces
- BCryptPasswordEncoder pour le hashing
- CSRF protection activee pour les formulaires
- Configurer les headers de securite via HttpSecurity
- Valider avec @Valid et @Validated""")

    if any(k in context.security_keywords_found for k in ["aspnet", "blazor", "dotnet"]):
        lines.append("""### ASP.NET Core Security
- Identity pour l'authentification/autorisation
- [Authorize] attribute sur les controllers/actions
- Data Annotations pour la validation
- Anti-forgery tokens automatiques
- HTTPS redirection et HSTS
- Secret Manager pour les credentials en dev""")

    if context.cves:
        lines.append("\n### VULNERABILITES DETECTEES (CVE)")
        for cve in context.cves[:5]:
            sev_tag = {"CRITICAL": "[CRIT]", "HIGH": "[HIGH]", "MEDIUM": "[MED]", "LOW": "[LOW]"}.get(cve.severity, "[?]")
            lines.append(f"\n**{sev_tag} {cve.id}** - {cve.package}")
            lines.append(f"- Severite: {cve.severity}")
            lines.append(f"- {cve.summary[:150]}...")
            if cve.fixed_version:
                lines.append(f"- Corrige dans: {cve.fixed_version}")

    lines.append("""
### Rappel OWASP Top 10
Verifie que ton code n'est pas vulnerable a:
1. Broken Access Control
2. Cryptographic Failures
3. Injection (SQL, Command, XSS)
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable Components
7. Authentication Failures
8. Integrity Failures
9. Logging Failures
10. SSRF""")

    return "\n".join(lines)


def get_security_system_prompt_addition() -> str:
    """Returns additional system prompt text for security-focused reformatting."""
    return """
IMPORTANT - SECURITE DU CODE:
Tu generes du code qui sera utilise en production. La securite est CRITIQUE.
- Applique TOUJOURS les bonnes pratiques de securite
- Utilise des requetes parametrees pour toute interaction base de donnees
- Valide et sanitize TOUS les inputs utilisateur
- N'expose JAMAIS de secrets dans le code ou les logs
- Prefere les bibliotheques de securite eprouvees
- Si tu detectes un risque de securite, ALERTE explicitement dans ta reponse
"""


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

def enrich_prompt_with_security(
    raw_prompt: str,
    project_context: str = "",
    check_cves: bool = True
) -> tuple[str, SecurityContext]:
    """Analyze prompt and project, add security context if dev-related."""
    full_text = f"{raw_prompt}\n{project_context}"
    context = detect_dev_context(full_text)

    if not context.is_dev:
        return project_context, context

    if check_cves:
        dependencies = detect_dependencies_from_text(project_context)
        if dependencies:
            context.cves = check_cve_osv(dependencies)

    security_guidelines = get_security_guidelines(context)

    if project_context:
        enriched = f"{project_context}\n{security_guidelines}"
    else:
        enriched = security_guidelines

    return enriched, context


def format_cve_alert(cves: list[CVEInfo]) -> str:
    """Format CVE alerts for display in UI."""
    if not cves:
        return ""

    lines = ["## Vulnerabilites detectees\n"]

    critical = [c for c in cves if c.severity == "CRITICAL"]
    high = [c for c in cves if c.severity == "HIGH"]
    medium = [c for c in cves if c.severity == "MEDIUM"]
    low = [c for c in cves if c.severity == "LOW"]

    if critical:
        lines.append(f"### [CRITICAL] ({len(critical)})")
        for cve in critical:
            lines.append(f"- **{cve.id}**: {cve.package} - {cve.summary[:100]}")
            if cve.fixed_version:
                lines.append(f"  - Mettre a jour vers: `{cve.fixed_version}`")

    if high:
        lines.append(f"\n### [HIGH] ({len(high)})")
        for cve in high:
            lines.append(f"- **{cve.id}**: {cve.package} - {cve.summary[:100]}")

    if medium:
        lines.append(f"\n### [MEDIUM] ({len(medium)})")
        for cve in medium[:3]:
            lines.append(f"- **{cve.id}**: {cve.package}")
        if len(medium) > 3:
            lines.append(f"  - ... et {len(medium) - 3} autres")

    if low:
        lines.append(f"\n### [LOW] ({len(low)})")
        lines.append(f"- {len(low)} vulnerabilite(s) de faible severite")

    return "\n".join(lines)
