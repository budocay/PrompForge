# CLAUDE.md - PromptForge Project Context

## Project Overview

**PromptForge** is a 100% local intelligent prompt reformatter that transforms raw prompts into structured XML/Markdown prompts optimized for different LLMs (Claude, GPT, Gemini).

**Version**: 0.1.0 (Alpha)
**License**: MIT

## Tech Stack

- **Language**: Python 3.10+ (stdlib only for core - zero external dependencies)
- **Web UI**: Gradio 4.x-6.x (optional)
- **Database**: SQLite3 (stdlib)
- **LLM Provider**: Ollama (local HTTP API on port 11434)
- **Token Estimation**: tiktoken (optional, accurate) / heuristics (fallback)
- **Deployment**: Docker + Docker Compose

## Project Structure

```
promptforge/
├── promptforge/           # Main source code
│   ├── __init__.py       # Public exports
│   ├── core.py           # Business logic, project management, formatting orchestration
│   ├── providers.py      # Ollama HTTP client, XML/Markdown conversion
│   ├── database.py       # SQLite CRUD operations
│   ├── profiles.py       # 11 LLM reformat profiles with optimized system prompts
│   ├── cli.py            # argparse CLI interface
│   ├── tokens.py         # Token estimation (tiktoken + heuristic fallback)
│   ├── logging_config.py # Structured logging configuration
│   ├── utils.py          # Cross-platform utilities (clipboard, GPU detection)
│   ├── scanner.py        # Project auto-scanner and config generator
│   ├── web.py            # DEPRECATED - backward compatibility wrapper
│   └── web/              # Modular web interface package
│       ├── __init__.py   # Package exports
│       ├── assets.py     # SVG logos, CSS, constants
│       ├── ollama_helpers.py    # Ollama status and model management
│       ├── project_helpers.py   # Project CRUD for UI
│       ├── analysis.py          # Prompt quality analysis
│       ├── recommendations.py   # Model recommendations and benchmarks
│       ├── profiles_ui.py       # Profile selection helpers
│       ├── scanner_helpers.py   # Scanner UI helpers
│       └── interface.py         # Main Gradio interface
├── tests/                # pytest test suite
│   ├── conftest.py       # Shared fixtures
│   ├── test_core.py
│   ├── test_database.py
│   ├── test_cli.py
│   ├── test_providers.py
│   ├── test_integration.py
│   ├── test_scanner.py     # Scanner module tests
│   └── test_ollama_integration.py  # Real Ollama integration tests
├── scripts/              # Build system
│   ├── build.py          # Docker build orchestration with GPU auto-detection
│   └── docker_helper.py  # Cross-platform Docker helper
├── templates/            # Configuration templates
│   └── PROJECT_GENERATOR_PROMPT.md
├── projects/             # Example project configs
├── data/                 # Runtime data (created automatically)
│   ├── projects/         # User config files
│   ├── history/          # Formatted prompt history (Markdown files)
│   └── promptforge.db    # SQLite database
└── docker/               # Docker compose variants
```

## Key Files

| File | Purpose | LOC |
|------|---------|-----|
| `core.py` | Main orchestration, project CRUD, format_prompt() | ~230 |
| `providers.py` | OllamaProvider class, Markdown↔XML conversion | ~424 |
| `database.py` | SQLite operations, Project/PromptHistory dataclasses | ~198 |
| `profiles.py` | 11 LLM profiles with system prompts + benchmarks | ~900+ |
| `cli.py` | CLI commands (init, use, format, history, web, etc.) | ~380 |
| `tokens.py` | Token estimation with tiktoken/heuristics | ~180 |
| `logging_config.py` | Structured JSON logging | ~200 |
| `scanner.py` | Project auto-scanner, config generator | ~1250 |
| `web/interface.py` | Main Gradio interface | ~550 |
| `web/scanner_helpers.py` | Scanner UI helpers | ~240 |
| `web/analysis.py` | Prompt quality analysis | ~350 |
| `web/recommendations.py` | Model recommendations | ~300 |

## Database Schema

```sql
-- Projects table
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    config_path TEXT NOT NULL,
    config_content TEXT NOT NULL,
    created_at TEXT NOT NULL,  -- ISO 8601
    is_active INTEGER DEFAULT 0
);

-- Prompt history table
CREATE TABLE prompt_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    raw_prompt TEXT NOT NULL,
    formatted_prompt TEXT NOT NULL,
    created_at TEXT NOT NULL,  -- ISO 8601
    file_path TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Settings table (for future use)
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

## Architecture Patterns

1. **Singleton**: `get_forge()` in web/ollama_helpers.py returns single PromptForge instance
2. **Provider**: `OllamaProvider` abstracts LLM communication
3. **Dataclasses**: `Project`, `PromptHistory` as DTOs
4. **Factory**: `PRESET_PROFILES` dict with `get_profile()` accessor
5. **Strategy**: Different profiles = different reformatting strategies
6. **Adapter**: `convert_markdown_to_xml()` for format conversion
7. **Modular Package**: web/ package split by responsibility

## Execution Flow

```
User Input (CLI/Web)
       ↓
