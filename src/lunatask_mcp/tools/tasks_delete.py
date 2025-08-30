"""Task deletion tool handler for LunaTask MCP integration."""

import logging
from typing import Any

from fastmcp import Context

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)

logger = logging.getLogger(__name__)


async def delete_task_tool(  # noqa: PLR0911
    lunatask_client: LunaTaskClient,
    ctx: Context,
    id: str,  # noqa: A002
) -> dict[str, Any]:
    """Delete an existing task in LunaTask.

    This MCP tool deletes an existing task using the LunaTask API. The task ID
    is required and will be permanently deleted.

    Args:
        ctx: MCP context for logging and communication
        id: Task ID to delete (required)

    Returns:
        dict[str, Any]: Response containing task deletion result with confirmation

    Raises:
        LunaTaskNotFoundError: When task is not found (404)
        LunaTaskAuthenticationError: When authentication fails (401)
        LunaTaskRateLimitError: When rate limit exceeded (429)
        LunaTaskServerError: When server error occurs (5xx)
        LunaTaskTimeoutError: When request times out
        LunaTaskAPIError: For other API errors
    """
    # Validate required task ID parameter
    if not id or not id.strip():
        error_msg = "Task ID cannot be empty"
        result = {
            "success": False,
            "error": "validation_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Empty task_id provided for deletion")
        return result

    await ctx.info(f"Deleting task {id}")

    try:
        # Use LunaTask client to delete the task. Any successful call (no exception)
        # indicates the task was deleted.
        async with lunatask_client as client:
            await client.delete_task(id)

        # Return success response with task ID for confirmation
        result = {
            "success": True,
            "task_id": id,
            "message": "Task deleted successfully",
        }

    except LunaTaskNotFoundError as e:
        # Handle task not found errors (404)
        error_msg = f"Task not found: {e}"
        result = {
            "success": False,
            "error": "not_found_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Task not found during deletion: %s", id)
        return result

    except LunaTaskAuthenticationError as e:
        # Handle authentication errors (401)
        error_msg = f"Authentication failed: {e}"
        result = {
            "success": False,
            "error": "authentication_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Authentication error during task deletion: %s", e)
        return result

    except LunaTaskRateLimitError as e:
        # Handle rate limit errors (429)
        error_msg = f"Rate limit exceeded: {e}"
        result = {
            "success": False,
            "error": "rate_limit_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Rate limit exceeded during task deletion: %s", e)
        return result

    except LunaTaskTimeoutError as e:
        # Handle timeout errors
        error_msg = f"Request timeout: {e}"
        result = {
            "success": False,
            "error": "timeout_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Timeout error during task deletion: %s", e)
        return result

    except LunaTaskServerError as e:
        # Handle server errors (5xx)
        error_msg = f"Server error: {e}"
        result = {
            "success": False,
            "error": "server_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Server error during task deletion: %s", e)
        return result

    except LunaTaskAPIError as e:
        # Handle other API errors
        error_msg = f"API error: {e}"
        result = {
            "success": False,
            "error": "api_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("API error during task deletion: %s", e)
        return result

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error deleting task: {e}"
        result = {
            "success": False,
            "error": "unexpected_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.exception("Unexpected error during task deletion")
        return result
    else:
        await ctx.info(f"Successfully deleted task {id}")
        return result
