# Epic 1: Foundation & Core Server

**Expanded Goal**: The primary objective of this epic is to create the fundamental scaffolding for the MCP server. This involves initializing the project structure using `uv`, implementing a basic FastMCP server that can communicate via the `stdio` transport, and establishing a secure mechanism for handling configuration and the LunaTask API bearer token. By the end of this epic, we will have a functional, though featureless, server that is ready for the core API integrations.

## **Story 1.1: Project Initialization**
**As a** developer, **I want** to have a standardized project structure with `uv` for dependency management and a Git repository, **so that** I can begin development with a clean, organized, and version-controlled foundation.
### Acceptance Criteria
1. A new Git repository is initialized for the project.
2. The project structure is created with a main application directory (e.g., `my_mcp_server/`).
3. `uv` is used to initialize the project, creating a `pyproject.toml` file.
4. A virtual environment is created and managed by `uv`.
5. `fastmcp` and `httpx` are added as initial dependencies using `uv`.
6. A `.gitignore` file is created with standard Python exclusions.
7. A basic `README.md` file is created with the project title.

## **Story 1.2: Basic Stdio Server**
**As a** developer, **I want** to implement a minimal, runnable FastMCP server that communicates over `stdio`, **so that** I can verify the core transport layer is working correctly with a client.
### Acceptance Criteria
1. A main application file (e.g., `main.py`) is created.
2. The file contains a basic FastMCP server instance.
3. The server, when run, listens for requests on `stdio` by default.
4. The server includes a simple "ping" or "health-check" tool that returns a static response (e.g., "pong").
5. A client script can successfully call the "ping" tool and receive the "pong" response via `stdio`.
6. The server directs all logging output to `stderr` to avoid interfering with the `stdio` JSON-RPC channel.

## **Story 1.3: Configuration Handling**
**As a** developer, **I want** the server to support configuration via both a file and command-line arguments, **so that** users can easily and flexibly manage settings like API tokens and ports.
### Acceptance Criteria
1. The server can parse command-line arguments (e.g., `--config-file`, `--port`).
2. The server can read settings from a specified configuration file (e.g., `config.toml`).
3. Command-line arguments take precedence over settings in the configuration file.
4. The server has a default configuration that is used if no file or arguments are provided.
5. The configuration supports, at a minimum, a placeholder for the LunaTask API token.

## **Story 1.4: Secure Authentication Handler**
**As a** developer, **I want** to securely load the LunaTask bearer token from the configuration and use it to make an authenticated test call to the LunaTask API, **so that** I can confirm the server can successfully communicate with the external API.
### Acceptance Criteria
1. The server loads the LunaTask bearer token from its configuration.
2. The loaded token is never exposed in any logs or standard output.
3. The server uses an HTTP client (like `httpx`) to make a simple, authenticated request to a read-only LunaTask API endpoint (e.g., a user info endpoint).
4. The server correctly handles a successful (e.g., 200 OK) response from the API.
5. The server correctly handles an unsuccessful (e.g., 401 Unauthorized) response and logs an appropriate error to `stderr` without exposing the token.

---