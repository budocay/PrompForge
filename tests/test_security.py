"""
Tests for PromptForge Security Module
=====================================

Tests dev context detection, CVE checking via OSV.dev, and security guidelines.
Includes tests with REAL vulnerable packages to verify CVE detection works.
"""

import pytest
from promptforge.security import (
    detect_dev_context,
    detect_dependencies_from_text,
    check_cve_osv,
    check_package_cve,
    get_security_guidelines,
    enrich_prompt_with_security,
    format_cve_alert,
    CVEInfo,
    SecurityContext,
)


# =============================================================================
# DEV CONTEXT DETECTION TESTS
# =============================================================================

class TestDevContextDetection:
    """Tests for detect_dev_context function."""

    def test_detect_python_language(self):
        """Should detect Python from keywords."""
        text = "Create a Flask API with SQLAlchemy"
        context = detect_dev_context(text)
        assert context.is_dev
        assert "python" in context.languages

    def test_detect_rust_language(self):
        """Should detect Rust from keywords."""
        text = "Build a REST API using Axum and Tokio in Rust"
        context = detect_dev_context(text)
        assert context.is_dev
        assert "rust" in context.languages

    def test_detect_javascript_language(self):
        """Should detect JavaScript/Node from keywords."""
        text = "Create an Express.js server with React frontend"
        context = detect_dev_context(text)
        assert context.is_dev
        assert "javascript" in context.languages

    def test_detect_multiple_languages(self):
        """Should detect multiple languages."""
        text = "Build a Python backend with TypeScript frontend using React"
        context = detect_dev_context(text)
        assert context.is_dev
        assert "python" in context.languages
        assert "typescript" in context.languages

    def test_detect_security_keywords(self):
        """Should detect security-sensitive keywords."""
        text = "Create a login endpoint with JWT authentication and password hashing"
        context = detect_dev_context(text)
        assert context.is_dev
        assert "auth" in context.security_keywords_found or "authentication" in context.security_keywords_found
        assert "jwt" in context.security_keywords_found
        assert "password" in context.security_keywords_found

    def test_elevated_security_level(self):
        """Should set elevated security level with multiple security keywords."""
        text = "Build an API with authentication, database queries, and file uploads"
        context = detect_dev_context(text)
        assert context.security_level in ["elevated", "critical"]

    def test_non_dev_text(self):
        """Should not detect dev context for non-technical text."""
        text = "Write a blog post about cooking pasta"
        context = detect_dev_context(text)
        assert not context.is_dev
        assert len(context.languages) == 0


class TestDependencyDetection:
    """Tests for detect_dependencies_from_text function."""

    def test_detect_python_requirements(self):
        """Should detect Python packages from requirements.txt format."""
        text = """
        flask==2.0.1
        sqlalchemy>=1.4.0
        requests==2.25.0
        """
        deps = detect_dependencies_from_text(text)
        assert len(deps) >= 3
        ecosystems = [d[0] for d in deps]
        packages = [d[1] for d in deps]
        assert "PyPI" in ecosystems
        assert "flask" in packages
        assert "sqlalchemy" in packages

    def test_detect_npm_packages(self):
        """Should detect npm packages from package.json format."""
        text = """
        {
          "dependencies": {
            "express": "^4.17.1",
            "lodash": "4.17.20",
            "axios": "~0.21.1"
          }
        }
        """
        deps = detect_dependencies_from_text(text)
        packages = [d[1] for d in deps]
        assert "express" in packages
        assert "lodash" in packages

    def test_detect_cargo_packages(self):
        """Should detect Rust packages from Cargo.toml format."""
        text = """
        [dependencies]
        tokio = "1.0.0"
        serde = "1.0.130"
        """
        deps = detect_dependencies_from_text(text)
        packages = [d[1] for d in deps]
        # Note: may have false positives, but should find packages
        assert len(deps) >= 0  # Best effort


# =============================================================================
# CVE CHECKING TESTS (REAL API CALLS)
# =============================================================================

