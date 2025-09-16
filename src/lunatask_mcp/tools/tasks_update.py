"""Task update tool handler for LunaTask MCP integration."""

import logging
from datetime import date
from typing import Any

from fastmcp import Context

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import TaskUpdate
from lunatask_mcp.tools.tasks_common import serialize_task_response

logger = logging.getLogger(__name__)


# TODO: Refactor update_task_tool response with `TypedDict` to avoid too many arguments
# and reduce it's complexity
async def update_task_tool(  # noqa: PLR0913, PLR0911, PLR0915, PLR0912, C901
    lunatask_client: LunaTaskClient,
    ctx: Context,
    id: str,  # noqa: A002
    name: str | None = None,
    note: str | None = None,
    area_id: str | None = None,
    status: str | None = None,
    priority: int | str | None = None,
    scheduled_on: str | None = None,
    motivation: str | None = None,
    eisenhower: int | str | None = None,
) -> dict[str, Any]:
    """Update an existing task in LunaTask.

    This MCP tool updates an existing task using the LunaTask API. The task ID
    is required, and any combination of other fields can be updated.

    Args:
        ctx: MCP context for logging and communication
        id: Task ID to update (required)
        name: Updated task name (optional)
        note: Updated task note (optional)
        area_id: Updated area ID the task belongs to (optional)
        status: Updated task status (optional)
        priority: Updated task priority level (optional)
        scheduled_on: Updated scheduled date in YYYY-MM-DD format (optional)
        motivation: Updated task motivation (must, should, want, unknown) (optional)
        eisenhower: Updated eisenhower matrix quadrant (0-4) (optional)

    Returns:
        dict[str, Any]: Response containing task update result with updated task data

    Raises:
        LunaTaskValidationError: When task validation fails (422)
        LunaTaskNotFoundError: When task is not found (404)
        LunaTaskAuthenticationError: When authentication fails (401)
        LunaTaskRateLimitError: When rate limit exceeded (429)
        LunaTaskServerError: When server error occurs (5xx)
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
        logger.warning("Empty task_id provided for update")
        return result

    # Validate that at least one field is provided for update
    update_fields = [name, note, area_id, status, priority, scheduled_on, motivation, eisenhower]
    if all(field is None for field in update_fields):
        error_msg = "At least one field must be provided for update"
        result = {
            "success": False,
            "error": "validation_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("No fields provided for task update: %s", id)
        return result

    # Parse and validate scheduled_on if provided
    parsed_scheduled_on = None
    if scheduled_on is not None:
        try:
            parsed_scheduled_on = date.fromisoformat(scheduled_on)
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid scheduled_on format. Expected YYYY-MM-DD format: {e}"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Invalid scheduled_on format for task %s: %s", id, scheduled_on)
            return result

    # Coerce string priority values to integers when possible for client UX
    coerced_priority: int | None = None
    if priority is not None:
        if isinstance(priority, int):
            coerced_priority = priority
        else:
            try:
                coerced_priority = int(priority)
            except (TypeError, ValueError):
                error_msg = "Invalid priority: must be an integer between -2 and 2"
                result = {
                    "success": False,
                    "error": "validation_error",
                    "message": f"Validation failed for priority: {error_msg}",
                }
                await ctx.error(error_msg)
                logger.warning("Invalid priority type for task %s: %r", id, priority)
                return result

    # Coerce string eisenhower values to integers when possible for client UX
    coerced_eisenhower: int | None = None
    if eisenhower is not None:
        if isinstance(eisenhower, int):
            coerced_eisenhower = eisenhower
        else:
            try:
                coerced_eisenhower = int(eisenhower)
            except (TypeError, ValueError):
                error_msg = "Invalid eisenhower: must be an integer between 0 and 4"
                result = {
                    "success": False,
                    "error": "validation_error",
                    "message": f"Validation failed for eisenhower: {error_msg}",
                }
                await ctx.error(error_msg)
                logger.warning("Invalid eisenhower type for task %s: %r", id, eisenhower)
                return result

    await ctx.info(f"Updating task {id}")

    try:
        # Create TaskUpdate object from provided parameters
        # Cast string parameters to proper Literal types for optional fields
        task_status = None
        if status is not None:
            task_status = (
                status if status in ("later", "next", "started", "waiting", "completed") else None
            )

        task_motivation = None
        if motivation is not None:
            task_motivation = (
                motivation if motivation in ("must", "should", "want", "unknown") else None
            )

        # Build kwargs to avoid passing None (preserve model defaults and PATCH semantics)
        update_kwargs: dict[str, Any] = {"id": id}
        if area_id is not None:
            update_kwargs["area_id"] = area_id
        if name is not None:
            update_kwargs["name"] = name
        if note is not None:
            update_kwargs["note"] = note
        if task_status is not None:
            update_kwargs["status"] = task_status
        if coerced_priority is not None:
            update_kwargs["priority"] = coerced_priority
        if parsed_scheduled_on is not None:
            update_kwargs["scheduled_on"] = parsed_scheduled_on
        if task_motivation is not None:
            update_kwargs["motivation"] = task_motivation
        if coerced_eisenhower is not None:
            update_kwargs["eisenhower"] = coerced_eisenhower

        task_update = TaskUpdate(**update_kwargs)

        # Use LunaTask client to update the task
        async with lunatask_client as client:
            updated_task = await client.update_task(id, task_update)

        # Return success response with updated task data
        result = {
            "success": True,
            "task_id": id,
            "message": "Task updated successfully",
            "task": serialize_task_response(updated_task),
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
        logger.warning("Task not found during update: %s", id)
        return result

    except LunaTaskValidationError as e:
        # Handle validation errors (422)
        error_msg = f"Task validation failed: {e}"
        result = {
            "success": False,
            "error": "validation_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Task validation error during update: %s", e)
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
        logger.warning("Authentication error during task update: %s", e)
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
        logger.warning("Rate limit exceeded during task update: %s", e)
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
        logger.warning("Server error during task update: %s", e)
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
        logger.warning("API error during task update: %s", e)
        return result

    except Exception as e:
        # Handle Pydantic validation errors specifically
        if "ValidationError" in str(type(e)) and hasattr(e, "errors"):
            # Handle Pydantic validation errors with structured MCP response
            error_details: list[str] = []
            for error in e.errors():  # type: ignore[attr-defined]
                field = error.get("loc", ["unknown"])[0] if error.get("loc") else "unknown"  # type: ignore[misc]
                msg = error.get("msg", "Invalid value")  # type: ignore[misc]
                if field == "motivation":
                    msg = "Must be one of: must, should, want, unknown"
                elif field == "eisenhower":
                    msg = "Must be between 0 and 4"
                elif field == "priority":
                    msg = "Must be between -2 and 2"
                elif field == "status":
                    msg = "Must be one of: later, next, started, waiting, completed"
                error_details.append(f"{field}: {msg}")

            error_msg = f"Validation failed for {', '.join(error_details)}"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Task validation error during update: %s", error_msg)
            return result
        # Handle unexpected errors
        error_msg = f"Unexpected error updating task: {e}"
        result = {
            "success": False,
            "error": "unexpected_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.exception("Unexpected error during task update")
        return result
    else:
        await ctx.info(f"Successfully updated task {id}")
        return result
