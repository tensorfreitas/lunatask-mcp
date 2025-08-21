# LunaTask MCP

Model Context Protocol integration for LunaTask.

## Quickstart

Set up the development environment:

```bash
# Install dependencies and create virtual environment
uv sync

# Verify the package imports correctly
uv run python -c "import lunatask_mcp"
```

## Running the Server

### CLI Command
The server can be started using the console script entry point:

```bash
# Run the MCP server using the CLI command
uv run lunatask-mcp
```

### Direct Python Module
Alternatively, run the server directly as a Python module:

```bash
# Run as a Python module
uv run python -m lunatask_mcp.main
```

The server will start and listen for MCP protocol messages on stdio. All logging output goes to stderr to maintain stdout purity for the MCP protocol channel.

### Server Capabilities
The server provides:
- **Ping Tool**: A health-check tool that responds with "pong" when called
- **LunaTask Resources**: Access to tasks and individual task details via MCP resources
- **MCP Protocol Version**: Supports MCP protocol version `2025-06-18`
- **Stdio Transport**: Communicates over standard input/output streams

## LunaTask Integration

### Resources Available

The server exposes LunaTask data through MCP resources:

#### All Tasks Resource
- **URI**: `lunatask://tasks`
- **Description**: Retrieves a list of all tasks from your LunaTask account
- **Response**: JSON array containing task objects with metadata

#### Single Task Resource  
- **URI**: `lunatask://tasks/{task_id}`
- **Description**: Retrieves details of a specific task by its ID
- **Parameters**: `task_id` - The unique identifier of the task
- **Response**: JSON object containing the task details and metadata

### Usage Examples

#### Accessing All Tasks
```python
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

async def get_all_tasks():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        # List all available resources
        resources = await client.list_resources()
        print(f"Available resources: {[r.uri for r in resources]}")
        
        # Access all tasks
        tasks_resource = await client.read_resource("lunatask://tasks")
        print(f"Retrieved {len(tasks_resource.contents[0].json['tasks'])} tasks")
        
        # Display task information
        for task in tasks_resource.contents[0].json['tasks']:
            print(f"Task {task['id']}: {task['status']} (Priority: {task['priority']})")
```

#### Accessing a Specific Task
```python
async def get_specific_task():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        # Access a specific task by ID
        task_id = "your-task-id-here"
        task_resource = await client.read_resource(f"lunatask://tasks/{task_id}")
        
        # Extract task details
        task_data = task_resource.contents[0].json
        task = task_data['task']
        
        print(f"Task Details:")
        print(f"  ID: {task['id']}")
        print(f"  Status: {task['status']}")
        print(f"  Priority: {task['priority']}")
        print(f"  Created: {task['created_at']}")
        print(f"  Due Date: {task.get('due_date', 'Not set')}")
        print(f"  Area: {task.get('area_id', 'No area assigned')}")
        print(f"  Tags: {', '.join(task.get('tags', []))}")
```

### Resource Response Format

#### All Tasks Resource Response
```json
{
  "resource_type": "lunatask_tasks",
  "total_count": 3,
  "tasks": [
    {
      "id": "task-123",
      "status": "open",
      "priority": 1,
      "due_date": "2025-08-25T18:00:00+00:00",
      "created_at": "2025-08-20T10:00:00+00:00",
      "updated_at": "2025-08-20T10:30:00+00:00",
      "area_id": "area-456",
      "source": {
        "type": "manual",
        "value": "user_created"
      },
      "tags": ["work", "urgent"]
    }
  ],
  "metadata": {
    "retrieved_at": "session-id-123",
    "encrypted_fields_note": "Fields like 'name' and 'notes' are not included due to LunaTask's E2E encryption"
  }
}
```

#### Single Task Resource Response
```json
{
  "resource_type": "lunatask_task",
  "task_id": "task-123",
  "task": {
    "id": "task-123",
    "status": "open",
    "priority": 1,
    "due_date": "2025-08-25T18:00:00+00:00",
    "created_at": "2025-08-20T10:00:00+00:00",
    "updated_at": "2025-08-20T10:30:00+00:00",
    "area_id": "area-456",
    "source": {
      "type": "manual",
      "value": "user_created"
    },
    "tags": ["work", "urgent"]
  },
  "metadata": {
    "retrieved_at": "session-id-456",
    "encrypted_fields_note": "Fields like 'name' and 'notes' are not included due to LunaTask's E2E encryption"
  }
}
```