PromptForge.format_prompt() [core.py]
       ↓
OllamaProvider.format_prompt_with_ollama() [providers.py]
       ↓
Load profile system prompt [profiles.py]
       ↓
HTTP POST to Ollama API (:11434/api/generate)
       ↓
Post-process: detect format, convert Markdown→XML if needed
       ↓
Save to history (SQLite + Markdown file)
       ↓
Return formatted prompt
```

## Ollama API Usage

**Endpoint**: `POST http://localhost:11434/api/generate`

**Payload**:
```json
{
    "model": "qwen3:8b",
    "prompt": "<user_prompt>",
    "system": "<system_prompt>",
    "stream": false,
    "options": {
        "temperature": 0.3,
        "top_p": 0.9
    }
}
```

**Timeout**: 120 seconds

## Token Estimation

The `tokens.py` module provides accurate token counting:

```python
from promptforge import estimate_tokens, get_token_info

# Check available method
info = get_token_info()
# {'tiktoken_available': True, 'method': 'tiktoken (accurate)', 'encoding': 'cl100k_base'}

# Estimate tokens
tokens = estimate_tokens("Your text here")

# Detailed breakdown
from promptforge.tokens import count_tokens_detailed
details = count_tokens_detailed("Your text here")
# {'total': 4, 'method': 'tiktoken', 'characters': 14, 'words': 3, ...}
```

**Features**:
- Uses tiktoken (cl100k_base encoding) when available for accurate counting
- Falls back to intelligent heuristics if tiktoken not installed
- Handles code vs natural language differently
- Install tiktoken with: `pip install promptforge[tokens]`

## Logging System

Structured logging via `logging_config.py`:

```python
from promptforge import init_logging, get_logger
import logging

# Initialize with optional file output
init_logging(
    level=logging.INFO,
    log_file=Path("promptforge.log"),
    structured_file=True  # JSON format for files
)

# Get logger for module
logger = get_logger(__name__)
logger.info("Processing prompt", extra={"project": "my-project"})
```

**Features**:
- Colored console output for readability
- Structured JSON file logging for analysis
- Module-specific loggers
- Extra fields support for context

## LLM Profiles (profiles.py)

11 target model profiles with optimized system prompts:
- **Claude**: Opus 4.5, Sonnet 4.5, Haiku 4.5 (XML format)
- **GPT**: 5.1, 5.1 Mini, 5 Pro (Markdown format)
- **Gemini**: 3 Pro, 3 Flash (XML format)
- **Universal**: Generic XML format

## Environment Variables

```bash
OLLAMA_HOST=http://localhost:11434  # Ollama server URL
OLLAMA_MODEL=qwen3:8b               # Default model
PROMPTFORGE_DATA_PATH=./data        # Data directory path
```

## CLI Commands

```bash
promptforge init <name> --config <file.md>  # Create project
promptforge use <name>                       # Activate project
promptforge list                             # List projects
promptforge format [prompt]                  # Reformat prompt
promptforge history [--limit N]              # View history
promptforge status                           # System status
promptforge delete <name>                    # Delete project
promptforge reload <name>                    # Reload config
promptforge web [--port 7860]               # Launch web UI
promptforge template                         # Show config template
promptforge scan <path> --name <nom>        # Auto-scan project directory
```

### Scan Command Options

```bash
promptforge scan /path/to/project --name my-project [options]

Options:
  --name, -n       Project name (required)
  --description, -d  Optional project description
  --depth          Scan depth (default: 3)
  --output, -o     Output file path
  --dry-run        Preview without saving
  --no-register    Don't register as project
```

## Web UI Tabs (Gradio)

1. **Reformater** - Main prompt transformation interface
2. **Projets** - Project CRUD management
3. **Scanner** - Auto-scan directories to generate project configs
4. **Historique** - Browse past reformatted prompts
5. **Generer Config** - Template for AI-generated project configs
6. **Comparaison** - Model pricing comparison
7. **Aide** - Help and documentation

## Development Commands

```bash
# Install with all dependencies
pip install -e ".[all]"

# Or install specific extras
pip install -e ".[web]"      # Gradio UI
pip install -e ".[tokens]"   # tiktoken for accurate counting
pip install -e ".[dev]"      # pytest, black, ruff

# Run tests
make test                    # All tests (mocked)
make test-cov               # With coverage
pytest tests/test_ollama_integration.py -v  # Real Ollama tests

# Code quality
make check                  # Lint + format-check + tests
make format                 # Auto-format with black
make lint                   # Ruff linting

# Docker
make docker-start           # Start with auto GPU detection
make docker-stop            # Stop services
make docker-logs            # View Ollama logs
make rebuild                # Rebuild without cache
```

## Docker Compose Variants

