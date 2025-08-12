# 3. Tech Stack

## Cloud Infrastructure

*   **Provider**: Self-Hosted. This application is designed to be run on a user's local machine.
*   **Key Services**: N/A
*   **Deployment Regions**: N/A

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Language** | Python | **~3.12** | Primary development language | Project requirement. The latest stable version provides optimal performance and features. |
| **Package/Venv Mgmt**| `uv` | latest | Dependency & environment mgmt | High-performance, modern standard for Python project management. |
| **Framework** | `fastmcp` | latest | Core MCP server framework | Official SDK implementation. Abstracts protocol complexity, supports required transports. |
| **HTTP Client** | `httpx` | latest | Async requests to LunaTask API| Required by `fastmcp`. Modern, fully async-capable HTTP client. |
| **Configuration** | `pydantic` | latest | Data validation & settings mgmt | Provides robust, typed configuration from files/env vars. Integrates seamlessly with `fastmcp`. |
| **Testing** | `pytest` | latest | Test framework and runner | De-facto standard for Python testing; powerful and extensible. |
| **Testing (Async)** | `pytest-asyncio`| latest | `pytest` plugin for `asyncio` | Essential for writing tests for our `asyncio`-based application code. |
| **Linting/Formatting**| `ruff` | latest | Code linting and formatting | All-in-one, high-performance tool. Enforces code quality and consistent style. |
| **Type Checking** | `pyright` | latest | Static type checker | Strict, fast, and accurate type checking to ensure code correctness and robustness. |
| **Dev Workflow** | `pre-commit` | latest | Git hook management | Automates code quality checks (linting, formatting, type checking) before each commit. |

---