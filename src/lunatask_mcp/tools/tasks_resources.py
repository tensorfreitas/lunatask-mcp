"""Task resource handlers for LunaTask MCP integration.

These functions implement the MCP resource endpoints for listing tasks and
retrieving single tasks, designed to be bound as methods of TaskTools.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
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
from lunatask_mcp.api.models import TaskResponse
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
            # Upstream-supported statuses; "open" is a composite (not forwarded upstream)
            "status": "later|next|started|waiting|completed",
            "min_priority": "low|medium|high",
            "priority": ["low", "medium", "high"],
            "completed_since": "-72h|ISO8601",
            "tz": "UTC",
            "q": "string",
            "limit": 50,
            "cursor": "opaque",
            "sort": "priority.desc,scheduled_on.asc,id.asc",
        },
        "defaults": {
            "status": "open",
            "limit": 50,
            "sort": "priority.desc,scheduled_on.asc,id.asc",
            "tz": "UTC",
        },
        "limits": {"max_limit": 50, "dense_cap": 25},
        "projection": [
            "id",
            "scheduled_on",
            "priority",
            "status",
            "area_id",
            "list_id",
            "detail_uri",
        ],
        "sorts": {
            "default": "priority.desc,scheduled_on.asc,id.asc",
            "overdue": "scheduled_on.asc,priority.desc,id.asc",
            "recent_completions": "completed_at.desc,id.asc",
        },
        "aliases": [
            {
                "family": "area",
                "name": "now",
                "uri": "lunatask://area/{area_id}/now",
                # Canonical params sorted by key: area_id, limit, status, window
                "canonical": ("lunatask://tasks?area_id={area_id}&limit=25&status=open"),
            },
            {
                "family": "global",
                "name": "overdue",
                "uri": "lunatask://global/overdue",
                # Canonical params sorted by key with explicit scope=global
                "canonical": (
                    "lunatask://tasks?limit=50&scope=global&sort=scheduled_on.asc,priority.desc,id.asc"
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


def _get_alias_filter_criteria(alias: str) -> dict[str, Any] | None:
    """Map an alias string to client-side filtering criteria.

    Returns filtering criteria that will be applied after fetching tasks,
    since the LunaTask API doesn't support these advanced filtering parameters.

    Semantics adjustments:
    - "today": due today only (unchanged)
    - "now": client-side only; include UNDated tasks matching any of:
        * status == "started"
        * priority == 2
        * motivation == "must"
        * eisenhower == 1
      Always excludes completed tasks.
    """
    criteria_map = {
        # Special client-side criteria (no upstream window parameter)
        "now": {
            "filter_type": "now",
            "status_filter": "open",
            "limit": 25,
            "now_rules": {
                "require_no_scheduled_on": True,
                "include_status": {"started"},
                "include_priority_exact": {2},
                "include_motivation": {"must"},
                "include_eisenhower_exact": {1},
            },
        },
        # Time windows (applied upstream when possible, and client-side when needed)
        "today": {"filter_type": "window", "window": "today", "status_filter": "open", "limit": 50},
        "overdue": {
            "filter_type": "window",
            "window": "overdue",
            "status_filter": "open",
            "limit": 50,
        },
        "next_7_days": {
            "filter_type": "window",
            "window": "next_7_days",
            "status_filter": "open",
            "limit": 50,
        },
        "high_priority": {
            "filter_type": "priority",
            "min_priority": 1,  # High priority = 1 or 2 (range is -2 to 2)
            "status_filter": "open",
            "limit": 50,
        },
        "recent_completions": {
            "filter_type": "completion",
            "status_filter": "completed",
            "completed_hours_ago": 72,
            "limit": 50,
        },
    }
    return criteria_map.get(alias)


def _filter_by_status(tasks: Sequence[TaskResponse], status: str | None) -> list[TaskResponse]:
    """Filter tasks by status; supports composite 'open' (not completed)."""
    if not status:
        return list(tasks)
    if status == "open":
        return [t for t in tasks if t.status != "completed"]
    return [t for t in tasks if t.status == status]


def _filter_by_priority(tasks: Sequence[TaskResponse], min_priority: int) -> list[TaskResponse]:
    """Filter tasks by minimum priority threshold."""
    return [t for t in tasks if t.priority is not None and t.priority >= min_priority]


def _filter_by_completion_recent(
    tasks: Sequence[TaskResponse], hours_ago: int
) -> list[TaskResponse]:
    """Filter tasks completed within the last N hours."""
    cutoff_time = datetime.now(UTC) - timedelta(hours=hours_ago)
    return [t for t in tasks if t.completed_at is not None and t.completed_at >= cutoff_time]


def _filter_now_rules(tasks: Sequence[TaskResponse], rules: dict[str, Any]) -> list[TaskResponse]:
    """Apply custom 'now' rules to include unscheduled tasks only."""
    require_no_scheduled = bool(rules.get("require_no_scheduled_on", True))
    include_status = set(rules.get("include_status", set()))
    include_priority_exact = set(rules.get("include_priority_exact", set()))
    include_motivation = set(rules.get("include_motivation", set()))
    include_eisenhower_exact = set(rules.get("include_eisenhower_exact", set()))

    def should_include(t: TaskResponse) -> bool:
        if require_no_scheduled and t.scheduled_on is not None:
            return False
        if t.status in include_status:
            return True
        prio = t.priority
        if prio is not None and prio in include_priority_exact:
            return True
        mot = t.motivation
        if mot is not None and mot in include_motivation:
            return True
        eis = t.eisenhower
        return eis is not None and eis in include_eisenhower_exact

    return [t for t in tasks if should_include(t)]


def _apply_task_filters(
    tasks: Sequence[TaskResponse], filter_criteria: dict[str, Any]
) -> list[TaskResponse]:
    """Apply client-side filtering to tasks based on filter criteria."""
    if not filter_criteria:
        return list(tasks)

    filtered_tasks: list[TaskResponse] = list(tasks)
    filter_type = filter_criteria.get("filter_type")

    # Status first
    filtered_tasks = _filter_by_status(filtered_tasks, filter_criteria.get("status_filter"))

    # Then type-specific
    if filter_type == "window":
        filtered_tasks = _filter_by_time_window(filtered_tasks, filter_criteria["window"])
    elif filter_type == "priority":
        filtered_tasks = _filter_by_priority(filtered_tasks, filter_criteria["min_priority"])
    elif filter_type == "completion":
        filtered_tasks = _filter_by_completion_recent(
            filtered_tasks, filter_criteria["completed_hours_ago"]
        )
    elif filter_type == "now":
        filtered_tasks = _filter_now_rules(filtered_tasks, filter_criteria.get("now_rules", {}))

    return filtered_tasks


def _filter_today_scheduled_or_due(tasks: Sequence[TaskResponse]) -> list[TaskResponse]:
    """Return tasks scheduled or due today (UTC).

    Includes tasks where scheduled_on equals today's UTC date.
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_date = today_start.date()

    def is_today(t: TaskResponse) -> bool:
        return t.scheduled_on is not None and t.scheduled_on == today_date

    return [t for t in tasks if is_today(t)]