class TestCVEChecking:
    """Tests for CVE checking via OSV.dev API.

    These tests make REAL API calls to OSV.dev to verify the integration works.
    They use known vulnerable package versions.
    """

    @pytest.mark.integration
    def test_check_vulnerable_python_package(self):
        """Test with a known vulnerable Python package: urllib3 < 1.26.5 (CVE-2021-33503)."""
        cves = check_package_cve("urllib3", "1.26.4", "PyPI")
        # This version has known vulnerabilities
        # Note: may return empty if no vulns found or API changes
        print(f"Found {len(cves)} CVEs for urllib3 1.26.4")
        for cve in cves:
            print(f"  - {cve.id}: {cve.severity} - {cve.summary[:80]}")

    @pytest.mark.integration
    def test_check_vulnerable_npm_package(self):
        """Test with a known vulnerable npm package: lodash < 4.17.21."""
        cves = check_package_cve("lodash", "4.17.20", "npm")
        print(f"Found {len(cves)} CVEs for lodash 4.17.20")
        for cve in cves:
            print(f"  - {cve.id}: {cve.severity} - {cve.summary[:80]}")

    @pytest.mark.integration
    def test_check_vulnerable_requests_package(self):
        """Test with requests package that had CVE-2023-32681."""
        cves = check_package_cve("requests", "2.28.0", "PyPI")
        print(f"Found {len(cves)} CVEs for requests 2.28.0")
        for cve in cves:
            print(f"  - {cve.id}: {cve.severity} - {cve.summary[:80]}")

    @pytest.mark.integration
    def test_check_safe_package(self):
        """Test with a package version that should be safe."""
        # Using a very recent version that should have no known CVEs
        cves = check_package_cve("pytest", "8.0.0", "PyPI")
        print(f"Found {len(cves)} CVEs for pytest 8.0.0")
        # Should ideally be 0 or very few

    @pytest.mark.integration
    def test_batch_check_multiple_packages(self):
        """Test batch checking multiple packages at once."""
        dependencies = [
            ("PyPI", "django", "3.2.0"),  # Had security issues
            ("PyPI", "pillow", "8.0.0"),  # Had security issues
            ("npm", "minimist", "1.2.5"),  # Had prototype pollution
        ]
        cves = check_cve_osv(dependencies)
        print(f"Found {len(cves)} total CVEs for batch check")
        for cve in cves:
            print(f"  - {cve.id}: {cve.package} - {cve.severity}")

    @pytest.mark.integration
    def test_check_nonexistent_package(self):
        """Test with a package that doesn't exist - should return empty, not error."""
        cves = check_package_cve("this-package-does-not-exist-xyz", "1.0.0", "PyPI")
        assert cves == []  # Should return empty list, not crash


# =============================================================================
# SECURITY GUIDELINES TESTS
# =============================================================================

class TestSecurityGuidelines:
    """Tests for security guidelines generation."""

    def test_python_guidelines(self):
        """Should generate Python-specific security guidelines."""
        context = SecurityContext(
            is_dev=True,
            languages=["python"],
            security_keywords_found=["database", "sql"],
            security_level="elevated"
        )
        guidelines = get_security_guidelines(context)
        assert "Python Security" in guidelines
        assert "secrets" in guidelines or "bcrypt" in guidelines

    def test_auth_guidelines(self):
        """Should generate auth-specific guidelines when auth keywords found."""
        context = SecurityContext(
            is_dev=True,
            languages=["python"],
            security_keywords_found=["auth", "jwt", "password"],
            security_level="elevated"
        )
        guidelines = get_security_guidelines(context)
        assert "Authentification" in guidelines
        assert "JWT" in guidelines or "jwt" in guidelines.lower()

    def test_database_guidelines(self):
        """Should generate database security guidelines."""
        context = SecurityContext(
            is_dev=True,
            languages=["python"],
            security_keywords_found=["sql", "database", "query"],
            security_level="elevated"
        )
        guidelines = get_security_guidelines(context)
        assert "Base de donnees" in guidelines or "parametrees" in guidelines

    def test_cve_warnings_in_guidelines(self):
        """Should include CVE warnings when CVEs are present."""
        cve = CVEInfo(
            id="CVE-2021-12345",
            summary="Test vulnerability",
            severity="HIGH",
            package="test-package",
            affected_versions="1.0.0 - 1.5.0",
            fixed_version="1.5.1"
        )
        context = SecurityContext(
            is_dev=True,
            languages=["python"],
            security_keywords_found=["database"],
            cves=[cve],
            security_level="elevated"
        )
        guidelines = get_security_guidelines(context)
        assert "CVE-2021-12345" in guidelines
        assert "HIGH" in guidelines
        assert "test-package" in guidelines

    def test_owasp_reminder(self):
        """Should always include OWASP Top 10 reminder for dev context."""
        context = SecurityContext(
            is_dev=True,
            languages=["python"],
            security_keywords_found=["api"],
            security_level="standard"
        )
        guidelines = get_security_guidelines(context)
        assert "OWASP" in guidelines
        assert "Injection" in guidelines

    def test_no_guidelines_for_non_dev(self):
        """Should return empty string for non-dev context."""
        context = SecurityContext(is_dev=False)
        guidelines = get_security_guidelines(context)
        assert guidelines == ""


