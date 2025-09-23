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

from lunatask_mcp.api.models import JournalEntryResponse, NoteResponse, TaskResponse

# People models will be available after Phase 2 implementation
try:
    from lunatask_mcp.api.models_people import PersonResponse
except ImportError:
    # Placeholder for TDD phase - will be replaced with actual import
    PersonResponse = None  # type: ignore[misc,assignment]

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


def create_journal_entry_response(  # noqa: PLR0913
    entry_id: str = "journal-entry-1",
    date_on: date = date(2025, 9, 20),
    name: str | None = None,
    content: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> JournalEntryResponse:
    """Create a JournalEntryResponse object with default or provided values."""

    if created_at is None:
        created_at = datetime(2025, 9, 20, 7, 30, tzinfo=UTC)
    if updated_at is None:
        updated_at = datetime(2025, 9, 20, 7, 35, tzinfo=UTC)

    payload = {
        "id": entry_id,
        "date_on": date_on,
        "created_at": created_at,
        "updated_at": updated_at,
    }

    # The API omits name/content fields in responses; include only when provided for tests.
    if name is not None:
        payload["name"] = name
    if content is not None:
        payload["content"] = content

    return JournalEntryResponse(**payload)


def create_person_response(  # noqa: PLR0913
    person_id: str = "5999b945-b2b1-48c6-aa72-b251b75b3c2e",
    relationship_strength: str = "casual-friends",
    source: str | None = None,
    source_id: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    email: str | None = None,
    birthday: date | None = None,
    phone: str | None = None,
) -> object:
    """Create a PersonResponse object with default or provided values.

    Args:
        person_id: Person ID (default: "5999b945-b2b1-48c6-aa72-b251b75b3c2e")
        relationship_strength: Relationship strength (default: "casual-friends")
        source: Source system identifier (default: None)
        source_id: Source system record ID (default: None)
        created_at: Creation timestamp (default: 2021-01-10 10:39:25 UTC)
        updated_at: Last update timestamp (default: 2021-01-10 10:39:25 UTC)
        email: Person's email address (default: None)
        birthday: Person's birthday (default: None)
        phone: Person's phone number (default: None)

    Returns:
        PersonResponse object suitable for mocking API responses.
    """
    if created_at is None:
        created_at = datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC)
    if updated_at is None:
        updated_at = datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC)

    # Handle sources similar to other response factories
    if source is not None or source_id is not None:
        sources_payload = [{"source": source, "source_id": source_id}]
    else:
        sources_payload = []

    # During TDD phase, return a mock object that behaves like PersonResponse
    if PersonResponse is None:
        # Return a simple object with the expected attributes for testing
        class MockPersonResponse:
            def __init__(self, **kwargs: object) -> None:
                for key, value in kwargs.items():
                    setattr(self, key, value)

        return MockPersonResponse(
            id=person_id,
            relationship_strength=relationship_strength,
            sources=sources_payload,
            created_at=created_at,
            updated_at=updated_at,
            email=email,
            birthday=birthday,
            phone=phone,
        )

    # Once PersonResponse is implemented, use the real model
    return PersonResponse(
        id=person_id,
        relationship_strength=relationship_strength,
        source=source,
        source_id=source_id,
        created_at=created_at,
        updated_at=updated_at,
        email=email,
        birthday=birthday,
        phone=phone,
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
