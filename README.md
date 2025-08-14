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
- **MCP Protocol Version**: Supports MCP protocol version `2025-06-18`
- **Stdio Transport**: Communicates over standard input/output streams

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