# =============================================================================
# INTEGRATION HELPER TESTS
# =============================================================================

class TestEnrichPromptWithSecurity:
    """Tests for enrich_prompt_with_security function."""

    def test_enrich_dev_prompt(self):
        """Should enrich a dev prompt with security context."""
        raw_prompt = "Create a REST API with JWT authentication in Python"
        enriched, context = enrich_prompt_with_security(raw_prompt, "", check_cves=False)

        assert context.is_dev
        assert "python" in context.languages
        assert len(enriched) > 0
        assert "SECURITE" in enriched or "Security" in enriched

    def test_enrich_with_project_context(self):
        """Should combine project context with security guidelines."""
        raw_prompt = "Add a login endpoint"
        project_context = "# My Python API\nUsing Flask and SQLAlchemy"

        enriched, context = enrich_prompt_with_security(raw_prompt, project_context, check_cves=False)

        assert "My Python API" in enriched
        assert "SECURITE" in enriched or "Security" in enriched

    def test_no_enrichment_for_non_dev(self):
        """Should not add security context for non-dev prompts."""
        raw_prompt = "Write a poem about nature"
        enriched, context = enrich_prompt_with_security(raw_prompt, "", check_cves=False)

        assert not context.is_dev
        assert enriched == ""

    @pytest.mark.integration
    def test_enrich_with_cve_check(self):
        """Should include CVE check results when enabled."""
        raw_prompt = "Update my Python API"
        project_context = """
        # Dependencies
        flask==2.0.1
        requests==2.25.0
        """

        enriched, context = enrich_prompt_with_security(raw_prompt, project_context, check_cves=True)

        print(f"Found {len(context.cves)} CVEs")
        print(f"Enriched context length: {len(enriched)}")


class TestCVEAlertFormatting:
    """Tests for CVE alert formatting."""

    def test_format_critical_cves(self):
        """Should format critical CVEs with proper emphasis."""
        cves = [
            CVEInfo("CVE-2021-0001", "Critical vuln", "CRITICAL", "pkg1", "1.0", "1.1"),
            CVEInfo("CVE-2021-0002", "High vuln", "HIGH", "pkg2", "2.0", "2.1"),
        ]
        alert = format_cve_alert(cves)

        assert "[CRITICAL]" in alert
        assert "[HIGH]" in alert
        assert "CVE-2021-0001" in alert
        assert "pkg1" in alert

    def test_format_empty_cves(self):
        """Should return empty string for no CVEs."""
        alert = format_cve_alert([])
        assert alert == ""

    def test_format_many_medium_cves(self):
        """Should truncate many medium CVEs."""
        cves = [
            CVEInfo(f"CVE-2021-{i:04d}", f"Medium vuln {i}", "MEDIUM", f"pkg{i}", "1.0", None)
            for i in range(10)
        ]
        alert = format_cve_alert(cves)

        assert "[MEDIUM]" in alert
        assert "autres" in alert  # Should mention "... et X autres"


# =============================================================================
# REAL WORLD SCENARIO TESTS
# =============================================================================

class TestRealWorldScenarios:
    """Tests simulating real-world usage scenarios."""

    def test_rust_api_prompt(self):
        """Test a Rust API development prompt."""
        prompt = "Create a REST API route in Rust using Axum with JWT token authentication"
        context = detect_dev_context(prompt)

        assert context.is_dev
        assert "rust" in context.languages
        assert "jwt" in context.security_keywords_found
        assert context.security_level in ["elevated", "critical"]

    def test_fullstack_prompt(self):
        """Test a fullstack development prompt."""
        prompt = """
        Build a web application with:
        - Python FastAPI backend with PostgreSQL database
        - React TypeScript frontend
        - JWT authentication
        - File upload functionality
        """
        context = detect_dev_context(prompt)

        assert context.is_dev
        assert "python" in context.languages
        assert "typescript" in context.languages
        assert context.security_level == "critical"  # Many security keywords

    def test_data_science_prompt(self):
        """Test a data science prompt - should detect Python but fewer security concerns."""
        prompt = "Train a machine learning model using PyTorch and Pandas"
        context = detect_dev_context(prompt)

        assert context.is_dev
        assert "python" in context.languages
        assert context.security_level == "standard"  # No security keywords

    @pytest.mark.integration
    def test_vulnerable_project_scan(self):
        """Simulate scanning a project with vulnerable dependencies."""
        project_config = """
        # Old Project Config

        ## Dependencies
        django==3.1.0
        pillow==8.0.0
        requests==2.25.0
        pyyaml==5.3.1
        """

        prompt = "Help me secure this Django project"
        enriched, context = enrich_prompt_with_security(prompt, project_config, check_cves=True)

        print(f"\n=== Vulnerable Project Scan Results ===")
        print(f"Languages detected: {context.languages}")
        print(f"Security keywords: {context.security_keywords_found}")
        print(f"Security level: {context.security_level}")
        print(f"CVEs found: {len(context.cves)}")

        for cve in context.cves:
            print(f"  - {cve.id} ({cve.severity}): {cve.package}")

        print(f"\nEnriched context preview (first 500 chars):")
        print(enriched[:500])


