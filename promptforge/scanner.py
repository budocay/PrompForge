"""
Project Scanner - Automatic project analysis and configuration generation.

This module provides functionality to scan a project directory and automatically
detect languages, frameworks, databases, code conventions, tests, and infrastructure.
It generates a comprehensive Markdown configuration file for PromptForge.
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_IGNORE_PATTERNS = [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "htmlcov",
    ".idea",
    ".vscode",
    "*.egg-info",
    ".tox",
    ".nox",
    ".gradle",
    ".dart_tool",
    ".pub-cache",
]

LANGUAGE_EXTENSIONS = {
    "Python": [".py", ".pyw", ".pyi"],
    "TypeScript": [".ts", ".tsx"],
    "JavaScript": [".js", ".jsx", ".mjs", ".cjs"],
    "Go": [".go"],
    "Rust": [".rs"],
    "Java": [".java"],
    "Kotlin": [".kt", ".kts"],
    "C#": [".cs"],
    "C": [".c", ".h"],
    "C++": [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
    "Ruby": [".rb"],
    "PHP": [".php"],
    "Swift": [".swift"],
    "Scala": [".scala"],
    "Dart": [".dart"],
    "Vue": [".vue"],
    "Svelte": [".svelte"],
    "HTML": [".html", ".htm"],
    "CSS": [".css", ".scss", ".sass", ".less"],
    "SQL": [".sql"],
    "Shell": [".sh", ".bash", ".zsh"],
    "PowerShell": [".ps1", ".psm1"],
}

VERSION_FILES = {
    "Python": [
        ("pyproject.toml", r'python\s*=\s*["\']([^"\']+)["\']'),
        ("pyproject.toml", r'requires-python\s*=\s*["\']>=?([^"\']+)["\']'),
        (".python-version", r"^(\d+\.\d+(?:\.\d+)?)"),
        ("runtime.txt", r"python-(\d+\.\d+(?:\.\d+)?)"),
    ],
    "Node.js": [
        ("package.json", r'"node"\s*:\s*["\']([^"\']+)["\']'),
        (".nvmrc", r"^v?(\d+(?:\.\d+)*)"),
        (".node-version", r"^v?(\d+(?:\.\d+)*)"),
    ],
    "Go": [
        ("go.mod", r"^go\s+(\d+\.\d+)"),
    ],
    "Rust": [
        ("rust-toolchain.toml", r'channel\s*=\s*["\']([^"\']+)["\']'),
        ("rust-toolchain", r"^(\d+\.\d+(?:\.\d+)?)"),
    ],
    "Java": [
        ("pom.xml", r"<java\.version>(\d+(?:\.\d+)*)</java\.version>"),
        ("build.gradle", r"sourceCompatibility\s*=\s*['\"]?(\d+(?:\.\d+)*)['\"]?"),
    ],
}

FRAMEWORK_SIGNATURES = {
    # Python Backend
    "FastAPI": {
        "files": ["requirements.txt", "pyproject.toml", "setup.py"],
        "pattern": r"fastapi",
        "category": "backend",
    },
    "Django": {
        "files": ["requirements.txt", "pyproject.toml", "manage.py"],
        "pattern": r"django(?!-)",
        "category": "backend",
    },
    "Flask": {
        "files": ["requirements.txt", "pyproject.toml"],
        "pattern": r"flask(?!-)",
        "category": "backend",
    },
    "Starlette": {
        "files": ["requirements.txt", "pyproject.toml"],
        "pattern": r"starlette",
        "category": "backend",
    },
    # Python ORM
    "SQLAlchemy": {
        "files": ["requirements.txt", "pyproject.toml"],
        "pattern": r"sqlalchemy",
        "category": "orm",
    },
    "Tortoise ORM": {
        "files": ["requirements.txt", "pyproject.toml"],
        "pattern": r"tortoise-orm",
        "category": "orm",
    },
    "Peewee": {
        "files": ["requirements.txt", "pyproject.toml"],
        "pattern": r"peewee",
        "category": "orm",
    },
    # JavaScript/TypeScript Frontend
    "React": {
        "files": ["package.json"],
        "pattern": r'"react"\s*:',
        "category": "frontend",
    },
    "Vue": {
        "files": ["package.json"],
        "pattern": r'"vue"\s*:',
        "category": "frontend",
    },
    "Angular": {
        "files": ["package.json", "angular.json"],
        "pattern": r'"@angular/core"',
        "category": "frontend",
    },
    "Svelte": {
        "files": ["package.json"],
        "pattern": r'"svelte"\s*:',
        "category": "frontend",
    },
    "Next.js": {
        "files": ["package.json", "next.config.js", "next.config.mjs", "next.config.ts"],
        "pattern": r'"next"\s*:',
        "category": "frontend",
    },
    "Nuxt": {
        "files": ["package.json", "nuxt.config.ts", "nuxt.config.js"],
        "pattern": r'"nuxt"\s*:',
        "category": "frontend",
    },
    "Astro": {
        "files": ["package.json", "astro.config.mjs"],
        "pattern": r'"astro"\s*:',
        "category": "frontend",
    },
    # JavaScript/TypeScript Backend
    "Express": {
        "files": ["package.json"],
        "pattern": r'"express"\s*:',
        "category": "backend",
    },
    "NestJS": {
        "files": ["package.json"],
        "pattern": r'"@nestjs/core"',
        "category": "backend",
    },
    "Fastify": {
        "files": ["package.json"],
        "pattern": r'"fastify"\s*:',
        "category": "backend",
    },
    "Koa": {
        "files": ["package.json"],
        "pattern": r'"koa"\s*:',
        "category": "backend",
    },
    # Go
    "Gin": {
        "files": ["go.mod"],
        "pattern": r"github\.com/gin-gonic/gin",
        "category": "backend",
    },
    "Echo": {
        "files": ["go.mod"],
        "pattern": r"github\.com/labstack/echo",
        "category": "backend",
    },
    "Fiber": {
        "files": ["go.mod"],
        "pattern": r"github\.com/gofiber/fiber",
        "category": "backend",
    },
    # Rust
    "Actix Web": {
        "files": ["Cargo.toml"],
        "pattern": r"actix-web",
        "category": "backend",
    },
    "Rocket": {
        "files": ["Cargo.toml"],
        "pattern": r'rocket\s*=',
        "category": "backend",
    },
    "Axum": {
        "files": ["Cargo.toml"],
        "pattern": r'axum\s*=',
        "category": "backend",
    },
    # CSS/UI
    "TailwindCSS": {
        "files": ["tailwind.config.js", "tailwind.config.ts", "tailwind.config.cjs"],
        "pattern": None,
        "category": "ui",
    },
    "Bootstrap": {
        "files": ["package.json"],
        "pattern": r'"bootstrap"\s*:',
        "category": "ui",
    },
    "Material UI": {
        "files": ["package.json"],
        "pattern": r'"@mui/material"',
        "category": "ui",
    },
    "Chakra UI": {
        "files": ["package.json"],
        "pattern": r'"@chakra-ui/react"',
        "category": "ui",
    },
    # State Management
    "Redux": {
        "files": ["package.json"],
        "pattern": r'"redux"|"@reduxjs/toolkit"',
        "category": "state",
    },
    "Zustand": {
        "files": ["package.json"],
        "pattern": r'"zustand"\s*:',
        "category": "state",
    },
    "Pinia": {
        "files": ["package.json"],
        "pattern": r'"pinia"\s*:',
        "category": "state",
    },
    "MobX": {
        "files": ["package.json"],
        "pattern": r'"mobx"\s*:',
        "category": "state",
    },
    # Dart/Flutter
    "Flutter": {
        "files": ["pubspec.yaml"],
        "pattern": r"flutter:",
        "category": "mobile",
    },
    # Prisma
    "Prisma": {
        "files": ["schema.prisma", "package.json"],
        "pattern": r'"prisma"|"@prisma/client"',
        "category": "orm",
    },
}

DATABASE_SIGNATURES = {
    "PostgreSQL": {
        "docker": ["postgres", "postgresql"],
        "env_patterns": [r"POSTGRES_", r"DATABASE_URL.*postgres"],
        "packages": ["psycopg2", "psycopg", "asyncpg", "pg", "postgres"],
    },
    "MySQL": {
        "docker": ["mysql", "mariadb"],
        "env_patterns": [r"MYSQL_", r"DATABASE_URL.*mysql"],
        "packages": ["mysql-connector", "pymysql", "mysql2", "mysqlclient"],
    },
    "SQLite": {
        "files": ["*.sqlite", "*.db", "*.sqlite3"],
        "packages": ["sqlite3", "better-sqlite3"],
    },
    "MongoDB": {
        "docker": ["mongo", "mongodb"],
        "env_patterns": [r"MONGO_", r"MONGODB_URI"],
        "packages": ["pymongo", "mongoose", "mongodb", "motor"],
    },
    "Redis": {
        "docker": ["redis"],
        "env_patterns": [r"REDIS_"],
        "packages": ["redis", "ioredis", "aioredis"],
    },
    "Elasticsearch": {
        "docker": ["elasticsearch"],
        "packages": ["elasticsearch", "@elastic/elasticsearch"],
    },
}

TEST_SIGNATURES = {
    "pytest": {
        "files": ["pytest.ini", "conftest.py", "pyproject.toml"],
        "dirs": ["tests", "test"],
        "pattern": r"\[tool\.pytest|pytest",
        "category": "python",
    },
    "unittest": {
        "dirs": ["tests", "test"],
        "pattern": r"import unittest|from unittest",
        "category": "python",
    },
    "Jest": {
        "files": ["jest.config.js", "jest.config.ts", "jest.config.cjs", "package.json"],
        "dirs": ["__tests__", "tests"],
        "pattern": r'"jest"\s*:|"@types/jest"',
        "category": "javascript",
    },
    "Vitest": {
        "files": ["vitest.config.ts", "vitest.config.js", "package.json"],
        "pattern": r'"vitest"\s*:',
        "category": "javascript",
    },
    "Mocha": {
        "files": [".mocharc.js", ".mocharc.json", "package.json"],
        "pattern": r'"mocha"\s*:',
        "category": "javascript",
    },
    "Cypress": {
        "files": ["cypress.config.js", "cypress.config.ts", "cypress.json"],
        "dirs": ["cypress"],
        "pattern": r'"cypress"\s*:',
        "category": "e2e",
    },
    "Playwright": {
        "files": ["playwright.config.ts", "playwright.config.js"],
        "pattern": r'"@playwright/test"',
        "category": "e2e",
    },
    "Go Test": {
        "files": ["*_test.go"],
        "pattern": None,
        "category": "go",
    },
    "Cargo Test": {
        "files": ["Cargo.toml"],
        "dirs": ["tests"],
        "pattern": r"\[dev-dependencies\]",
        "category": "rust",
    },
}

CONVENTION_FILES = {
    # Python
    "pyproject.toml": {"tools": ["black", "ruff", "isort", "mypy"]},
    ".flake8": {"linter": "flake8"},
    "setup.cfg": {"tools": ["flake8", "mypy"]},
    ".pylintrc": {"linter": "pylint"},
    "ruff.toml": {"linter": "ruff"},
    ".ruff.toml": {"linter": "ruff"},
    ".mypy.ini": {"typechecker": "mypy"},
    # JavaScript/TypeScript
    ".prettierrc": {"formatter": "prettier"},
    ".prettierrc.json": {"formatter": "prettier"},
    ".prettierrc.js": {"formatter": "prettier"},
    ".prettierrc.cjs": {"formatter": "prettier"},
    "prettier.config.js": {"formatter": "prettier"},
    ".eslintrc": {"linter": "eslint"},
    ".eslintrc.json": {"linter": "eslint"},
    ".eslintrc.js": {"linter": "eslint"},
    ".eslintrc.cjs": {"linter": "eslint"},
    "eslint.config.js": {"linter": "eslint"},
    "eslint.config.mjs": {"linter": "eslint"},
    "biome.json": {"formatter": "biome", "linter": "biome"},
    "biome.jsonc": {"formatter": "biome", "linter": "biome"},
    # Go
    ".golangci.yml": {"linter": "golangci-lint"},
    ".golangci.yaml": {"linter": "golangci-lint"},
    # Rust
    "rustfmt.toml": {"formatter": "rustfmt"},
    ".rustfmt.toml": {"formatter": "rustfmt"},
    "clippy.toml": {"linter": "clippy"},
    # Editor
    ".editorconfig": {"editor": "editorconfig"},
}

CICD_SIGNATURES = {
    "GitHub Actions": {
        "path": ".github/workflows",
        "pattern": "*.yml",
    },
    "GitLab CI": {
        "files": [".gitlab-ci.yml"],
    },
    "CircleCI": {
        "path": ".circleci",
        "files": ["config.yml"],
    },
    "Jenkins": {
        "files": ["Jenkinsfile"],
    },
    "Azure Pipelines": {
        "files": ["azure-pipelines.yml"],
    },
    "Travis CI": {
        "files": [".travis.yml"],
    },
    "Bitbucket Pipelines": {
        "files": ["bitbucket-pipelines.yml"],
    },
}


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class DetectedLanguage:
    """Represents a detected programming language."""

    name: str
    extensions: list[str]
    file_count: int
    percentage: float
    version: Optional[str] = None


@dataclass
class DetectedFramework:
    """Represents a detected framework or library."""

    name: str
    category: str
    version: Optional[str] = None
    config_file: Optional[str] = None


@dataclass
class DetectedDatabase:
    """Represents detected database configuration."""

    name: str
    detected_from: str
    orm: Optional[str] = None


@dataclass
class CodeConventions:
    """Detected code conventions."""

    formatter: Optional[str] = None
    linter: Optional[str] = None
    typechecker: Optional[str] = None
    line_length: Optional[int] = None
    config_files: list[str] = field(default_factory=list)


@dataclass
class TestSetup:
    """Detected test configuration."""

    framework: Optional[str] = None
    category: Optional[str] = None
    test_dirs: list[str] = field(default_factory=list)
    config_file: Optional[str] = None


@dataclass
class DockerSetup:
    """Detected Docker configuration."""

    has_dockerfile: bool = False
    has_compose: bool = False
    services: list[str] = field(default_factory=list)
    compose_file: Optional[str] = None


@dataclass
class CICDSetup:
    """Detected CI/CD configuration."""

    provider: Optional[str] = None
    config_files: list[str] = field(default_factory=list)
    workflows: list[str] = field(default_factory=list)


@dataclass
class ProjectStructure:
    """Directory tree representation."""

    root_name: str
    directories: list[str]
    tree_string: str
    total_dirs: int = 0
    total_files: int = 0


@dataclass
class ScanResult:
    """Complete scan result."""

    languages: list[DetectedLanguage] = field(default_factory=list)
    frameworks: list[DetectedFramework] = field(default_factory=list)
    databases: list[DetectedDatabase] = field(default_factory=list)
    structure: Optional[ProjectStructure] = None
    conventions: Optional[CodeConventions] = None
    tests: list[TestSetup] = field(default_factory=list)
    docker: Optional[DockerSetup] = None
    cicd: Optional[CICDSetup] = None
    readme_description: Optional[str] = None
    project_name_suggestion: Optional[str] = None
    scan_duration_ms: int = 0
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)


# =============================================================================
# PROJECT SCANNER
# =============================================================================


class ProjectScanner:
    """
    Scans a project directory and detects languages, frameworks, and configurations.
    """

    def __init__(
        self,
        max_depth: int = 3,
        max_files: int = 10000,
        timeout_seconds: int = 30,
        ignore_patterns: Optional[list[str]] = None,
    ):
        """
        Initialize the scanner.

        Args:
            max_depth: Maximum directory depth to scan
            max_files: Maximum number of files to scan
            timeout_seconds: Maximum scan duration
            ignore_patterns: Patterns to ignore (defaults to DEFAULT_IGNORE_PATTERNS)
        """
        self.max_depth = max_depth
        self.max_files = max_files
        self.timeout_seconds = timeout_seconds
        self.ignore_patterns = ignore_patterns or DEFAULT_IGNORE_PATTERNS

        self._files_scanned = 0
        self._start_time: Optional[float] = None
        self._errors: list[str] = []
        self._file_cache: dict[str, str] = {}

    def scan(self, path: Path) -> ScanResult:
        """
        Scan a project directory and return results.

        Args:
            path: Path to the project directory

        Returns:
            ScanResult with all detected information
        """
        self._start_time = time.time()
        self._files_scanned = 0
        self._errors = []
        self._file_cache = {}

        path = Path(path).resolve()

        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        result = ScanResult()
        result.project_name_suggestion = path.name

        # Scan in order of importance
        result.structure = self._scan_structure(path)
        result.languages = self._scan_languages(path)
        result.frameworks = self._scan_frameworks(path)
        result.databases = self._scan_databases(path)
        result.conventions = self._scan_conventions(path)
        result.tests = self._scan_tests(path)
        result.docker = self._scan_docker(path)
        result.cicd = self._scan_cicd(path)
        result.readme_description = self._extract_description(path)

        # Final stats
        result.files_scanned = self._files_scanned
        result.scan_duration_ms = int((time.time() - self._start_time) * 1000)
        result.errors = self._errors

        return result

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        name = path.name
        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False

    def _should_continue(self) -> bool:
        """Check if scanning should continue."""
        if self._files_scanned >= self.max_files:
            return False
        if self._start_time and (time.time() - self._start_time) > self.timeout_seconds:
            return False
        return True

    def _safe_read_file(self, path: Path, max_size: int = 1024 * 1024) -> Optional[str]:
        """Read file safely with error handling."""
        str_path = str(path)
        if str_path in self._file_cache:
            return self._file_cache[str_path]

        try:
            if path.stat().st_size > max_size:
                return None
            content = path.read_text(encoding="utf-8", errors="ignore")
            self._file_cache[str_path] = content
            return content
        except PermissionError:
            self._errors.append(f"Permission denied: {path}")
            return None
        except Exception as e:
            self._errors.append(f"Error reading {path}: {e}")
            return None

    def _walk_files(self, path: Path, depth: int = 0):
        """Walk directory yielding files."""
        if depth > self.max_depth or not self._should_continue():
            return

        try:
            for item in path.iterdir():
                if self._should_ignore(item):
                    continue

                if item.is_file():
                    self._files_scanned += 1
                    yield item
                elif item.is_dir():
                    yield from self._walk_files(item, depth + 1)
        except PermissionError:
            self._errors.append(f"Permission denied: {path}")

    def _scan_structure(self, path: Path) -> ProjectStructure:
        """Scan and build directory structure."""
        directories = []
        total_files = 0
        total_dirs = 0

        def build_tree(p: Path, prefix: str = "", depth: int = 0) -> list[str]:
            nonlocal total_files, total_dirs
            lines = []

            if depth > self.max_depth:
                return lines

            try:
                items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                items = [i for i in items if not self._should_ignore(i)]

                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    connector = "└── " if is_last else "├── "
                    extension = "    " if is_last else "│   "

                    if item.is_dir():
                        total_dirs += 1
                        lines.append(f"{prefix}{connector}{item.name}/")
                        if depth == 0:
                            directories.append(item.name)
                        lines.extend(build_tree(item, prefix + extension, depth + 1))
                    else:
                        total_files += 1
                        lines.append(f"{prefix}{connector}{item.name}")

            except PermissionError:
                pass

            return lines

        tree_lines = build_tree(path)
        tree_string = f"{path.name}/\n" + "\n".join(tree_lines[:100])  # Limit output

        if len(tree_lines) > 100:
            tree_string += f"\n... et {len(tree_lines) - 100} autres fichiers/dossiers"

        return ProjectStructure(
            root_name=path.name,
            directories=directories,
            tree_string=tree_string,
            total_dirs=total_dirs,
            total_files=total_files,
        )

    def _scan_languages(self, path: Path) -> list[DetectedLanguage]:
        """Detect programming languages used."""
        extension_counts: dict[str, int] = {}

        for file in self._walk_files(path):
            ext = file.suffix.lower()
            if ext:
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

        # Map extensions to languages
        language_counts: dict[str, tuple[list[str], int]] = {}

        for lang, exts in LANGUAGE_EXTENSIONS.items():
            count = sum(extension_counts.get(ext, 0) for ext in exts)
            if count > 0:
                found_exts = [ext for ext in exts if extension_counts.get(ext, 0) > 0]
                language_counts[lang] = (found_exts, count)

        # Calculate percentages and detect versions
        total_files = sum(count for _, count in language_counts.values())
        languages = []

        for lang, (exts, count) in sorted(
            language_counts.items(), key=lambda x: x[1][1], reverse=True
        ):
            percentage = (count / total_files * 100) if total_files > 0 else 0
            version = self._detect_language_version(path, lang)

            languages.append(
                DetectedLanguage(
                    name=lang,
                    extensions=exts,
                    file_count=count,
                    percentage=round(percentage, 1),
                    version=version,
                )
            )

        return languages

    def _detect_language_version(self, path: Path, language: str) -> Optional[str]:
        """Try to detect language version from config files."""
        if language not in VERSION_FILES:
            return None

        for filename, pattern in VERSION_FILES[language]:
            file_path = path / filename
            if file_path.exists():
                content = self._safe_read_file(file_path)
                if content:
                    match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
                    if match:
                        return match.group(1)
        return None

    def _scan_frameworks(self, path: Path) -> list[DetectedFramework]:
        """Detect frameworks and libraries."""
        frameworks = []

        for fw_name, signature in FRAMEWORK_SIGNATURES.items():
            detected = False
            config_file = None

            # Check for signature files
            for filename in signature.get("files", []):
                file_path = path / filename
                if file_path.exists():
                    if signature.get("pattern"):
                        content = self._safe_read_file(file_path)
                        if content and re.search(
                            signature["pattern"], content, re.IGNORECASE
                        ):
                            detected = True
                            config_file = filename
                            break
                    else:
                        # File existence is enough
                        detected = True
                        config_file = filename
                        break

            if detected:
                frameworks.append(
                    DetectedFramework(
                        name=fw_name,
                        category=signature.get("category", "other"),
                        config_file=config_file,
                    )
                )

        return frameworks

    def _scan_databases(self, path: Path) -> list[DetectedDatabase]:
        """Detect database configurations."""
        databases = []
        detected_orms = []

        # First, detect ORMs from frameworks
        for fw in self._scan_frameworks(path):
            if fw.category == "orm":
                detected_orms.append(fw.name)

        # Check docker-compose for database services
        compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
        for compose_file in compose_files:
            compose_path = path / compose_file
            if compose_path.exists():
                content = self._safe_read_file(compose_path)
                if content:
                    for db_name, signature in DATABASE_SIGNATURES.items():
                        for docker_name in signature.get("docker", []):
                            if docker_name in content.lower():
                                databases.append(
                                    DetectedDatabase(
                                        name=db_name,
                                        detected_from=compose_file,
                                        orm=detected_orms[0] if detected_orms else None,
                                    )
                                )
                                break

        # Check .env files
        env_files = [".env", ".env.example", ".env.local", ".env.development"]
        for env_file in env_files:
            env_path = path / env_file
            if env_path.exists():
                content = self._safe_read_file(env_path)
                if content:
                    for db_name, signature in DATABASE_SIGNATURES.items():
                        if db_name not in [d.name for d in databases]:
                            for pattern in signature.get("env_patterns", []):
                                if re.search(pattern, content, re.IGNORECASE):
                                    databases.append(
                                        DetectedDatabase(
                                            name=db_name,
                                            detected_from=env_file,
                                            orm=detected_orms[0] if detected_orms else None,
                                        )
                                    )
                                    break

        # Check package files for database packages
        package_files = {
            "requirements.txt": None,
            "pyproject.toml": None,
            "package.json": None,
            "Cargo.toml": None,
            "go.mod": None,
        }

        for pkg_file in package_files:
            pkg_path = path / pkg_file
            if pkg_path.exists():
                content = self._safe_read_file(pkg_path)
                if content:
                    for db_name, signature in DATABASE_SIGNATURES.items():
                        if db_name not in [d.name for d in databases]:
                            for pkg in signature.get("packages", []):
                                if pkg.lower() in content.lower():
                                    databases.append(
                                        DetectedDatabase(
                                            name=db_name,
                                            detected_from=pkg_file,
                                            orm=detected_orms[0] if detected_orms else None,
                                        )
                                    )
                                    break

        return databases

    def _scan_conventions(self, path: Path) -> CodeConventions:
        """Detect code conventions and formatting tools."""
        conventions = CodeConventions()
        config_files = []

        for filename, info in CONVENTION_FILES.items():
            file_path = path / filename
            if file_path.exists():
                config_files.append(filename)

                if "formatter" in info and not conventions.formatter:
                    conventions.formatter = info["formatter"]
                if "linter" in info and not conventions.linter:
                    conventions.linter = info["linter"]
                if "typechecker" in info and not conventions.typechecker:
                    conventions.typechecker = info["typechecker"]

        # Parse pyproject.toml for more details
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            content = self._safe_read_file(pyproject_path)
            if content:
                if "[tool.black]" in content:
                    conventions.formatter = "black"
                    # Try to extract line-length
                    match = re.search(r"line-length\s*=\s*(\d+)", content)
                    if match:
                        conventions.line_length = int(match.group(1))
                if "[tool.ruff]" in content:
                    conventions.linter = "ruff"
                if "[tool.isort]" in content and not conventions.formatter:
                    conventions.formatter = "isort"
                if "[tool.mypy]" in content:
                    conventions.typechecker = "mypy"

        conventions.config_files = config_files
        return conventions

    def _scan_tests(self, path: Path) -> list[TestSetup]:
        """Detect test frameworks and configuration."""
        tests = []

        for test_name, signature in TEST_SIGNATURES.items():
            detected = False
            config_file = None
            test_dirs = []

            # Check for test directories
            for dir_name in signature.get("dirs", []):
                dir_path = path / dir_name
                if dir_path.exists() and dir_path.is_dir():
                    test_dirs.append(dir_name)
                    detected = True

            # Check for config files
            for filename in signature.get("files", []):
                if "*" in filename:
                    # Glob pattern
                    for file_path in path.glob(filename):
                        detected = True
                        config_file = file_path.name
                        break
                else:
                    file_path = path / filename
                    if file_path.exists():
                        if signature.get("pattern"):
                            content = self._safe_read_file(file_path)
                            if content and re.search(
                                signature["pattern"], content, re.IGNORECASE
                            ):
                                detected = True
                                config_file = filename
                        else:
                            detected = True
                            config_file = filename

            if detected:
                tests.append(
                    TestSetup(
                        framework=test_name,
                        category=signature.get("category"),
                        test_dirs=test_dirs,
                        config_file=config_file,
                    )
                )

        return tests

    def _scan_docker(self, path: Path) -> DockerSetup:
        """Detect Docker configuration."""
        docker = DockerSetup()

        # Check for Dockerfile
        dockerfile_variants = ["Dockerfile", "dockerfile"]
        for variant in dockerfile_variants:
            if (path / variant).exists():
                docker.has_dockerfile = True
                break

        # Also check for Dockerfile.* variants
        for file in path.glob("Dockerfile.*"):
            docker.has_dockerfile = True
            break

        # Check for docker-compose
        compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
        for compose_file in compose_files:
            compose_path = path / compose_file
            if compose_path.exists():
                docker.has_compose = True
                docker.compose_file = compose_file

                # Extract services
                content = self._safe_read_file(compose_path)
                if content:
                    # Simple service extraction
                    services_match = re.findall(
                        r"^\s{2}(\w[\w-]*):\s*$", content, re.MULTILINE
                    )
                    if services_match:
                        docker.services = services_match
                break

        return docker

    def _scan_cicd(self, path: Path) -> CICDSetup:
        """Detect CI/CD configuration."""
        cicd = CICDSetup()

        for provider, signature in CICD_SIGNATURES.items():
            detected = False
            config_files = []
            workflows = []

            # Check path-based configs (like .github/workflows/)
            if "path" in signature:
                cicd_path = path / signature["path"]
                if cicd_path.exists() and cicd_path.is_dir():
                    detected = True
                    pattern = signature.get("pattern", "*")
                    for file in cicd_path.glob(pattern):
                        config_files.append(str(file.relative_to(path)))
                        workflows.append(file.stem)

            # Check file-based configs
            for filename in signature.get("files", []):
                file_path = path / filename
                if file_path.exists():
                    detected = True
                    config_files.append(filename)

            if detected:
                cicd.provider = provider
                cicd.config_files = config_files
                cicd.workflows = workflows
                break

        return cicd

    def _extract_description(self, path: Path) -> Optional[str]:
        """Try to extract project description from README."""
        readme_files = ["README.md", "README.rst", "README.txt", "README"]

        for readme_file in readme_files:
            readme_path = path / readme_file
            if readme_path.exists():
                content = self._safe_read_file(readme_path)
                if content:
                    # Skip badges and title
                    lines = content.split("\n")
                    description_lines = []
                    in_description = False
                    skip_next = False

                    for line in lines:
                        # Skip badges
                        if "![" in line or "[![" in line:
                            continue
                        # Skip title
                        if line.startswith("# "):
                            skip_next = True
                            continue
                        if skip_next and not line.strip():
                            skip_next = False
                            continue

                        # Start collecting description
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            in_description = True
                            description_lines.append(stripped)
                        elif in_description and not stripped:
                            # End of first paragraph
                            break

                        if len(description_lines) >= 3:
                            break

                    if description_lines:
                        return " ".join(description_lines[:3])

        return None

    def generate_config(
        self,
        result: ScanResult,
        project_name: str,
        description: Optional[str] = None,
    ) -> str:
        """
        Generate a Markdown configuration file from scan results.

        Args:
            result: The ScanResult from scanning
            project_name: Name for the project
            description: Optional description (uses README extraction if not provided)

        Returns:
            Markdown string ready to save
        """
        lines = [f"# {project_name}"]
        lines.append("")

        # Description
        desc = description or result.readme_description or "Description du projet."
        lines.append("## Description")
        lines.append("")
        lines.append(desc)
        lines.append("")

        # Stack Technique
        lines.append("---")
        lines.append("")
        lines.append("## Stack Technique")
        lines.append("")

        # Languages
        if result.languages:
            lines.append("### Langages")
            lines.append("")
            lines.append("| Langage | Version | Fichiers | % |")
            lines.append("|---------|---------|----------|---|")
            for lang in result.languages[:5]:
                version = lang.version or "-"
                lines.append(
                    f"| **{lang.name}** | {version} | {lang.file_count} | {lang.percentage}% |"
                )
            lines.append("")

        # Frameworks by category
        if result.frameworks:
            by_category: dict[str, list[DetectedFramework]] = {}
            for fw in result.frameworks:
                by_category.setdefault(fw.category, []).append(fw)

            category_labels = {
                "backend": "Backend",
                "frontend": "Frontend",
                "orm": "ORM / Base de donnees",
                "ui": "UI / Styling",
                "state": "State Management",
                "mobile": "Mobile",
                "other": "Autres",
            }

            for category, fws in by_category.items():
                label = category_labels.get(category, category.title())
                lines.append(f"### {label}")
                lines.append("")
                for fw in fws:
                    lines.append(f"- **{fw.name}**")
                lines.append("")

        # Databases
        if result.databases:
            lines.append("### Base de donnees")
            lines.append("")
            for db in result.databases:
                orm_str = f" (ORM: {db.orm})" if db.orm else ""
                lines.append(f"- **{db.name}**{orm_str}")
            lines.append("")

        # Infrastructure
        if result.docker and (result.docker.has_dockerfile or result.docker.has_compose):
            lines.append("### Infrastructure")
            lines.append("")
            if result.docker.has_dockerfile:
                lines.append("- Docker: Oui")
            if result.docker.has_compose:
                services_str = ", ".join(result.docker.services[:5]) if result.docker.services else ""
                lines.append(f"- Docker Compose: {result.docker.compose_file}")
                if services_str:
                    lines.append(f"- Services: {services_str}")
            lines.append("")

        # CI/CD
        if result.cicd and result.cicd.provider:
            lines.append("### CI/CD")
            lines.append("")
            lines.append(f"- Provider: **{result.cicd.provider}**")
            if result.cicd.workflows:
                lines.append(f"- Workflows: {', '.join(result.cicd.workflows[:5])}")
            lines.append("")

        # Structure
        lines.append("---")
        lines.append("")
        lines.append("## Structure du Projet")
        lines.append("")
        lines.append("```")
        if result.structure:
            lines.append(result.structure.tree_string)
        lines.append("```")
        lines.append("")

        # Conventions
        if result.conventions:
            lines.append("---")
            lines.append("")
            lines.append("## Conventions de Code")
            lines.append("")
            if result.conventions.formatter:
                lines.append(f"- **Formatter**: {result.conventions.formatter}")
            if result.conventions.linter:
                lines.append(f"- **Linter**: {result.conventions.linter}")
            if result.conventions.typechecker:
                lines.append(f"- **Type Checker**: {result.conventions.typechecker}")
            if result.conventions.line_length:
                lines.append(f"- **Longueur de ligne**: {result.conventions.line_length}")
            if result.conventions.config_files:
                lines.append(f"- **Fichiers de config**: {', '.join(result.conventions.config_files)}")
            lines.append("")

        # Tests
        if result.tests:
            lines.append("---")
            lines.append("")
            lines.append("## Tests")
            lines.append("")
            for test in result.tests:
                dirs_str = f" ({', '.join(test.test_dirs)})" if test.test_dirs else ""
                lines.append(f"- **{test.framework}**{dirs_str}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        lines.append(f"- Configuration generee automatiquement par PromptForge Scanner")
        lines.append(f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"- Fichiers scannes: {result.files_scanned}")
        lines.append(f"- Duree du scan: {result.scan_duration_ms}ms")

        if result.errors:
            lines.append("")
            lines.append("### Erreurs de scan")
            lines.append("")
            for error in result.errors[:5]:
                lines.append(f"- {error}")

        return "\n".join(lines)


# =============================================================================
# PUBLIC API
# =============================================================================


def scan_directory(
    path: str | Path,
    max_depth: int = 3,
    max_files: int = 10000,
) -> ScanResult:
    """
    Convenience function to scan a directory.

    Args:
        path: Directory path to scan
        max_depth: Maximum directory depth (default: 3)
        max_files: Maximum files to scan (default: 10000)

    Returns:
        ScanResult with all detected information
    """
    scanner = ProjectScanner(max_depth=max_depth, max_files=max_files)
    return scanner.scan(Path(path))
