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
- **LunaTask Tools**: Create and update tasks in LunaTask via MCP tools
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

### Tools Available

The server provides MCP tools for creating and updating tasks in LunaTask:

#### Create Task Tool
- **Tool Name**: `create_task`
- **Description**: Creates a new task in LunaTask with the specified parameters
- **Returns**: Task creation result with the newly assigned task ID

##### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | ✅ Yes | - | Task name (will be encrypted client-side by LunaTask) |
| `notes` | string | ❌ No | `null` | Task notes (will be encrypted client-side by LunaTask) |
| `area_id` | string | ❌ No | `null` | Area ID the task belongs to |
| `status` | string | ❌ No | `"open"` | Task status (e.g., "open", "completed") |
| `priority` | integer | ❌ No | `null` | Task priority level |
| `tags` | list[string] | ❌ No | `[]` | List of task tags |

##### Tool Usage Examples

###### Create Minimal Task
```python
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

async def create_simple_task():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        # Create a task with just the required name parameter
        result = await client.call_tool("create_task", {
            "name": "Review quarterly reports"
        })
        
        if result.success:
            print(f"Task created successfully with ID: {result.task_id}")
        else:
            print(f"Error creating task: {result.message}")
```

###### Create Complete Task
```python
async def create_detailed_task():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        # Create a task with all available parameters
        result = await client.call_tool("create_task", {
            "name": "Implement OAuth2 authentication",
            "notes": "Add support for Google and GitHub OAuth2 providers with PKCE security",
            "area_id": "development-area-123",
            "status": "open",
            "priority": 3,
            "tags": ["security", "authentication", "urgent"]
        })
        
        if result.success:
            print(f"Detailed task created with ID: {result.task_id}")
        else:
            print(f"Task creation failed: {result.error} - {result.message}")
```

##### Response Format

###### Successful Creation Response
```json
{
  "success": true,
  "task_id": "new-task-abc123",
  "message": "Task created successfully"
}
```

###### Error Response Examples

**Validation Error (422)**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Task validation failed: Task name is required"
}
```

**Subscription Required (402)**
```json
{
  "success": false,
  "error": "subscription_required", 
  "message": "Subscription required: Free plan task limit reached"
}
```

**Authentication Error (401)**
```json
{
  "success": false,
  "error": "authentication_error",
  "message": "Authentication failed: Invalid or expired LunaTask API credentials"
}
```

**Rate Limit Error (429)**
```json
{
  "success": false,
  "error": "rate_limit_error",
  "message": "Rate limit exceeded: Please try again later"
}
```

**Server Error (5xx)**
```json
{
  "success": false,
  "error": "server_error",
  "message": "Server error: LunaTask API is temporarily unavailable"
}
```

##### Tool Error Handling

```python
async def create_task_with_error_handling():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        try:
            result = await client.call_tool("create_task", {
                "name": "Test task",
                "priority": 1
            })
            
            if result.success:
                print(f"✅ Task created: {result.task_id}")
            else:
                # Handle specific error types
                if result.error == "validation_error":
                    print("❌ Validation failed - check your parameters")
                elif result.error == "subscription_required":
                    print("💳 Upgrade your LunaTask plan to create more tasks")
                elif result.error == "authentication_error":
                    print("🔑 Check your bearer token in config.toml")
                elif result.error == "rate_limit_error":
                    print("⏰ Rate limit exceeded - wait and retry")
                else:
                    print(f"❌ Unknown error: {result.message}")
                    
        except Exception as e:
            print(f"🚨 Unexpected error: {e}")
```

##### Important Notes

###### End-to-End Encryption Support
- The `name` and `notes` fields **can be included** in create requests
- LunaTask automatically encrypts these fields client-side before storage
- Once created, these fields will not be visible in GET responses due to E2E encryption
- This is normal LunaTask behavior and ensures data privacy

###### Task Creation Limits
- Free LunaTask plans have limits on the number of tasks that can be created
- When limits are reached, the tool returns a `subscription_required` error
- Consider upgrading your LunaTask plan if you need to create more tasks

###### Rate Limiting
- The server implements rate limiting to prevent API abuse
- If you encounter rate limit errors, wait before retrying
- Rate limits are per-server instance and reset over time

#### Update Task Tool
- **Tool Name**: `update_task`
- **Description**: Updates an existing task in LunaTask with the specified parameters
- **Returns**: Task update result with the updated task data

##### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | ✅ Yes | - | Task ID to update (unique identifier) |
| `name` | string | ❌ No | `null` | Updated task name (will be encrypted client-side by LunaTask) |
| `notes` | string | ❌ No | `null` | Updated task notes (will be encrypted client-side by LunaTask) |
| `area_id` | string | ❌ No | `null` | Updated area ID the task belongs to |
| `status` | string | ❌ No | `null` | Updated task status (e.g., "open", "completed") |
| `priority` | integer | ❌ No | `null` | Updated task priority level |
| `due_date` | string | ❌ No | `null` | Updated due date as ISO 8601 string (e.g., "2025-12-31T23:59:59Z") |
| `tags` | list[string] | ❌ No | `null` | Updated list of task tags |

##### Tool Usage Examples

###### Update Single Field
```python
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

async def update_task_status():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        # Update only the status of a specific task
        result = await client.call_tool("update_task", {
            "id": "task-abc123",
            "status": "completed"
        })
        
        if result.success:
            print(f"Task {result.task_id} status updated successfully")
        else:
            print(f"Error updating task: {result.message}")
