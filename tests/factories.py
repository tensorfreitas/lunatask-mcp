"""Factory functions for creating test data objects.

This module contains small builder functions for creating TaskResponse objects
for use in tests. These functions help reduce duplication in test setup while
keeping the construction explicit and readable.
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import LiteralString, cast

from pydantic import ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError

from lunatask_mcp.api.models import NoteResponse, TaskResponse

VALID_ESTIMATE_MINUTES = 45
VALID_PROGRESS_PERCENT = 80
VALID_GOAL_ID = "goal-123"
VALID_SCHEDULED_ON = date(2025, 9, 1)


# TODO: Refactor create_task response with `TypedDict` to avoid too many arguments
def create_task_response(  # noqa: PLR0913  # Factory functions need many parameters to reduce test duplication
    task_id: str = "task-1",
    status: str = "later",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    priority: int = 0,
    scheduled_on: date | None = None,
    area_id: str = "default-area",
    sources: Sequence[dict[str, str | None]] | None = None,
    source: str | None = None,
    source_id: str | None = None,
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
        sources: Iterable of source dictionaries from API (overrides source/source_id)
        source: Task source label (e.g., "github")
        source_id: Task source identifier (e.g., external record ID)
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

    if sources is None:
        sources_payload: list[dict[str, str | None]] = []
        if source is not None or source_id is not None:
            sources_payload.append(
                {
                    "source": source,
                    "source_id": source_id,
                }
            )
    else:
        sources_payload = [
            {
                "source": payload.get("source"),
                "source_id": payload.get("source_id"),
            }
            for payload in sources
        ]

    return TaskResponse(
        id=task_id,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        priority=priority,
        scheduled_on=scheduled_on,
        area_id=area_id,
        sources=sources_payload,
        goal_id=goal_id,
        estimate=estimate,
        motivation=motivation,
        eisenhower=eisenhower,
        previous_status=previous_status,
        progress=progress,
        completed_at=completed_at,
    )


def create_note_response(  # noqa: PLR0913
    note_id: str = "note-1",
    notebook_id: str | None = "notebook-123",
    date_on: date | None = VALID_SCHEDULED_ON,
    sources: Sequence[dict[str, str | None]] | None = None,
    source: str | None = None,
    source_id: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> NoteResponse:
    """Create a NoteResponse object with default or provided values."""

    if created_at is None:
        created_at = datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC)
    if updated_at is None:
        updated_at = datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC)

    if sources is None:
        sources_payload: list[dict[str, str | None]] = []
        if source is not None or source_id is not None:
            sources_payload.append({"source": source, "source_id": source_id})
    else:
        sources_payload = [
            {"source": payload.get("source"), "source_id": payload.get("source_id")}
            for payload in sources
        ]

    return NoteResponse(
        id=note_id,
        notebook_id=notebook_id,
        date_on=date_on,
        sources=sources_payload,
        created_at=created_at,
        updated_at=updated_at,
        deleted_at=deleted_at,
    )


def build_validation_error(
    model_name: str,
    validation_entries: Sequence[tuple[str, str, object]],
) -> ValidationError:
    """Create a Pydantic ValidationError with provided field messages.

    Args:
        model_name: Name of the model associated with the validation error.
        validation_entries: Iterable of tuples describing field validation errors
            as (field_name, message, invalid_value).

    Returns:
        ValidationError: Validation error instance containing all provided entries.
    """

    error_details: list[InitErrorDetails] = []
    for field_name, message, invalid_value in validation_entries:
        literal_message: LiteralString = cast(LiteralString, message)
        error_details.append(
            {
                "type": PydanticCustomError("value_error", literal_message),
                "loc": (field_name,),
                "input": invalid_value,
            }
        )

    return ValidationError.from_exception_data(model_name, error_details)
