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
```bash
# Format and lint code
uv run ruff format
uv run ruff check --fix

# Type checking
uv run pyright

# Run tests
uv run pytest

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Running the Application
```bash
# Run the MCP server
python -m lunatask_mcp
# or
lunatask-mcp
```

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
├── __init__.py             # Entry point and main server logic
tests/                      # Test files
docs/                       # Architecture and PRD documentation
├── architecture/           # Technical architecture docs
└── prd/                    # Product requirements
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