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


async def tasks_discovery_resource(
    _lunatask_client: LunaTaskClient, ctx: Context
) -> dict[str, Any]:
    """Return discovery metadata for task list resources.

    Provides a read-only JSON description of supported parameters, defaults,
    limits, canonical alias examples (area and global families), and guardrails.

    Args:
        lunatask_client: Injected LunaTaskClient (unused; reserved for parity)
        ctx: MCP request context used for logging

    Returns:
        dict[str, Any]: Discovery document describing list resource behavior
    """
    # Log via MCP context; do not emit tokens or sensitive data
    await ctx.info("Serving tasks discovery")

    # Keep keys aligned with the proposal addendum; prefer explicit, minimal schema.
    discovery: dict[str, Any] = {
        "resource_type": "lunatask_tasks_discovery",
        "params": {
            "area_id": "string",
            "scope": "global",
            "window": "today|overdue|next_7_days|now",
            "status": "open|completed|next|started|now",
            "min_priority": "low|medium|high",
            "priority": ["low", "medium", "high"],
            "completed_since": "-72h|ISO8601",
            "tz": "UTC",
            "q": "string",
            "limit": 50,
            "cursor": "opaque",
            "sort": "priority.desc,due_date.asc,id.asc",
        },
        "defaults": {
            "status": "open",
            "limit": 50,
            "sort": "priority.desc,due_date.asc,id.asc",
            "tz": "UTC",
        },
        "limits": {"max_limit": 50, "dense_cap": 25},
        "projection": [
            "id",
            "due_date",
            "priority",
            "status",
            "area_id",
            "list_id",
            "detail_uri",
        ],
        "sorts": {
            "default": "priority.desc,due_date.asc,id.asc",
            "overdue": "due_date.asc,priority.desc,id.asc",
            "recent_completions": "completed_at.desc,id.asc",
        },
        "aliases": [
            {
                "family": "area",
                "name": "now",
                "uri": "lunatask://area/{area_id}/now",
                # Canonical params sorted by key: area_id, limit, status, window
                "canonical": ("lunatask://tasks?area_id={area_id}&limit=25&status=open&window=now"),
            },
            {
                "family": "global",
                "name": "overdue",
                "uri": "lunatask://global/overdue",
                # Canonical params sorted by key with explicit scope=global
                "canonical": (
                    "lunatask://tasks?limit=50&scope=global&sort=due_date.asc,priority.desc,id.asc"
                    "&status=open&window=overdue"
                ),
            },
        ],
        "guardrails": {
            "unscoped_error_code": "LUNA_TASKS/UNSCOPED_LIST",
            "message": "Provide area_id or scope=global for list views.",
            "examples": [
                "lunatask://area/AREA123/today",
                "lunatask://global/next-7-days",
            ],
        },
        "examples": [
            "lunatask://tasks",
            "lunatask://area/{area_id}/now",
            "lunatask://global/overdue",
        ],
    }
    return discovery


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


def _get_alias_params(alias: str) -> dict[str, Any] | None:
    """Map an alias string to a dictionary of canonical query parameters."""
    if alias in ("now", "today", "overdue", "next_7_days"):
        return {"window": alias, "status": "open", "limit": 25 if alias == "now" else 50}
    if alias == "high_priority":
        return {"min_priority": "high", "status": "open", "limit": 50}
    if alias == "recent_completions":
        return {"status": "completed", "completed_since": "-72h", "limit": 50}
    return None


async def list_tasks_global_alias(
    lunatask_client: LunaTaskClient,
    ctx: Context,
    *,
    alias: str,
) -> dict[str, Any]:
    """List tasks for a global alias with deterministic ordering.

    Args:
        lunatask_client: Injected LunaTaskClient.
        ctx: MCP context for stderr-only logging.
        alias: One of "now", "today", "overdue", "next_7_days",
               "high_priority", "recent_completions".

    Returns:
        dict[str, Any]: Minimal projection list with items and metadata.
    """
    params = _get_alias_params(alias)
    if params is None:
        await ctx.error(f"Unknown alias: {alias}")
        raise LunaTaskBadRequestError

    params["scope"] = "global"

    await ctx.info(
        f"Listing global tasks: alias={alias}, params={{'status': {params.get('status')}, "
        f"'limit': {params.get('limit')}}}"
    )

    async with lunatask_client:
        tasks = await lunatask_client.get_tasks(**params)

    # Deterministic ordering client-side to ensure stability regardless of upstream
    if alias == "overdue":
        tasks.sort(
            key=lambda t: (  # due_date.asc, priority.desc, id.asc
                ((0, int(t.due_date.timestamp())) if t.due_date else (1, 0)),
                -(t.priority if t.priority is not None else -10),
                t.id,
            )
        )
        sort = "due_date.asc,priority.desc,id.asc"
    elif alias == "recent_completions":
        tasks.sort(
            key=lambda t: (
                (0, -int(t.completed_at.timestamp())) if t.completed_at else (1, 0),
                t.id,
            )
        )
        sort = "completed_at.desc,id.asc"
    else:
        tasks.sort(
            key=lambda t: (  # priority.desc, due_date.asc, id.asc
                -(t.priority if t.priority is not None else -10),
                ((0, int(t.due_date.timestamp())) if t.due_date else (1, 0)),
                t.id,
            )
        )
        sort = "priority.desc,due_date.asc,id.asc"

    items = [
        {**serialize_task_response(t), "detail_uri": f"lunatask://tasks/{t.id}"} for t in tasks
    ]

    return {"items": items, "limit": params.get("limit", 50), "sort": sort}


async def list_tasks_area_alias(
    lunatask_client: LunaTaskClient,
    ctx: Context,
    *,
    area_id: str,
    alias: str,
) -> dict[str, Any]:
    """List tasks for a specific area alias.

    Args:
        lunatask_client: Injected LunaTaskClient.
        ctx: MCP context for stderr-only logging.
        area_id: Area identifier to scope the query.
        alias: One of "now", "today", "overdue", "next_7_days",
               "high_priority", "recent_completions".

    Returns:
        dict[str, Any]: A minimal projection list with items and metadata.
    """
    if not area_id:
        await ctx.error("Missing required parameter: area_id")
        raise LunaTaskBadRequestError

    params = _get_alias_params(alias)
    if params is None:
        await ctx.error(f"Unknown alias: {alias}")
        raise LunaTaskBadRequestError

    params["area_id"] = area_id

    await ctx.info(
        f"Listing tasks for area {area_id}: alias={alias}, params="
        f"{{'status': {params.get('status')}, 'limit': {params.get('limit')}}}"
    )

    async with lunatask_client:
        tasks = await lunatask_client.get_tasks(**params)

    items = [
        {**serialize_task_response(t), "detail_uri": f"lunatask://tasks/{t.id}"} for t in tasks
    ]

    # Provide minimal response shape with deterministic sort hint
    sort = (
        "due_date.asc,priority.desc,id.asc"
        if alias == "overdue"
        else "priority.desc,due_date.asc,id.asc"
    )

    return {"items": items, "limit": params.get("limit", 50), "sort": sort}
