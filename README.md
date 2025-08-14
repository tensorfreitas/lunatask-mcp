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

# Connect to the server
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