```

###### Update Multiple Fields
```python
async def update_task_details():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        # Update multiple fields of a task (partial update)
        result = await client.call_tool("update_task", {
            "id": "task-xyz789",
            "name": "Updated task name",
            "priority": 2,
            "due_date": "2025-12-31T23:59:59Z",
            "tags": ["updated", "high-priority"]
        })
        
        if result.success:
            print(f"Task {result.task_id} updated successfully")
            # The response includes updated task data
            if 'task' in result:
                task = result.task
                print(f"Updated priority: {task.get('priority')}")
                print(f"Updated due date: {task.get('due_date')}")
                print(f"Updated tags: {task.get('tags')}")
        else:
            print(f"Task update failed: {result.error} - {result.message}")
```

###### Update with ISO 8601 Date Handling
```python
from datetime import datetime, timezone

async def update_task_due_date():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        # Update due date with proper timezone handling
        due_date = datetime(2025, 12, 25, 18, 0, 0, tzinfo=timezone.utc)
        
        result = await client.call_tool("update_task", {
            "id": "task-holiday-prep",
            "due_date": due_date.isoformat(),  # "2025-12-25T18:00:00+00:00"
            "tags": ["holiday", "deadline"]
        })
        
        if result.success:
            print(f"Task due date updated to {due_date}")
        else:
            print(f"Date update failed: {result.message}")
```

##### Response Format

###### Successful Update Response
```json
{
  "success": true,
  "task_id": "task-abc123",
  "message": "Task updated successfully",
  "task": {
    "id": "task-abc123",
    "status": "completed",
    "priority": 2,
    "due_date": "2025-12-31T23:59:59+00:00",
    "created_at": "2025-08-20T10:00:00+00:00",
    "updated_at": "2025-08-23T15:30:00+00:00",
    "area_id": "area-456",
    "source": {
      "type": "api",
      "value": "mcp_update"
    },
    "tags": ["updated", "high-priority"]
  }
}
```

###### Error Response Examples

**Task Not Found (404)**
```json
{
  "success": false,
  "error": "not_found_error",
  "message": "Task not found: Task with ID 'nonexistent-task' was not found"
}
```

**Validation Error (Empty Task ID)**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Task ID cannot be empty"
}
```

**Validation Error (Invalid Due Date)**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Invalid due_date format. Expected ISO 8601 string: time data 'invalid-date' does not match format"
}
```

**Authentication Error (401)**
```json
{
  "success": false,
  "error": "authentication_error",
  "message": "Authentication failed: Invalid or expired LunaTask API credentials"
}
```

**Rate Limit Error (429)**
```json
{
  "success": false,
  "error": "rate_limit_error",
  "message": "Rate limit exceeded: Please try again later"
}
```

##### Tool Error Handling

```python
async def update_task_with_error_handling():
    transport = StdioTransport(command="uv", args=["run", "lunatask-mcp"])
    client = Client(transport)
    
    async with client:
        try:
            result = await client.call_tool("update_task", {
                "id": "task-to-update",
                "status": "completed",
                "priority": 1
            })
            
            if result.success:
                print(f"✅ Task updated: {result.task_id}")
            else:
                # Handle specific error types
                if result.error == "not_found_error":
                    print("❌ Task not found - check the task ID")
                elif result.error == "validation_error":
                    print("❌ Validation failed - check your parameters")
                elif result.error == "authentication_error":
                    print("🔑 Check your bearer token in config.toml")
                elif result.error == "rate_limit_error":
                    print("⏰ Rate limit exceeded - wait and retry")
                else:
                    print(f"❌ Unknown error: {result.message}")
                    
        except Exception as e:
            print(f"🚨 Unexpected error: {e}")
```

##### Important Notes

###### Partial Updates
- **Only provided fields are updated** - omitted fields remain unchanged
- You can update just one field (e.g., only status) without affecting other fields
- Pass `null` or omit parameters to leave fields unchanged
- This allows for precise, targeted task modifications

###### End-to-End Encryption Support
- The `name` and `notes` fields **can be included** in update requests
- LunaTask automatically encrypts these fields client-side before storage
- Updated encrypted fields will not be visible in the response due to E2E encryption
- Non-encrypted fields (status, priority, etc.) will be visible in the response

###### Date Format Requirements
- `due_date` must be provided as an ISO 8601 string
- Supported formats: `"2025-12-31T23:59:59Z"` (UTC), `"2025-12-31T18:00:00-05:00"` (with timezone)
- Invalid date formats will result in validation errors
- Use Python's `datetime.isoformat()` for proper formatting

###### Task ID Requirements
- Task ID is required and cannot be empty
- Must be a valid, existing task ID from your LunaTask account
- Use the resources (`lunatask://tasks`) to discover available task IDs
- Non-existent task IDs will result in "not_found_error"

###### Rate Limiting
- The server implements rate limiting for update operations
- If you encounter rate limit errors, wait before retrying
- Rate limits help prevent API abuse and ensure service stability

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
        # Expected tools: ['ping', 'create_task', 'update_task']
        
        # Call the ping tool
        result = await client.call_tool("ping", {})
        print(f"Ping result: {result}")
        
        # Call the create_task tool
        task_result = await client.call_tool("create_task", {
            "name": "Test task from manual testing"
        })
        print(f"Task creation result: {task_result}")

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
    tool_names = [tool.name for tool in tools]
    assert "ping" in tool_names
    assert "create_task" in tool_names
    assert "update_task" in tool_names
    
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
