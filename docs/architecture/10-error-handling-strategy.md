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
# Base exception class
class LunaTaskAPIError(Exception):
    """Base exception for all LunaTask API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)

# Specific HTTP status code exceptions
class LunaTaskBadRequestError(LunaTaskAPIError):          # 400
class LunaTaskAuthenticationError(LunaTaskAPIError):      # 401
class LunaTaskSubscriptionRequiredError(LunaTaskAPIError): # 402
class LunaTaskNotFoundError(LunaTaskAPIError):            # 404
class LunaTaskValidationError(LunaTaskAPIError):          # 422
class LunaTaskRateLimitError(LunaTaskAPIError):           # 429
class LunaTaskServerError(LunaTaskAPIError):              # 5xx
class LunaTaskServiceUnavailableError(LunaTaskAPIError):  # 503

# Network-level exceptions
class LunaTaskNetworkError(LunaTaskAPIError):             # Network failures
class LunaTaskTimeoutError(LunaTaskAPIError):             # Request timeouts
```

### HTTP Status Code Mapping

The `LunaTaskClient` maps HTTP status codes to specific exceptions:

```python
# Example from client error handling
if status_code == 400:
    raise LunaTaskBadRequestError from error
elif status_code == 401:
    raise LunaTaskAuthenticationError from error
elif status_code == 402:
    raise LunaTaskSubscriptionRequiredError from error
elif status_code == 404:
    raise LunaTaskNotFoundError from error
elif status_code == 422:
    raise LunaTaskValidationError from error
elif status_code == 429:
    raise LunaTaskRateLimitError from error
elif status_code == 503:
    raise LunaTaskServiceUnavailableError from error
elif 500 <= status_code < 600:
    raise LunaTaskServerError("", status_code) from error
```

### MCP Tool Error Translation

MCP tools catch these exceptions and translate them into structured responses:

```python
try:
    # API operation
    result = await client.create_task(task_data)
except LunaTaskValidationError as e:
    return {
        "success": False,
        "error": "validation_error",
        "message": f"Task validation failed: {e}"
    }
except LunaTaskAuthenticationError as e:
    return {
        "success": False,
        "error": "authentication_error",
        "message": f"Authentication failed: {e}"
    }
```