### Error Handling

The server provides structured error responses for various scenarios:

#### Task Not Found (404)
```python
try:
    task_resource = await client.read_resource("lunatask://tasks/nonexistent-task")
except Exception as e:
    print(f"Error: {e}")
    # Error message will indicate the task was not found
```

#### Authentication Error (401)
```python
# Occurs when bearer token is invalid or expired
# Check your config.toml file and ensure the token is correct
```

#### Rate Limit Error (429)
```python
# Occurs when API rate limits are exceeded
# The server implements rate limiting to prevent this
# Wait and retry if this occurs
```

### Important Notes

#### End-to-End Encryption
LunaTask uses end-to-end encryption for sensitive task data. As a result:
- Task `name` and `notes` fields are **not included** in API responses
- Only non-sensitive metadata and structural information is available
- This is a security feature of LunaTask and cannot be bypassed

#### Task IDs
- Task IDs are unique identifiers assigned by LunaTask
- Use the All Tasks resource to discover available task IDs
- Task IDs remain consistent across API calls

## Configuration

The LunaTask MCP server supports flexible configuration through TOML files and command-line arguments. A bearer token is required to authenticate with the LunaTask API.

### Quick Start

1. Copy the example configuration file:
```bash
cp config.example.toml config.toml
```

2. Edit `config.toml` and add your LunaTask API bearer token:
```toml
lunatask_bearer_token = "your_lunatask_bearer_token_here"
```

3. Run the server:
```bash
uv run lunatask-mcp
```

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

# Override specific settings
uv run lunatask-mcp --log-level DEBUG --port 9000

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

### Error Handling

Configuration errors result in:
- Clear error messages to stderr
- Non-zero exit codes (exit code 1 for all configuration failures)
- No server startup on configuration validation failures

### Example Configurations

**Minimal setup:**
```toml
lunatask_bearer_token = "your_token_here"
```

**Development setup with debug logging:**
```toml
lunatask_bearer_token = "your_token_here"
log_level = "DEBUG"
```

**Custom API endpoint (if needed):**
```toml
lunatask_bearer_token = "your_token_here"
lunatask_base_url = "https://custom.lunatask.endpoint.com/v1/"
log_level = "WARNING"
```

## Client Testing

### Running Client Integration Tests
To test the server with a real MCP client:

```bash
# Run the integration tests using pytest
uv run pytest tests/test_stdio_client_integration.py -v

# Or run the integration test as a standalone script
uv run python tests/test_stdio_client_integration.py
```

### Manual Client Testing
You can also test the server manually using the FastMCP client:

```python
import asyncio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

async def test_server():
    # Create stdio transport to launch the server
    # Note: Ensure you have a config.toml file with your bearer token
    transport = StdioTransport(command="uv", args=["run", "python", "-m", "lunatask_mcp.main"])
    client = Client(transport)
    
    async with client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        # Call the ping tool
        result = await client.call_tool("ping", {})
        print(f"Ping result: {result}")

# Run the test
asyncio.run(test_server())
```

## Example Usage

### Client Connection Example
Here's how to connect to the LunaTask MCP server from another application:

```python
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

# Connect to the server (ensure config.toml exists with bearer token)
transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
client = Client(transport)

async with client:
    # Verify server capabilities
    tools = await client.list_tools()
    assert "ping" in [tool.name for tool in tools]
    
    # Test server health
    ping_response = await client.call_tool("ping", {})
    print("Server is healthy:", ping_response)
```

### Protocol Verification
The server implements MCP protocol version `2025-06-18`:

```python
async with client:
    # Check protocol version during initialization
    init_result = client.initialize_result
    protocol_version = init_result.protocolVersion
    print(f"Server protocol version: {protocol_version}")
    assert protocol_version == "2025-06-18"
```