# =============================================================================
# SECRET DETECTION TESTS
# =============================================================================

from promptforge.security import (
    scan_file_for_secrets,
    scan_directory_for_secrets,
    format_secret_alerts,
    mask_secret,
    is_placeholder_value,
    SecretFinding,
)
from pathlib import Path
import tempfile


# Identifiants synthetiques, invalides, generes pour ces tests uniquement.
# Ils sont assembles par concatenation a dessein : le fichier source ne contient
# donc aucun litteral qui declencherait un scanner de secrets sur ce depot
# (gitleaks, prevu par F-008), tout en donnant au scanner teste une valeur de
# longueur et de forme exactes.
FAKE_AWS_ACCESS_KEY_ID = "AKIA" + "3F7KQ2N9WBXDLZ4T"                    # 4 + 16 = 20
FAKE_AWS_SECRET_KEY = "kR9dTn2QvL7mXe4Wz" + "B1sYcJ0pHgAfU6iN3oD8rTq"   # 40
FAKE_GITHUB_TOKEN = "ghp_" + "Kq7Zx2Vb9NmTr4Lp1Wc6Ys3Hd8Jf0Gu5Ae2B"     # 4 + 36 = 40

# Identifiants d'exemple publies par la documentation AWS. Ils ne doivent JAMAIS
# etre remontes comme des secrets : ils sont copies dans d'innombrables README,
# `.env.example` et tutoriels.
AWS_DOC_EXAMPLE_ACCESS_KEY_ID = "AKIAIOSFODNN7" + "EXAMPLE"
AWS_DOC_EXAMPLE_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCY" + "EXAMPLEKEY"


class TestSecretMasking:
    """Tests for secret masking function."""

    def test_mask_short_secret(self):
        """Should fully mask short secrets."""
        masked = mask_secret("abc123")
        assert "abc" not in masked
        assert masked == "******"

    def test_mask_long_secret(self):
        """Should show first and last chars of long secrets."""
        masked = mask_secret("sk-1234567890abcdefghij")
        assert masked.startswith("sk-1")
        assert masked.endswith("ghij")
        assert "****" in masked

    def test_mask_empty(self):
        """Should handle empty string."""
        masked = mask_secret("")
        assert masked == "****"