| File | GPU | Default Model |
|------|-----|---------------|
| docker-compose.yml | NVIDIA | qwen3:8b |
| docker-compose.cpu.yml | None | phi4-mini |
| docker-compose.amd.yml | AMD ROCm (Linux) | qwen3:14b |
| docker-compose.win-amd.yml | AMD (Windows native) | qwen3:14b |
| docker-compose.win-nvidia.yml | NVIDIA (Windows native) | qwen3:8b |

## Recommended Ollama Models

| Model | Size | Best For |
|-------|------|----------|
| qwen3:8b | ~5GB | Default, good balance |
| qwen3:14b | ~9GB | Better quality, needs GPU |
| deepseek-r1:14b | ~9GB | Complex reasoning |
| phi4-mini | ~3GB | CPU-only systems |
| mistral-small:24b | ~14GB | Multilingual, agents |

## Code Style

- **Formatter**: black (line-length=100)
- **Linter**: ruff (E, F, W, I, N, UP rules)
- **Python**: 3.10, 3.11, 3.12 compatible
- **Docstrings**: Google style
- **Type hints**: Encouraged but not enforced

## Testing Strategy

- **Unit tests**: Mock Ollama responses (fast, CI-friendly)
- **Integration tests**: `test_ollama_integration.py` with real Ollama
- **Fixtures**: Temp directories, sample configs, mock providers
- **Coverage**: HTML reports via pytest-cov
- **Run real tests**: `pytest tests/test_ollama_integration.py -v`

## Important Implementation Details

1. **Zero external dependencies** in core - only stdlib (sqlite3, urllib, argparse)
2. **Gradio is optional** - install with `pip install -e ".[web]"`
3. **tiktoken is optional** - install with `pip install -e ".[tokens]"` for accurate token counting
4. **Markdown→XML conversion** handles small models that don't follow XML instructions
5. **Cross-platform clipboard**: Uses pbcopy (Mac), clip.exe (Windows), xclip/xsel/wl-copy (Linux)
6. **History saved twice**: SQLite DB + Markdown files in data/history/
7. **Single active project**: Only one project can be active at a time (is_active flag)
8. **Modular web package**: web/ directory split into focused modules for maintainability

## Common Workflows

### Adding a new LLM profile
1. Edit `profiles.py`
2. Add entry to `PRESET_PROFILES` dict
3. Create `ReformatProfile` with appropriate system prompt
4. Update `web/profiles_ui.py` with description
5. Update `web/recommendations.py` DOMAIN_EXPERTISE if needed

### Adding a new CLI command
1. Edit `cli.py`
2. Add argparse subparser
3. Implement handler function
4. Update help text

### Modifying database schema
1. Edit `database.py`
2. Update `_init_database()` for new tables
3. Add migration logic if needed
4. Update dataclasses if structure changes

### Adding web UI features
1. Identify which module in `web/` to modify
2. Add UI components in `web/interface.py`
3. Add business logic in appropriate helper module
4. Add event handlers

## Web Package Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `assets.py` | Static content: SVG, CSS, constants |
| `ollama_helpers.py` | Ollama connection, model management |
| `project_helpers.py` | Project CRUD operations |
| `analysis.py` | Prompt quality scoring, comparison |
| `recommendations.py` | Model recommendations, benchmarks |
| `profiles_ui.py` | Profile dropdown helpers |
| `scanner_helpers.py` | Scanner UI integration |
| `interface.py` | Main Gradio interface assembly |

## Project Scanner

The scanner module (`scanner.py`) automatically analyzes project directories and generates comprehensive configuration files.

### Features

- **Language Detection**: Python, TypeScript, JavaScript, Go, Rust, Java, C#, and 15+ more
- **Framework Detection**: FastAPI, Django, React, Vue, Next.js, Express, and 30+ frameworks
- **Database Detection**: PostgreSQL, MySQL, MongoDB, Redis, SQLite via docker-compose, .env, packages
- **Convention Detection**: black, ruff, prettier, eslint, biome formatters/linters
- **Test Detection**: pytest, Jest, Vitest, Cypress, Playwright
- **Infrastructure**: Docker, Docker Compose, GitHub Actions, GitLab CI, etc.

### Usage

```python
from promptforge import ProjectScanner, scan_directory

# Quick scan
result = scan_directory("/path/to/project")

# Custom scan
scanner = ProjectScanner(max_depth=5, max_files=20000)
result = scanner.scan("/path/to/project")

# Generate config
config = scanner.generate_config(result, "my-project", "Optional description")
```

### Dataclasses

| Class | Purpose |
|-------|---------|
| `DetectedLanguage` | Language name, extensions, file count, percentage, version |
| `DetectedFramework` | Framework name, category, version, config file |
| `DetectedDatabase` | Database name, detected source, ORM |
| `CodeConventions` | Formatter, linter, typechecker, line length |
| `TestSetup` | Test framework, category, directories |
| `DockerSetup` | Dockerfile presence, compose, services |
| `CICDSetup` | CI provider, config files, workflows |
| `ProjectStructure` | Directory tree, file counts |
| `ScanResult` | Aggregation of all detected information |
