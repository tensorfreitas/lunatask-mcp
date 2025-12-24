# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LunaTask MCP is a Model Context Protocol server that provides a standardized bridge between AI models and the LunaTask API. It's designed as a lightweight, asynchronous Python application using the FastMCP framework, running as a local subprocess to enable AI tools to interact with LunaTask data.

## Development Commands

### Environment Setup
```bash
# Install dependencies and create virtual environment
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

### Code Quality and Testing

Always follow the guidelines in [coding_guidelines](docs/architecture/11-coding-standards.md)

```bash
# Format and lint code
uv run ruff format
uv run ruff check --fix

# Type checking
uv run pyright

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_specific_file.py

# Run tests with coverage report
uv run pytest --cov=src/lunatask_mcp --cov-report=term-missing

# Run pre-commit hooks manually
uv run pre-commit run --all-files
```

### Running the Application
```bash
# Run the MCP server (looks for ./config.toml by default)
uv run python -m lunatask_mcp
# or using the installed script
uv run lunatask-mcp

# Run with custom config file
uv run lunatask-mcp --config-file /path/to/config.toml

# Run with debug logging
uv run lunatask-mcp --log-level DEBUG

# Get help on available options
uv run lunatask-mcp --help
```

### Configuration
The server requires a TOML configuration file with at minimum:
```toml
lunatask_bearer_token = "your_lunatask_bearer_token_here"
```
See `config.example.toml` for a complete configuration template.

## Architecture

The project follows a **single, event-driven monolith** architecture:

- **Core Framework**: FastMCP for MCP protocol handling
- **Transport**: stdio for client communication
- **External API**: HTTPS requests to LunaTask API
- **Concurrency**: asyncio for non-blocking I/O
- **Configuration**: Pydantic for settings and validation

Key architectural patterns:
- Decorator-based configuration (`@mcp.tool`, `@mcp.resource`)
- Dependency injection for configuration and HTTP clients
- Repository pattern for LunaTask API interactions
- Asynchronous I/O throughout the stack

## Project Structure

```
src/lunatask_mcp/           # Main package
├── __init__.py             # Entry point and version info
├── main.py                 # CoreServer and application entry point
├── config.py               # Configuration loading (Pydantic models)
├── rate_limiter.py         # Rate limiting implementation
├── api/                    # LunaTask API client components
│   ├── client.py           # LunaTaskClient class
│   ├── exceptions.py       # Custom exception definitions
│   └── models.py           # Pydantic data models
└── tools/                  # MCP tools implementation
    ├── tasks.py            # Main TaskTools delegator/registration
    ├── tasks_common.py     # Shared task helpers and serialization
    ├── tasks_resources.py  # Task list/single MCP resources
    ├── tasks_create.py     # create_task MCP tool
    ├── tasks_update.py     # update_task MCP tool
    ├── tasks_delete.py     # delete_task MCP tool
    └── habits.py           # Habit tracking tools
tests/                      # Test files (flat structure, split by concern)
docs/                       # Architecture and PRD documentation
├── architecture/           # Technical architecture docs (including 11-coding-standards.md)
├── prd/                    # Product requirements
└── stories/                # Development stories
```

## Coding Standards

**CRITICAL**: Follow the coding standards in `docs/architecture/11-coding-standards.md`. Key requirements:

### Development Methodology
- **Test-Driven Development (TDD)** is required: write tests first, watch them fail, implement minimal code, refactor, repeat

### Critical Rules for AI Agents
- **Log to `stderr` only**: All logging must use `sys.stderr`, never `print()`
- **Use custom exceptions**: Raise specific exceptions from `api/exceptions.py`
- **Secure token handling**: Never include LunaTask bearer tokens in logs/exceptions
- **Use `async/await`**: All I/O operations must be asynchronous
- **Type everything**: All function signatures require explicit type hints

### Code Standards
- **Python 3.12** compatibility required
- **Google-style docstrings** for all modules, classes, and functions
- **100 character line limit** (enforced by ruff)
- **500 lines max per file** - refactor if approaching this limit
- **Pre-commit hooks** run ruff and pyright automatically

## Test Organization Guidelines
- Split large test modules by concern before approaching 500 lines. Keep tests flat under `tests/`. Each test file should remain under 500 lines.
- Prefer explicit construction; use [tests/factories.py](tests/factories.py) only to reduce duplication.
- Keep fixtures minimal and function-scoped in [tests/conftest.py](tests/conftest.py); avoid `autouse` unless essential.
- Use pytest markers to separate unit vs integration/E2E (e.g., `@pytest.mark.integration`); register markers in [pytest.ini](pytest.ini) to avoid unknown-marker warnings.
- Assertions for logging must attach to `stderr` only.
- Coverage baseline is maintained at 95% minimum via `--cov-fail-under=95` in pytest configuration.

## Test Module Splitting Guidance
When test modules grow large, **split by concern before 500 lines**:

### Splitting Strategy
- **By functional concern**: initialization, resource listing, single resource access, create operations, update operations, delete operations, end-to-end workflows
- **By test type**: unit tests, integration tests, end-to-end tests
- **By feature area**: separate major features into focused test files

### Construction Patterns
- **Prefer explicit construction**: Create test objects directly in tests rather than abstracting into factories
- **Use factories only to reduce duplication**: Move to [tests/factories.py](tests/factories.py) only when same construction pattern is used 3+ times
- **Keep factories simple**: Basic builders, not complex object graphs

### Fixture Guidelines  
- **Keep fixtures minimal and function-scoped** in [tests/conftest.py](tests/conftest.py)
- **Avoid `autouse` fixtures** unless absolutely essential for test isolation
- **Prefer dependency injection** over global fixtures where possible

### Naming Conventions
- Use descriptive names that clearly indicate the test focus (e.g., `test_task_tools_init_and_registration.py`)
- Group related test classes within files by shared setup or concern
- Use consistent prefixes for related test modules (`test_task_tools_*`)

## Development Guidelines

- **Python Version**: 3.12 (strict requirement)
- **Code Style**: Enforced by ruff (line length: 100)
- **Type Checking**: Strict mode with pyright
- **Testing**: pytest with asyncio support
- **Git Hooks**: Pre-commit runs ruff and pyright automatically

## Key Dependencies

- `fastmcp`: Core MCP server framework
- `httpx`: Async HTTP client for LunaTask API
- `pydantic`: Configuration and data validation
- `pytest` + `pytest-asyncio`: Testing framework