"""Common helpers for task tools.

Provides shared serialization utilities used by task resource and tool handlers.
"""

from __future__ import annotations

from typing import Any

from lunatask_mcp.api.models import TaskResponse


def serialize_task_response(task: TaskResponse) -> dict[str, Any]:
    """Convert a TaskResponse object to a dictionary for JSON serialization.

    This shared helper method provides consistent serialization of TaskResponse
    objects across all task-related resources, ensuring proper handling of
    optional fields and datetime formatting.

    Args:
        task: TaskResponse object to serialize

    Returns:
        dict[str, Any]: Serialized task data suitable for JSON responses
    """
    return {
        "id": task.id,
        "area_id": task.area_id,
        "status": task.status,
        "priority": task.priority,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "source": {
            "type": task.source.type,
            "value": task.source.value,
        }
        if task.source
        else None,
        "goal_id": task.goal_id,
        "estimate": task.estimate,
        "motivation": task.motivation,
        "eisenhower": task.eisenhower,
        "previous_status": task.previous_status,
        "progress": task.progress,
        "scheduled_on": task.scheduled_on.isoformat() if task.scheduled_on else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }
