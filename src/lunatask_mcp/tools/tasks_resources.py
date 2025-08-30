"""Task resource handlers for LunaTask MCP integration.

These functions implement the MCP resource endpoints for listing tasks and
retrieving single tasks, designed to be bound as methods of TaskTools.
"""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import Context

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.tools.tasks_common import serialize_task_response

logger = logging.getLogger(__name__)


async def get_tasks_resource(lunatask_client: LunaTaskClient, ctx: Context) -> dict[str, Any]:
    """MCP resource providing access to all LunaTask tasks.

    This resource retrieves all tasks from the LunaTask API and presents them
    as a structured JSON resource accessible via the URI 'lunatask://tasks'.

    Args:
        ctx: MCP context providing logging and execution context

    Returns:
        dict[str, Any]: JSON structure containing task data with metadata

    Raises:
        LunaTaskAPIError: If the LunaTask API request fails
    """
    try:
        await ctx.info("Retrieving tasks from LunaTask API")

        # Use the LunaTaskClient to fetch all tasks
        async with lunatask_client:
            tasks = await lunatask_client.get_tasks()

        # Convert TaskResponse objects to dictionaries for JSON serialization
        task_data = [serialize_task_response(task) for task in tasks]

        resource_data = {
            "resource_type": "lunatask_tasks",
            "total_count": len(tasks),
            "tasks": task_data,
            "metadata": {
                "retrieved_at": ctx.session_id if hasattr(ctx, "session_id") else "unknown",
                "encrypted_fields_note": (
                    "Task names and note are not included due to E2E encryption"
                ),
            },
        }

    except LunaTaskAPIError as e:
        # Handle specific API errors based on exception type
        if e.__class__.__name__ == "LunaTaskAuthenticationError":
            error_msg = "Failed to retrieve tasks: Invalid or expired LunaTask API credentials"
            await ctx.error(error_msg)
            logger.exception("Authentication error accessing LunaTask API")
        elif e.__class__.__name__ == "LunaTaskRateLimitError":
            error_msg = (
                "Failed to retrieve tasks: LunaTask API rate limit exceeded - "
                "please try again later"
            )
            await ctx.error(error_msg)
            logger.warning("Rate limit exceeded for LunaTask API")
        elif e.__class__.__name__ == "LunaTaskServerError":
            error_msg = (
                f"Failed to retrieve tasks: LunaTask server error ({e.status_code}) "
                "- please try again"
            )
            await ctx.error(error_msg)
            logger.exception("LunaTask server error: %s", e.status_code)
        elif e.__class__.__name__ == "LunaTaskTimeoutError":
            error_msg = (
                "Failed to retrieve tasks: Request to LunaTask API timed out - please try again"
            )
            await ctx.error(error_msg)
            logger.warning("LunaTask API request timeout")
        else:
            # Generic LunaTask API error
            error_msg = f"Failed to retrieve tasks from LunaTask API: {e}"
            await ctx.error(error_msg)
            logger.exception("LunaTask API error")
        raise
    except Exception as e:
        error_msg = f"Unexpected error retrieving tasks: {e}"
        logger.exception(error_msg)
        await ctx.error(error_msg)
        raise LunaTaskAPIError(error_msg) from e
    else:
        await ctx.info(f"Successfully retrieved {len(tasks)} tasks from LunaTask")
        return resource_data


async def get_task_resource(
    lunatask_client: LunaTaskClient, ctx: Context, task_id: str
) -> dict[str, Any]:
    """MCP resource providing access to a single LunaTask task by ID.

    This resource retrieves a specific task from the LunaTask API and presents it
    as a structured JSON resource accessible via the URI 'lunatask://tasks/{task_id}'.

    Args:
        ctx: MCP context providing logging and execution context
        task_id: The unique identifier for the task to retrieve

    Returns:
        dict[str, Any]: JSON structure containing single task data with metadata

    Raises:
        LunaTaskBadRequestError: If the task_id parameter is empty or invalid
        LunaTaskNotFoundError: If the task with the specified ID is not found
        LunaTaskAPIError: If the LunaTask API request fails
    """
    # Defensive parameter validation for better UX
    if not task_id or not task_id.strip():
        await ctx.error("Empty or invalid task_id parameter provided")
        raise LunaTaskBadRequestError.empty_task_id()

    try:
        await ctx.info(f"Retrieving task {task_id} from LunaTask API")

        # Use the LunaTaskClient to fetch the specific task
        async with lunatask_client:
            task = await lunatask_client.get_task(task_id)

        # Convert TaskResponse object to dictionary for JSON serialization
        task_data = serialize_task_response(task)

        resource_data = {
            "resource_type": "lunatask_task",
            "task_id": task_id,
            "task": task_data,
            "metadata": {
                "retrieved_at": ctx.session_id if hasattr(ctx, "session_id") else "unknown",
                "encrypted_fields_note": (
                    "Task names and note are not included due to E2E encryption"
                ),
            },
        }

    except LunaTaskNotFoundError:
        # Handle specific task not found error with structured MCP response
        error_msg = f"Task {task_id} not found in LunaTask"
        await ctx.error(error_msg)
        logger.warning("Task not found: %s", task_id)
        raise
    except LunaTaskAuthenticationError:
        # Handle authentication errors
        error_msg = (
            f"Failed to retrieve task {task_id}: Invalid or expired LunaTask API credentials"
        )
        await ctx.error(error_msg)
        logger.exception("Authentication error accessing LunaTask API for task %s", task_id)
        raise
    except LunaTaskRateLimitError:
        # Handle rate limit errors
        error_msg = (
            f"Failed to retrieve task {task_id}: LunaTask API rate limit exceeded - "
            "please try again later"
        )
        await ctx.error(error_msg)
        logger.warning("Rate limit exceeded for LunaTask API task %s", task_id)
        raise
    except LunaTaskServerError as e:
        # Handle server errors
        error_msg = (
            f"Failed to retrieve task {task_id}: LunaTask server error ({e.status_code}) "
            "- please try again"
        )
        await ctx.error(error_msg)
        logger.exception("LunaTask server error for task %s: %s", task_id, e.status_code)
        raise
    except LunaTaskTimeoutError:
        # Handle timeout errors
        error_msg = (
            f"Failed to retrieve task {task_id}: Request to LunaTask API timed out - "
            "please try again"
        )
        await ctx.error(error_msg)
        logger.warning("LunaTask API request timeout for task %s", task_id)
        raise
    except LunaTaskAPIError as e:
        # Handle other LunaTask API errors
        error_msg = f"Failed to retrieve task {task_id} from LunaTask API: {e}"
        await ctx.error(error_msg)
        logger.exception("LunaTask API error for task %s", task_id)
        raise
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error retrieving task {task_id}: {e}"
        logger.exception(error_msg)
        await ctx.error(error_msg)
        raise LunaTaskAPIError(error_msg) from e
    else:
        await ctx.info(f"Successfully retrieved task {task_id} from LunaTask")
        return resource_data
