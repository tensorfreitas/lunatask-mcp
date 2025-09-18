"""Task creation tool handler for LunaTask MCP integration."""

import logging
from datetime import date
from typing import Any

from fastmcp import Context

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import TaskCreate

logger = logging.getLogger(__name__)


async def create_task_tool(  # noqa: PLR0913, PLR0911, PLR0915, PLR0912, C901
    lunatask_client: LunaTaskClient,
    ctx: Context,
    name: str,
    note: str | None = None,
    area_id: str | None = None,
    status: str = "later",
    priority: int | str = 0,
    motivation: str = "unknown",
    eisenhower: int | str | None = None,
    estimate: int | str | None = None,
    progress: int | str | None = None,
    goal_id: str | None = None,
    scheduled_on: str | None = None,
) -> dict[str, Any]:
    """Create a new task in LunaTask.

    This MCP tool creates a new task using the LunaTask API. All task fields
    are supported, with only the name being required.

    Args:
        ctx: MCP context for logging and communication
        name: Task name (required)
        note: Optional task note
        area_id: Optional area ID the task belongs to
        status: Task status (default: "later")
        priority: Optional task priority level (accepts int or numeric string)
        motivation: Optional task motivation (must, should, want, unknown)
        eisenhower: Optional eisenhower matrix quadrant (0-4; accepts int or numeric string)
        estimate: Optional estimated duration in minutes (accepts int or numeric string)
        progress: Optional task completion percentage (accepts int or numeric string)
        goal_id: Optional goal ID the task belongs to
        scheduled_on: Optional scheduled date in YYYY-MM-DD format

    Returns:
        dict[str, Any]: Response containing task creation result with task_id

    Raises:
        LunaTaskValidationError: When task validation fails (422)
        LunaTaskSubscriptionRequiredError: When subscription required (402)
        LunaTaskAuthenticationError: When authentication fails (401)
        LunaTaskRateLimitError: When rate limit exceeded (429)
        LunaTaskServerError: When server error occurs (5xx)
        LunaTaskAPIError: For other API errors
    """
    await ctx.info(f"Creating new task: {name}")

    # Coerce string priority values to integers when possible for client UX
    coerced_priority: int
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
            logger.warning("Invalid priority type for create_task: %r", priority)
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
                logger.warning("Invalid eisenhower type for create_task: %r", eisenhower)
                return result

    # Coerce string estimate values to integers when possible for client UX
    coerced_estimate: int | None = None
    if estimate is not None:
        if isinstance(estimate, int):
            coerced_estimate = estimate
        else:
            try:
                coerced_estimate = int(estimate)
            except (TypeError, ValueError):
                error_msg = "Invalid estimate: must be an integer (minutes)"
                result = {
                    "success": False,
                    "error": "validation_error",
                    "message": f"Validation failed for estimate: {error_msg}",
                }
                await ctx.error(error_msg)
                logger.warning("Invalid estimate type for create_task: %r", estimate)
                return result

    # Coerce string progress values to integers when possible for client UX
    coerced_progress: int | None = None
    if progress is not None:
        if isinstance(progress, int):
            coerced_progress = progress
        else:
            try:
                coerced_progress = int(progress)
            except (TypeError, ValueError):
                error_msg = "Invalid progress: must be an integer (percentage)"
                result = {
                    "success": False,
                    "error": "validation_error",
                    "message": f"Validation failed for progress: {error_msg}",
                }
                await ctx.error(error_msg)
                logger.warning("Invalid progress type for create_task: %r", progress)
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
            logger.warning("Invalid scheduled_on format for create_task: %s", scheduled_on)
            return result

    try:
        # Create TaskCreate object from parameters
        # Cast string parameters to proper Literal types
        task_status = (
            status if status in ("later", "next", "started", "waiting", "completed") else "later"
        )
        task_motivation = (
            motivation if motivation in ("must", "should", "want", "unknown") else "unknown"
        )

        task_data = TaskCreate(
            name=name,
            note=note,
            area_id=area_id,
            status=task_status,  # type: ignore[arg-type]
            priority=coerced_priority,
            motivation=task_motivation,  # type: ignore[arg-type]
            eisenhower=coerced_eisenhower,
            estimate=coerced_estimate,
            progress=coerced_progress,
            goal_id=goal_id,
            scheduled_on=parsed_scheduled_on,
        )

        # Use LunaTask client to create the task
        async with lunatask_client as client:
            created_task = await client.create_task(task_data)

        # Return success response with task ID
        result = {
            "success": True,
            "task_id": created_task.id,
            "message": "Task created successfully",
        }

    except LunaTaskValidationError as e:
        # Handle validation errors (422)
        error_msg = f"Task validation failed: {e}"
        result = {
            "success": False,
            "error": "validation_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Task validation error: %s", e)
        return result

    except LunaTaskSubscriptionRequiredError as e:
        # Handle subscription required errors (402)
        error_msg = f"Subscription required: {e}"
        result = {
            "success": False,
            "error": "subscription_required",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.warning("Subscription required for task creation: %s", e)
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
        logger.warning("Authentication error during task creation: %s", e)
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
        logger.warning("Rate limit exceeded during task creation: %s", e)
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
        logger.warning("Server error during task creation: %s", e)
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
        logger.warning("API error during task creation: %s", e)
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
                elif field == "estimate":
                    msg = "Must be a positive integer (minutes)"
                elif field == "progress":
                    msg = "Must be an integer between 0 and 100 (percentage)"
                elif field == "scheduled_on":
                    msg = "Must be in YYYY-MM-DD format"
                error_details.append(f"{field}: {msg}")

            error_msg = f"Validation failed for {', '.join(error_details)}"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Task validation error: %s", error_msg)
            return result
        # Handle unexpected errors
        error_msg = f"Unexpected error creating task: {e}"
        result = {
            "success": False,
            "error": "unexpected_error",
            "message": error_msg,
        }
        await ctx.error(error_msg)
        logger.exception("Unexpected error during task creation")
        return result
    else:
        await ctx.info(f"Successfully created task {created_task.id}")
        return result
