"""Factory functions for creating test data objects.

This module contains small builder functions for creating TaskResponse and Source
objects for use in tests. These functions help reduce duplication in test setup
while keeping the construction explicit and readable.
"""

from datetime import UTC, date, datetime

from lunatask_mcp.api.models import Source, TaskResponse


def create_source(source_type: str = "manual", value: str | None = "user_created") -> Source:
    """Create a Source object with default or provided values.

    Args:
        source_type: The source type (default: "manual")
        value: The source value (default: "user_created")

    Returns:
        A Source object with the specified values
    """
    return Source(type=source_type, value=value)


# TODO: Refactor create_task response with `TypedDict` to avoid too many arguments
def create_task_response(  # noqa: PLR0913  # Factory functions need many parameters to reduce test duplication
    task_id: str = "task-1",
    status: str = "later",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    priority: int = 0,
    scheduled_on: date | None = None,
    area_id: str = "default-area",
    source: Source | None = None,
    goal_id: str | None = None,
    estimate: int | None = None,
    motivation: str = "unknown",
    eisenhower: int = 0,
    previous_status: str | None = None,
    progress: int | None = None,
    completed_at: datetime | None = None,
) -> TaskResponse:
    """Create a TaskResponse object with default or provided values.

    Args:
        task_id: Task ID (default: "task-1")
        status: Task status (default: "later")
        created_at: Creation timestamp (default: 2025-08-20 10:00:00 UTC)
        updated_at: Last update timestamp (default: 2025-08-20 10:30:00 UTC)
        priority: Task priority (default: 0)
        scheduled_on: Date when task is scheduled
        area_id: Area ID (default: "default-area")
        source: Source object
        goal_id: Goal ID
        estimate: Estimated duration in minutes
        motivation: Task motivation level (default: "unknown")
        eisenhower: Eisenhower matrix quadrant (default: 0)
        previous_status: Previous task status
        progress: Task completion percentage
        completed_at: Task completion timestamp

    Returns:
        A TaskResponse object with the specified values
    """
    # Set default timestamps if not provided
    if created_at is None:
        created_at = datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC)
    if updated_at is None:
        updated_at = datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC)

    return TaskResponse(
        id=task_id,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        priority=priority,
        scheduled_on=scheduled_on,
        area_id=area_id,
        source=source,
        goal_id=goal_id,
        estimate=estimate,
        motivation=motivation,
        eisenhower=eisenhower,
        previous_status=previous_status,
        progress=progress,
        completed_at=completed_at,
    )
