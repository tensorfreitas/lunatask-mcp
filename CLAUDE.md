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

# Archon MCP Integration & Workflow

You can use archon mcp to research for FastMCP and Lunatask API documentation.

### Universal Research & Planning Phase

**For all scenarios, research before task creation:**

```bash
# High-level patterns and architecture
archon:perform_rag_query(query="[technology] architecture patterns", match_count=5)

# Specific implementation guidance  
archon:search_code_examples(query="[specific feature] implementation", match_count=3)
```

**Create atomic, prioritized tasks:**
- Each task = 1-4 hours of focused work
- Higher `task_order` = higher priority
- Include meaningful descriptions and feature assignments

## Development Iteration Workflow
### Task-Specific Research
**For each task, conduct focused research:**
```bash
# High-level: Architecture, security, optimization patterns
archon:perform_rag_query(
  query="JWT authentication security best practices",
  match_count=5
)

# Low-level: Specific API usage, syntax, configuration
archon:perform_rag_query(
  query="Express.js middleware setup validation",
  match_count=3
)

# Implementation examples
archon:search_code_examples(
  query="Express JWT middleware implementation",
  match_count=3
)
```

**Research Scope Examples:**
- **High-level**: "microservices architecture patterns", "database security practices"
- **Low-level**: "Zod schema validation syntax", "Cloudflare Workers KV usage", "PostgreSQL connection pooling"
- **Debugging**: "TypeScript generic constraints error", "npm dependency resolution"

**Implement with Research-Driven Approach:**
- Use findings from `search_code_examples` to guide implementation
- Follow patterns discovered in `perform_rag_query` results`

## Knowledge Management Integration

### Documentation Queries

**Use RAG for both high-level and specific technical guidance:**

```bash
# Architecture & patterns
archon:perform_rag_query(query="microservices vs monolith pros cons", match_count=5)

# Security considerations  
archon:perform_rag_query(query="OAuth 2.0 PKCE flow implementation", match_count=3)

# Specific API usage
archon:perform_rag_query(query="React useEffect cleanup function", match_count=2)

# Configuration & setup
archon:perform_rag_query(query="Docker multi-stage build Node.js", match_count=3)

# Debugging & troubleshooting
archon:perform_rag_query(query="TypeScript generic type inference error", match_count=2)
```

### Code Example Integration

**Search for implementation patterns before coding:**

```bash
# Before implementing any feature
archon:search_code_examples(query="React custom hook data fetching", match_count=3)

# For specific technical challenges
archon:search_code_examples(query="PostgreSQL connection pooling Node.js", match_count=2)
```

**Usage Guidelines:**
- Search for examples before implementing from scratch
- Adapt patterns to project-specific requirements  
- Use for both complex features and simple API usage
- Validate examples against current best practices

## Research-Driven Development Standards

### Before Any Implementation

**Research checklist:**

- [ ] Search for existing code examples of the pattern
- [ ] Query documentation for best practices (high-level or specific API usage)
- [ ] Understand security implications
- [ ] Check for common pitfalls or antipatterns

### Knowledge Source Prioritization

**Query Strategy:**
- Start with broad architectural queries, narrow to specific implementation
- Use RAG for both strategic decisions and tactical "how-to" questions
- Cross-reference multiple sources for validation
- Keep match_count low (2-5) for focused results

## Error Handling & Recovery

### When Research Yields No Results

**If knowledge queries return empty results:**

1. Broaden search terms and try again
2. Search for related concepts or technologies
3. Document the knowledge gap for future learning
4. Proceed with conservative, well-tested approaches

### When Tasks Become Unclear

**If task scope becomes uncertain:**

1. Break down into smaller, clearer subtasks
2. Research the specific unclear aspects
3. Update task descriptions with new understanding
4. Create parent-child task relationships if needed

## Quality Assurance Integration

### Research Validation

**Always validate research findings:**
- Cross-reference multiple sources
- Verify recency of information
- Test applicability to current project context
- Document assumptions and limitations