"""Data models for LunaTask API requests and responses.

This module defines Pydantic models and enums used to parse and validate
LunaTask API data. Request models use field constraints for numeric bounds
and `StrEnum` for string enums to generate clearer schemas and consistent
validation errors.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class TaskStatus(StrEnum):
    """Status values accepted by LunaTask task creation/update."""

    LATER = "later"
    NEXT = "next"
    STARTED = "started"
    WAITING = "waiting"
    COMPLETED = "completed"


class TaskMotivation(StrEnum):
    """Motivation values accepted by LunaTask task creation/update."""

    MUST = "must"
    SHOULD = "should"
    WANT = "want"
    UNKNOWN = "unknown"


# Constants for validation bounds
MIN_PRIORITY = -2
MAX_PRIORITY = 2
MIN_EISENHOWER = 0
MAX_EISENHOWER = 4


class Source(BaseModel):
    """Source information for task origin."""

    type: str = Field(..., description="Type of source (e.g., 'email', 'web', 'manual')")
    value: str | None = Field(None, description="Source value or identifier")


class TaskPayload(BaseModel):
    """Shared request payload fields for task create/update.

    This base model centralizes field declarations and validation constraints
    common to both `TaskCreate` and `TaskUpdate`. Fields that need defaults
    for creation are overridden in `TaskCreate` with proper non-None defaults.

    Notes:
        - Enum and bounds validation live here so both subclasses stay in sync.
        - Outbound serialization uses enum string values (`use_enum_values=True`).
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    # Shared relational/context fields
    area_id: str = Field(description="Area ID the task belongs to")
    goal_id: str | None = Field(
        default=None,
        description=(
            "ID of the goal where the task should belong to (optional, "
            "can be found in our apps in the goal's settings)"
        ),
    )

    # State and prioritization - kept as None for TaskUpdate's PATCH semantics
    # TaskCreate will override these with proper defaults
    status: TaskStatus = Field(default=TaskStatus.LATER, description="Task status")
    estimate: int | None = Field(default=None, description="Estimated duration in minutes")
    priority: int = Field(
        default=0,
        ge=MIN_PRIORITY,
        le=MAX_PRIORITY,
        description=f"Task priority level [{MIN_PRIORITY}, {MAX_PRIORITY}]",
    )
    progress: int | None = Field(default=None, description="Task completion percentage")
    motivation: TaskMotivation | None = Field(
        default=None, description="Task motivation level (must, should, want, unknown)"
    )
    eisenhower: int | None = Field(
        default=None,
        ge=MIN_EISENHOWER,
        le=MAX_EISENHOWER,
        description=f"Eisenhower matrix quadrant [{MIN_EISENHOWER}, {MAX_EISENHOWER}]",
    )
    scheduled_on: date | None = Field(
        default=None, description="Date when task is scheduled (YYYY-MM-DD format, date-only)"
    )
    source: Source | None = Field(default=None, description="Task source information")


class TaskResponse(BaseModel):
    """Response model for LunaTask task data.

    This model represents a task as returned by the LunaTask API in wrapped format.
    API returns tasks in: {"tasks": [TaskResponse, ...]}
    Note: Encrypted fields (name, note) are not included due to E2E encryption.
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(description="The ID of the task (UUID)")
    previous_status: TaskStatus | None = Field(default=None, description="Previous task status")
    completed_at: datetime | None = Field(None, description="Task completion timestamp")
    created_at: datetime = Field(description="Task creation timestamp")
    updated_at: datetime = Field(description="Task last update timestamp")

    # Fields that overlap with payloads but may have different validation (e.g., non-nullable)
    area_id: str = Field(..., description="The ID of the area the task belongs in")
    goal_id: str | None = Field(None, description="The ID of the goal the task belongs in")
    status: TaskStatus = Field(description="Task status")
    estimate: int | None = Field(None, description="Estimated duration in minutes")
    priority: int = Field(..., ge=MIN_PRIORITY, le=MAX_PRIORITY, description="Current priority")
    progress: int | None = Field(None, description="Task completion percentage")
    motivation: TaskMotivation = Field(
        default=TaskMotivation.UNKNOWN, description="Task motivation"
    )
    eisenhower: int = Field(
        0, ge=MIN_EISENHOWER, le=MAX_EISENHOWER, description="Eisenhower matrix quadrant"
    )
    scheduled_on: date | None = Field(None, description="Date when task is scheduled")
    source: Source | None = Field(None, description="Task source information")

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]


class TaskCreate(TaskPayload):
    """Request model for creating new tasks in LunaTask.

    Inherits shared fields and validation from `TaskPayload` and applies
    create-time defaults and requirements. Overrides specific fields with
    proper non-None defaults to ensure explicit validation behavior.
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    # Encrypted content fields (present in write payloads only)
    name: str = Field(description="Task name (gets encrypted client-side)")
    note: str | None = Field(
        default=None, description="Task note in Markdown (encrypted client-side)"
    )

    status: TaskStatus = Field(default=TaskStatus.LATER, description="Task status")

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]


class TaskUpdate(BaseModel):
    """Partial update payload for existing tasks.

    All fields are optional to support PATCH semantics. Outbound serialization
    relies on `model_dump(exclude_none=True)` at call sites to send only changed
    fields. Field validation constraints are maintained from TaskPayload.
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    # Required field for updates
    id: str = Field(description="The ID of the task (UUID)")

    # Optional relational/context fields
    area_id: str | None = Field(None, description="Area ID the task belongs to")
    goal_id: str | None = Field(
        None,
        description=(
            "ID of the goal where the task should belong to (optional, "
            "can be found in our apps in the goal's settings)"
        ),
    )

    # Optional encrypted content fields
    name: str | None = Field(None, description="Task name (gets encrypted client-side)")
    note: str | None = Field(None, description="Task note in Markdown (encrypted client-side)")

    # Optional state and prioritization fields
    status: TaskStatus | None = Field(None, description="Task status")
    estimate: int | None = Field(None, description="Estimated duration in minutes")
    priority: int | None = Field(
        None,
        ge=MIN_PRIORITY,
        le=MAX_PRIORITY,
        description=f"Task priority level [{MIN_PRIORITY}, {MAX_PRIORITY}]",
    )
    progress: int | None = Field(None, description="Task completion percentage")
    motivation: TaskMotivation | None = Field(
        None, description="Task motivation level (must, should, want, unknown)"
    )
    eisenhower: int | None = Field(
        None,
        ge=MIN_EISENHOWER,
        le=MAX_EISENHOWER,
        description=f"Eisenhower matrix quadrant [{MIN_EISENHOWER}, {MAX_EISENHOWER}]",
    )
    scheduled_on: date | None = Field(
        None, description="Date when task is scheduled (YYYY-MM-DD format, date-only)"
    )
    source: Source | None = Field(None, description="Task source information")

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]
