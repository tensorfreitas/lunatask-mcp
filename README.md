# LunaTask MCP Server

LunaTask MCP is an unnoficial Model Context Protocol server that provides a standardized bridge between AI models and the LunaTask API. It's designed as a lightweight, asynchronous Python application using the FastMCP framework, running as a local subprocess to enable AI tools to interact with LunaTask data.

## Important Notes

### End-to-End Encryption
LunaTask uses end-to-end encryption for sensitive task data. As a result:
- Task `name` and `note` fields are **not included** in API responses
- Only non-sensitive metadata and structural information is available
- This is a security feature of LunaTask and cannot be bypassed
- The `name` and `note` fields **can be included** in create requests
- LunaTask automatically encrypts these fields client-side before storage
- Once created, these fields will not be visible in GET responses due to E2E encryption
- This is normal LunaTask behavior and ensures data privacy

#### Task IDs
- Task IDs are unique identifiers assigned by LunaTask
- Use the All Tasks resource to discover available task IDs
- Task IDs remain consistent across API calls

#### Task Creation Limits
- Free LunaTask plans have limits on the number of tasks that can be created
- When limits are reached, the tool returns a `subscription_required` error
- Consider upgrading your LunaTask plan if you need to create more tasks

##### Rate Limiting
- The server implements rate limiting to prevent API abuse
- If you encounter rate limit errors, wait before retrying
- Rate limits are per-server instance and reset over time

## Local Installation