def _filter_by_time_window(tasks: list[TaskResponse], window: str) -> list[TaskResponse]:
    """Filter tasks by time window.

    Args:
        tasks: List of TaskResponse objects
        window: Time window ("now", "today", "overdue", "next_7_days")

    Returns:
        Filtered list of tasks
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _is_overdue(t: TaskResponse) -> bool:
        # Primary: scheduled_on before today (strictly prior days)
        return t.scheduled_on is not None and t.scheduled_on < today_start.date()

    if window == "now":
        # "Now" = items with no scheduled_on meeting existing heuristics
        # This should be handled by _filter_now_rules, not here
        return tasks
    if window == "today":
        # "Today" = scheduled_on == today (UTC)
        today_date = today_start.date()
        return [t for t in tasks if t.scheduled_on is not None and t.scheduled_on == today_date]
    if window == "overdue":
        # "Overdue" = scheduled_on < today (UTC)
        return [t for t in tasks if _is_overdue(t)]
    if window == "next_7_days":
        # "Next 7 days" (scheduled) = tasks with scheduled_on in (today, today+7] (UTC)
        # Excludes items scheduled today or in the past; includes up to and including day+7.
        next_week_date = (today_start + timedelta(days=7)).date()  # today_date + 7
        today_date = today_start.date()
        return [
            t
            for t in tasks
            if (t.scheduled_on is not None and today_date < t.scheduled_on <= next_week_date)
        ]

    return tasks


async def _fetch_tasks_for_global_alias(
    client: LunaTaskClient, filter_criteria: dict[str, Any], params: dict[str, str | int]
) -> tuple[list[TaskResponse], bool]:
    """Fetch tasks for a global alias and whether to apply client-side filtering."""
    should_filter = False
    ftype = filter_criteria["filter_type"]
    if ftype == "window":
        window = str(filter_criteria["window"])  # today|overdue|next_7_days|now
        if window != "now":
            params["window"] = window
            params["status"] = "open"
            # Apply client-side narrowing for windows that upstream may ignore
            if window in {"overdue", "next_7_days"}:
                if window == "overdue":
                    params["sort"] = "scheduled_on.asc,priority.desc,id.asc"
                should_filter = True
            return (await client.get_tasks(**params), should_filter)
        # now → client-side only
        should_filter = True
        return (await client.get_tasks(), should_filter)
    if ftype == "priority":
        params["min_priority"] = "high"
        params["status"] = "open"
        should_filter = True
        return (await client.get_tasks(**params), should_filter)
    if ftype == "completion":
        params["status"] = "completed"
        params["completed_since"] = "-72h"
        should_filter = True
        return (await client.get_tasks(**params), should_filter)
    if ftype == "now":
        should_filter = True
        return (await client.get_tasks(), should_filter)
    return (await client.get_tasks(**params), should_filter)


async def _fetch_tasks_for_area_alias(
    client: LunaTaskClient, filter_criteria: dict[str, Any], params: dict[str, str | int]
) -> tuple[list[TaskResponse], bool]:
    """Fetch tasks for an area alias and indicate if client-side filtering is needed."""
    should_filter = False
    ftype = filter_criteria["filter_type"]
    if ftype == "window":
        w = str(filter_criteria["window"])  # today|overdue|next_7_days
        params["window"] = w
        params["status"] = "open"
        # Apply client-side narrowing where upstream may ignore window
        if w in {"overdue", "next_7_days"}:
            if w == "overdue":
                params["sort"] = "scheduled_on.asc,priority.desc,id.asc"
            should_filter = True
        return (await client.get_tasks(**params), should_filter)
    if ftype == "priority":
        params["min_priority"] = "high"
        params["status"] = "open"
        should_filter = True
        return (await client.get_tasks(**params), should_filter)
    if ftype == "completion":
        params["status"] = "completed"
        params["completed_since"] = "-72h"
        return (await client.get_tasks(**params), should_filter)
    if ftype == "now":
        params["status"] = "open"
        should_filter = True
        return (await client.get_tasks(**params), should_filter)
    return (await client.get_tasks(**params), should_filter)


def _sort_tasks_for_alias(alias: str, tasks: list[TaskResponse]) -> tuple[list[TaskResponse], str]:
    """Return tasks sorted for the alias and the sort string used."""
    sorted_tasks = list(tasks)
    if alias == "overdue":
        sorted_tasks.sort(
            key=lambda t: (
                ((0, int(t.scheduled_on.toordinal())) if t.scheduled_on else (1, 0)),
                -(t.priority if t.priority is not None else -10),
                t.id,
            )
        )
        return sorted_tasks, "scheduled_on.asc,priority.desc,id.asc"
    if alias == "recent_completions":
        sorted_tasks.sort(
            key=lambda t: (
                (0, -int(t.completed_at.timestamp())) if t.completed_at else (1, 0),
                t.id,
            )
        )
        return sorted_tasks, "completed_at.desc,id.asc"
    sorted_tasks.sort(
        key=lambda t: (
            -(t.priority if t.priority is not None else -10),
            ((0, int(t.scheduled_on.toordinal())) if t.scheduled_on else (1, 0)),
            t.id,
        )
    )
    return sorted_tasks, "priority.desc,scheduled_on.asc,id.asc"


async def list_tasks_global_alias(
    lunatask_client: LunaTaskClient,
    ctx: Context,
    *,
    alias: str,
) -> dict[str, Any]:
    """List tasks for a global alias with client-side filtering and deterministic ordering.

    Args:
        lunatask_client: Injected LunaTaskClient.
        ctx: MCP context for stderr-only logging.
        alias: One of "now", "today", "overdue", "next_7_days",
               "high_priority", "recent_completions".

    Returns:
        dict[str, Any]: Minimal projection list with filtered items and metadata.
    """
    filter_criteria = _get_alias_filter_criteria(alias)
    if filter_criteria is None:
        await ctx.error(f"Unknown alias: {alias}")
        raise LunaTaskBadRequestError.unknown_alias(alias)

    await ctx.info(f"Listing global tasks with client-side filtering: alias={alias}")

    # Build canonical params but special-case "now" to call API without filters
    params: dict[str, str | int] = {"scope": "global"}
    limit = int(filter_criteria["limit"])  # 25 for now, else 50
    params["limit"] = limit

    should_filter = False
    async with lunatask_client:
        all_tasks, should_filter = await _fetch_tasks_for_global_alias(
            lunatask_client, filter_criteria, params
        )

    # For time/priority windows that require client-side filtering, apply it now.
    filtered_tasks = (
        _apply_task_filters(all_tasks, filter_criteria) if should_filter else list(all_tasks)
    )

    # If upstream 'today' window appears too broad, narrow locally using schedule/due.
    if alias == "today" and any(getattr(t, "scheduled_on", None) is not None for t in all_tasks):
        await ctx.info("Applying client-side 'today' filter by scheduled_on")
        filtered_tasks = _filter_today_scheduled_or_due(all_tasks)

    # Fallback: if overdue alias yields no results, retry without window upstream and
    # filter client-side only. This guards against upstreams that ignore or reject
    # non-standard params (e.g., window/scope) or return pages that miss overdue items.
    if alias == "overdue" and not filtered_tasks:
        await ctx.info(
            "No items after overdue filter; retrying without window for client-side filtering"
        )
        fallback_params: dict[str, str | int] = {
            "scope": "global",
            "limit": limit,
            "status": "open",
        }
        # Provide a sort hint to increase likelihood of capturing earliest due tasks
        fallback_params["sort"] = "scheduled_on.asc,id.asc"
        async with lunatask_client:
            all_tasks = await lunatask_client.get_tasks(**fallback_params)
        filtered_tasks = _apply_task_filters(all_tasks, filter_criteria)

    await ctx.info(f"Filtered {len(all_tasks)} tasks to {len(filtered_tasks)} for alias {alias}")

    # Apply deterministic ordering based on alias type
    if alias == "overdue":
        filtered_tasks.sort(
            key=lambda t: (  # scheduled_on.asc, priority.desc, id.asc
                ((0, int(t.scheduled_on.toordinal())) if t.scheduled_on else (1, 0)),
                -(t.priority if t.priority is not None else -10),
                t.id,
            )
        )
        sort = "scheduled_on.asc,priority.desc,id.asc"
    elif alias == "recent_completions":
        filtered_tasks.sort(
            key=lambda t: (
                (0, -int(t.completed_at.timestamp())) if t.completed_at else (1, 0),
                t.id,
            )
        )
        sort = "completed_at.desc,id.asc"
    else:
        filtered_tasks.sort(
            key=lambda t: (  # priority.desc, scheduled_on.asc, id.asc
                -(t.priority if t.priority is not None else -10),
                ((0, int(t.scheduled_on.toordinal())) if t.scheduled_on else (1, 0)),
                t.id,
            )
        )
        sort = "priority.desc,scheduled_on.asc,id.asc"

    # Apply limit after filtering and sorting
    limited_tasks = filtered_tasks[:limit]

    items = [
        {**serialize_task_response(t), "detail_uri": f"lunatask://tasks/{t.id}"}
        for t in limited_tasks
    ]

    return {"items": items, "limit": limit, "sort": sort}


async def list_tasks_area_alias(
    lunatask_client: LunaTaskClient,
    ctx: Context,
    *,
    area_id: str,
    alias: str,
) -> dict[str, Any]:
    """List tasks for a specific area alias with client-side filtering.

    Args:
        lunatask_client: Injected LunaTaskClient.
        ctx: MCP context for stderr-only logging.
        area_id: Area identifier to scope the query.
        alias: One of "now", "today", "overdue", "next_7_days",
               "high_priority", "recent_completions".

    Returns:
        dict[str, Any]: A minimal projection list with filtered items and metadata.
    """
    if not area_id:
        await ctx.error("Missing required parameter: area_id")
        raise LunaTaskBadRequestError.missing_area_id()

    filter_criteria = _get_alias_filter_criteria(alias)
    if filter_criteria is None:
        await ctx.error(f"Unknown alias: {alias}")
        raise LunaTaskBadRequestError.unknown_alias(alias)

    await ctx.info(f"Listing tasks for area {area_id} with client-side filtering: alias={alias}")

    # Build canonical query parameters and fetch once via helper
    params: dict[str, str | int] = {"area_id": area_id}
    limit = int(filter_criteria["limit"])  # 25 for now, else 50
    params["limit"] = limit

    async with lunatask_client:
        all_tasks, should_filter = await _fetch_tasks_for_area_alias(
            lunatask_client, filter_criteria, params
        )

    # Always scope to the requested area_id client-side to guard against upstream
    # ignoring area filters. Then apply alias filters deterministically.
    scoped = [t for t in all_tasks if getattr(t, "area_id", None) == area_id]
    filtered_tasks = _apply_task_filters(scoped, filter_criteria) if should_filter else list(scoped)

    # Apply the same client-side correction for "today" as global: if scheduled_on
    # hints are present, restrict to items scheduled/due today within the area.
    if alias == "today" and any(getattr(t, "scheduled_on", None) is not None for t in scoped):
        await ctx.info("Applying client-side area 'today' filter by scheduled_on")
        filtered_tasks = _filter_today_scheduled_or_due(scoped)

    await ctx.info(
        f"Retrieved {len(all_tasks)} tasks for area {area_id}; returning {len(filtered_tasks)}"
    )

    # Apply deterministic ordering
    filtered_tasks, sort = _sort_tasks_for_alias(alias, filtered_tasks)

    # Apply limit after filtering and sorting
    limit = filter_criteria["limit"]
    limited_tasks = filtered_tasks[:limit]

    items = [
        {**serialize_task_response(t), "detail_uri": f"lunatask://tasks/{t.id}"}
        for t in limited_tasks
    ]

    return {"items": items, "limit": limit, "sort": sort}
