# 10. Error Handling Strategy

## General Approach

The server will use a layered error handling approach based on a hierarchy of custom exceptions that map directly to the official LunaTask API error codes.

1.  **Custom Exception Hierarchy**: A set of specific, custom exceptions will be defined to represent each documented error from the LunaTask API.
2.  **Service Layer Exception Mapping**: The `LunaTaskClient` component will be responsible for inspecting the HTTP status code of every response from the LunaTask API and raising the appropriate custom exception.
3.  **Tool Layer Translation**: The MCP `tool` components (`TaskTools`, `HabitTools`) will contain `try...except` blocks that catch these specific exceptions. They will then translate them into structured, user-friendly MCP error responses.
4.  **Fail-Fast on Startup**: The server will validate its configuration on startup and fail immediately with a clear `stderr` message if critical settings are missing.

## Logging Standards

*   **Output Channel**: All logging **MUST** be directed to `sys.stderr` to prevent corrupting the `stdout` JSON-RPC channel.
*   **Format**: Logs will include a timestamp, log level, and message.
*   **Security**: The LunaTask bearer token will never be written to logs.
*   **Exception Logging**: Unhandled exceptions will be logged with a full traceback to `stderr`.

## Error Handling Patterns

### Custom Exception Definitions

A dedicated module will define our application's exception hierarchy.

```python