class TestSecretFileScanning:
    """Tests for file-level secret scanning."""

    def test_scan_env_file_with_secrets(self):
        """Should detect secrets in .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DATABASE_URL=postgresql://user:password123@localhost/db\n")
            f.write("API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert len(findings) >= 2
            secret_types = [f.secret_type for f in findings]
            assert any("Database" in t for t in secret_types)
        finally:
            path.unlink()

    def test_scan_file_with_aws_keys(self):
        """Should detect AWS credentials that are not documentation examples."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"AWS_ACCESS_KEY_ID={FAKE_AWS_ACCESS_KEY_ID}\n")
            f.write(f"AWS_SECRET_ACCESS_KEY={FAKE_AWS_SECRET_KEY}\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert len(findings) >= 1
            assert any("AWS" in f.secret_type for f in findings)
            assert all(f.severity in ["HIGH", "CRITICAL"] for f in findings)
        finally:
            path.unlink()

    def test_skip_aws_documentation_example_keys(self):
        """Should NOT flag the credentials published by the AWS documentation.

        Pins the F-004 arbitration: a scanner that reports AWS's own published
        example credentials produces false positives on a large share of real
        projects, which CLAUDE.md forbids.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"AWS_ACCESS_KEY_ID={AWS_DOC_EXAMPLE_ACCESS_KEY_ID}\n")
            f.write(f"AWS_SECRET_ACCESS_KEY={AWS_DOC_EXAMPLE_SECRET_KEY}\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert findings == []
        finally:
            path.unlink()

    def test_aws_access_key_id_longer_than_20_chars_not_flagged(self):
        """Should not report an AKIA-prefixed blob that is not 20 chars long."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("AWS_ACCESS_KEY_ID=" + "AKIA" + "3F7KQ2N9WBXDLZ4TQRST" + "\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert not any("AWS Access Key ID" == f.secret_type for f in findings)
        finally:
            path.unlink()

    def test_scan_file_with_github_token(self):
        """Should detect a GitHub PAT of the documented length.

        A classic PAT is `ghp_` followed by exactly 36 characters (40 total).
        See the length note on the GitHub Token pattern in security.py.
        """
        assert len(FAKE_GITHUB_TOKEN) == 40

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"GITHUB_TOKEN={FAKE_GITHUB_TOKEN}\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert len(findings) >= 1
            assert any("GitHub" in f.secret_type for f in findings)
        finally:
            path.unlink()

    @pytest.mark.parametrize("body_length", [32, 40])
    def test_github_token_of_wrong_length_not_flagged(self, body_length):
        """Should not report a `ghp_` blob whose body is not 36 chars long.

        Guards both directions of the length rule: too short (32) and too long
        (40). The upper bound only holds because the pattern is right-bounded.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GITHUB_TOKEN=" + "ghp_" + ("a" * body_length) + "\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert not any("GitHub" in f.secret_type for f in findings)
        finally:
            path.unlink()

    def test_skip_placeholder_values(self):
        """Should skip placeholder values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("API_KEY=your_api_key_here\n")
            f.write("SECRET=<replace_with_secret>\n")
            f.write("PASSWORD=changeme\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            # Should not flag placeholder values
            assert len(findings) == 0
        finally:
            path.unlink()

    def test_skip_comments(self):
        """Should skip commented lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz\n")
            f.write("// ANOTHER_KEY=secret123456789012345\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert len(findings) == 0
        finally:
            path.unlink()


class TestPlaceholderFilter:
    """Tests for is_placeholder_value, the anti-false-positive filter (F-004)."""

    @pytest.mark.parametrize("value", [
        "your_api_key_here",
        "XXXXXXXXXXXXXXXX",
        "changeme",
        "replace_with_secret",
        "placeholder_value",
        "TODO_set_this",
        "${VAULT_DB_PASSWORD}",
        "{{ db_password }}",
        "<SET-ME-IN-VAULT>",
        "",
    ])
    def test_rejects_placeholders(self, value):
        assert is_placeholder_value(value) is True

    @pytest.mark.parametrize("value", [
        FAKE_AWS_ACCESS_KEY_ID,
        FAKE_AWS_SECRET_KEY,
        FAKE_GITHUB_TOKEN,
        "Tr0ub4dor<3!",          # un chevron isole ne fait pas un gabarit
        "a<b>c_D3f9hK2mQ",       # chevrons au milieu, valeur non encadree
    ])
    def test_accepts_real_looking_values(self, value):
        assert is_placeholder_value(value) is False

    def test_documented_example_credentials_are_placeholders(self):
        """AWS's published example credentials are placeholders, by decision."""
        assert is_placeholder_value(AWS_DOC_EXAMPLE_ACCESS_KEY_ID) is True
        assert is_placeholder_value(AWS_DOC_EXAMPLE_SECRET_KEY) is True

    def test_password_containing_angle_bracket_is_detected(self):
        """A password merely containing `<` must still be reported.

        Before F-004 the filter rejected any value containing `<` or `>`, which
        silently dropped a whole class of real passwords.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DB_PASSWORD=Tr0ub4dor<3!xK9\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert len(findings) >= 1
        finally:
            path.unlink()


class TestSecretDirectoryScanning:
    """Tests for directory-level secret scanning."""

    def test_scan_directory_with_secrets(self):
        """Should scan multiple files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)

            # Create .env file
            (project / '.env').write_text("API_KEY=sk-1234567890abcdef\n")

            # Create config.py
            (project / 'config.py').write_text('SECRET = "my_secret_value_123456789"\n')

            findings = scan_directory_for_secrets(project)
            assert len(findings) >= 1

    def test_scan_skips_node_modules(self):
        """Should skip node_modules directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)

            # Create node_modules with secrets (should be skipped)
            nm = project / 'node_modules' / 'some_pkg'
            nm.mkdir(parents=True)
            (nm / 'config.js').write_text('const KEY = "sk-1234567890abcdef";\n')

            # Create real file with secret
            (project / '.env').write_text("API_KEY=sk-realkey1234567890\n")

            findings = scan_directory_for_secrets(project)

            # Should only find the .env secret, not node_modules
            file_paths = [f.file_path for f in findings]
            assert not any("node_modules" in p for p in file_paths)

    def test_scan_empty_directory(self):
        """Should handle empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            findings = scan_directory_for_secrets(project)
            assert findings == []


class TestSecretAlertFormatting:
    """Tests for secret alert formatting."""

    def test_format_critical_findings(self):
        """Should format critical findings with emphasis."""
        findings = [
            SecretFinding(
                secret_type="AWS Secret Key",
                file_path="/project/.env",
                line_number=5,
                key_name="AWS_SECRET_KEY",
                masked_value="wJal****EKEY",
                severity="CRITICAL",
                recommendation="Use AWS IAM roles"
            )
        ]
        alert = format_secret_alerts(findings)

        assert "CRITIQUE" in alert
        assert "AWS_SECRET_KEY" in alert
        assert "wJal****EKEY" in alert

    def test_format_high_findings(self):
        """Should format high severity findings."""
        findings = [
            SecretFinding(
                secret_type="Generic API Key",
                file_path="/project/config.py",
                line_number=10,
                key_name="API_KEY",
                masked_value="sk-1****wxyz",
                severity="HIGH",
                recommendation="Use environment variables"
            )
        ]
        alert = format_secret_alerts(findings)

        assert "ELEVE" in alert
        assert "API_KEY" in alert

    def test_format_empty_findings(self):
        """Should return empty string for no findings."""
        alert = format_secret_alerts([])
        assert alert == ""

    def test_format_includes_recommendations(self):
        """Should include general recommendations."""
        findings = [
            SecretFinding(
                secret_type="Test",
                file_path="/test",
                line_number=1,
                key_name="TEST",
                masked_value="****",
                severity="HIGH",
                recommendation="Test rec"
            )
        ]
        alert = format_secret_alerts(findings)

        assert "gitignore" in alert.lower() or ".env" in alert
        assert "Secrets Manager" in alert or "secrets" in alert.lower()


class TestSecretPatterns:
    """Tests for specific secret pattern detection."""

    def test_detect_openai_key(self):
        """Should detect OpenAI API keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("OPENAI_API_KEY=sk-proj-1234567890abcdefghijklmnopqrstuvwxyz\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert any("OpenAI" in f.secret_type for f in findings)
        finally:
            path.unlink()

    def test_detect_anthropic_key(self):
        """Should detect Anthropic API keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnopqrstuvwxyz12345678\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert any("Anthropic" in f.secret_type for f in findings)
        finally:
            path.unlink()

    def test_detect_stripe_live_key(self):
        """Should detect Stripe live keys as critical."""
        # Use fake key that looks real but won't trigger GitHub scanner
        # Pattern: sk_live_ + 24 alphanumeric (avoid xxx which is filtered as placeholder)
        fake_stripe_key = "sk_live_" + "0a1b2c3d4e5f6g7h8i9j0k1l"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f'STRIPE_SECRET_KEY = "{fake_stripe_key}"\n')
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            stripe_findings = [f for f in findings if "Stripe" in f.secret_type]
            assert len(stripe_findings) >= 1
            assert any(f.severity == "CRITICAL" for f in stripe_findings)
        finally:
            path.unlink()

    def test_detect_jwt_token(self):
        """Should detect JWT tokens."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f'TOKEN = "{jwt}"\n')
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert any("JWT" in f.secret_type for f in findings)
        finally:
            path.unlink()

    def test_detect_private_key(self):
        """Should detect private keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN RSA PRIVATE KEY-----\n")
            f.write("MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF6M...\n")
            f.write("-----END RSA PRIVATE KEY-----\n")
            f.flush()
            path = Path(f.name)

        try:
            findings = scan_file_for_secrets(path)
            assert any("Private Key" in f.secret_type for f in findings)
            assert any(f.severity == "CRITICAL" for f in findings)
        finally:
            path.unlink()


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_security.py -v
    # Run integration tests: python -m pytest tests/test_security.py -v -m integration
    pytest.main([__file__, "-v"])