Lunatask MCP Server is managed by uv, so you will need to [install it](https://docs.astral.sh/uv/getting-started/installation/).

### Using `uv`
```bash
# Install dependencies and create the local virtual environment
uv sync

# Optionally verify the package imports correctly
uv run python -c "import lunatask_mcp"
```

## Server Configuration

The LunaTask MCP server supports flexible configuration through TOML files and command-line arguments. A bearer token is required to authenticate with the LunaTask API.

### Quick Start

1. Copy the example configuration file to a path you prefer:
```bash
cp config.example.toml ~/path/to/your/lunatask_mcp_config.toml
```

2. Edit `config.toml` and add your LunaTask API bearer token:
```toml
lunatask_bearer_token = "your_lunatask_bearer_token_here"
```

3. Run the server:
```bash
uv run lunatask-mcp --config-file /path/to/your/config.toml
```

Note: To create an acess token open Lunatask app, open application settings, head to "Access tokens" section, and create a new access token. Then, click "Copy to clipboard", and paste it in the `lunatask_bearer_token` field in the config file.

### Configuration Methods

The server supports three configuration methods with the following precedence (highest to lowest):

1. **Command-line arguments** (highest priority)
2. **Configuration file** (TOML format)
3. **Default values** (lowest priority)

### Command-Line Usage

```bash
# Basic usage with default config file (./config.toml)
uv run lunatask-mcp

# Specify a custom config file
uv run lunatask-mcp --config-file /path/to/your/config.toml

# Override specific settings (examples)
uv run lunatask-mcp --log-level DEBUG --port 9000
uv run lunatask-mcp --base-url https://api.lunatask.app/v1/
uv run lunatask-mcp --token "$LUNATASK_TOKEN"
uv run lunatask-mcp --rate-limit-rpm 120 --rate-limit-burst 20

# Get help on available options
uv run lunatask-mcp --help
```

### Configuration File Format

Create a `config.toml` file with your settings:

```toml
# Required: Your LunaTask API bearer token
lunatask_bearer_token = "your_lunatask_bearer_token_here"

# Optional: API base URL (default: https://api.lunatask.app/v1/)
lunatask_base_url = "https://api.lunatask.app/v1/"

# Optional: Port for future HTTP transport (default: 8080, range: 1-65535)
# Note: Currently unused as server only supports stdio transport
port = 8080

# Optional: Logging level (default: INFO)
# Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = "INFO"

# Optional: Connectivity test during startup (default: false)
test_connectivity_on_startup = false

# Optional: Rate limiting (defaults: rpm=60, burst=10)
rate_limit_rpm = 60
rate_limit_burst = 10

# Optional: HTTP client tuning
http_retries = 2
http_backoff_start_seconds = 0.25
http_user_agent = "lunatask-mcp/0.1.0"
timeout_connect = 5.0
timeout_read = 30.0
```

### Configuration Discovery

- If `--config-file` is not specified, the server looks for `./config.toml`
- Missing configuration files are only an error if explicitly specified
- Default values are used when no configuration file exists

### Configuration Validation

The server validates all configuration on startup and fails fast with clear error messages:

- **Invalid TOML syntax**: Clear parsing error with file location
- **Unknown configuration keys**: Rejected with list of unknown keys
- **Invalid values**: Port must be 1-65535, URL must be HTTPS, log level must be valid
- **Missing bearer token**: Required field, server will not start without it

### Security Features

- **Bearer tokens are never logged**: Automatically redacted in all log output and error messages
- **Effective configuration logging**: Server logs the final configuration with secrets redacted
- **Unknown keys rejection**: Prevents typos and ensures clean configuration
- **Input validation**: All configuration values are validated before server startup

## Server Capabilities

The server provides the following tools:
- **Ping Tool**: A health-check tool that responds with "pong" when called
- **MCP Resources (read-only)**: Discovery + single task, plus area/global list aliases
- **MCP Tools (write)**: Create, update, delete tasks; track habit activity
- **MCP Protocol Version**: Supports MCP protocol version `2025-06-18`
- **Stdio Transport**: Communicates over standard input/output streams

## Tools Available
- `create_task`: Creates a new task. Requires `name` and the target `area_id`. Optional fields include text content (`note`), planning data (`status`, `scheduled_on`, `estimate`, `progress`), prioritisation (`priority`, `motivation`, `eisenhower`), goal context (`goal_id`) and external source metadata (`source`, `source_id`). Returns `{ "success": true, "task_id": "..." }` with the new identifier.
- `update_task`: Updates an existing task by ID. Supports partial updates—only the fields you pass (same set as create, minus the required `name`) are mutated. Returns `{ "success": true, "task": {...} }` with the full serialized task payload.
- `delete_task`: Permanently deletes a task from LunaTask. Returns `{ "success": true, "task_id": "..." }`. **Deleted tasks cannot be recovered**, so invoke with caution.
- `track_habit`: Logs habit activity for a specific habit ID and ISO date. Returns `{ "ok": true, "message": "Successfully tracked habit <id> on <date>" }` when the API confirms the event.

## Resources Available
The server also has the following resources:
- Discovery: `lunatask://tasks` and `lunatask://tasks/discovery`
- Single Task: `lunatask://tasks/{task_id}`
- Area lists (replace `{area_id}`):
  - `lunatask://area/{area_id}/now`
  - `lunatask://area/{area_id}/today`
  - `lunatask://area/{area_id}/overdue`
  - `lunatask://area/{area_id}/next-7-days`
  - `lunatask://area/{area_id}/high-priority`
  - `lunatask://area/{area_id}/recent-completions`
- Global lists:
  - `lunatask://global/now`
  - `lunatask://global/today`
  - `lunatask://global/overdue`
  - `lunatask://global/next-7-days`
  - `lunatask://global/high-priority`
  - `lunatask://global/recent-completions`

Discovery resource returns discovery metadata for list resources, including supported parameters, alias URIs, canonical examples, defaults, and guardrails.

You can filter globally and by `area_id`. The filters work as follows:
- **today**: scheduled today
- **overdue**: scheduled before today
- **next-7-days**: scheduled within the next 7 days (UTC), excluding today
- **recent-completions**: tasks completed in the last 72 hours.
- **now**: one of the following:
  - Tasks without scheduled date but with status as "started" (in progress in the app)
  - Tasks without scheduled date but with highest priority (2)
  - Tasks without scheduled date but with motivation as "must"
  - Tasks without scheduled date but with eisenhower as 1 (urgent and important)

The reason behind these filters is that if you try to gather all the tasks from the Lunastask API you will easily fill up your LLM context if you have a lot of tasks. 
In the future these could be expanded to include:
- filters by `goal_id`
- filters for all priority types
- filters for all motivation types
- filters for all eisenhower types
- filters for specific dates
- filters for completed tasks in a range of dates

## Integration with other tools

### Claude Code
You give access to Claude Code via:
```bash
claude mcp add lunatask-mcp -- uvx --from git+https://github.com/tensorfreitas/lunatask-mcp --config-file /your/path/to/lunatask_mcp_config.toml
```

### Claude Desktop or LM Studio
```json
{
    "mcpServers": {
        "lunatask-mcp": {
            "command": "uvx",
            "args": ["--from", "git+https://github.com/tensorfreitas/lunatask-mcp", "--config-file", "/your/path/to/lunatask_mcp_config.toml"]
        }
    }
}
```

### Codex
Unlike Claude Code, in Codex you add an MCP server globally and not per project. Add the following to ~/.codex/config.toml (create the file if it does not exist):

```toml
[mcp_servers.lunatask-mcp]
command = "uvx"
args = ["--from", "git+https://github.com/tensorfreitas/lunatask-mcp", "--config-file", "/your/path/to/lunatask_mcp_config.toml"]
```

## To Be Implemented
1. Implementation of MCp Server-Sent Events (SSE) for HTTP-based clients
2. Extra Task Resource Filters
- [ ] resource filters by `goal_id`
- [ ] filters for all priority types
- [ ] filters for all motivation types
- [ ] filters for all eisenhower types
- [ ] filters for specific dates
- [ ] filters for completed tasks in a range of dates
3. Extra tools
- [ ] Implement [`create_note` tool](https://lunatask.app/api/notes-api/create)
- [ ] Implement [`create_entry_journal` tool](https://lunatask.app/api/journal-api/create)
- [ ] Implement [`create_person` tool](https://lunatask.app/api/people-api/create)
- [ ] Implement [`delete_person` tool](https://lunatask.app/api/people-api/delete)
- [ ] Implement [`create_person_timeline_note` tool](https://lunatask.app/api/person-timeline-notes-api/create)
4. Extra Resources
- [ ] Implement [Retrieve person](https://lunatask.app/api/person-timeline-notes-api/create) resource
- [ ] Implement [Retrieve all people](https://lunatask.app/api/people-api/list) resource

## Disclaimer

This project was developed with the assistance of AI. The purpose was to test various workflows using different LLMs and identify the most effective approach for me. Since I’m doing this on my free time, this was the only feasible option. Consequently, some of the documentation or code may not be entirely accurate. I’ve made every effort to review everything, but there might have been some errors that I overlooked. If you discover any issues that require correction, please create an issue on GitHub.
