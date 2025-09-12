"""Data models for LunaTask API requests and responses.

This module defines Pydantic models and enums used to parse and validate
LunaTask API data. Request models use field constraints for numeric bounds
and `StrEnum` for string enums to generate clearer schemas and consistent
validation errors.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import cast

from pydantic import BaseModel, Field, model_validator
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


class TaskResponse(BaseModel):
    """Response model for LunaTask task data.

    This model represents a task as returned by the LunaTask API in wrapped format.
    API returns tasks in: {"tasks": [TaskResponse, ...]}
    Note: Encrypted fields (name, note) are not included due to E2E encryption.
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)
    id: str = Field(..., description="The ID of the task (UUID)")
    area_id: str | None = Field(
        None, description="The ID of the area of life the task belongs in (UUID)"
    )
    goal_id: str | None = Field(None, description="The ID of the goal the task belongs in (UUID)")
    status: TaskStatus | str = Field(
        default=TaskStatus.LATER, description="Task status (default: 'later')"
    )
    previous_status: TaskStatus | str | None = Field(
        default=None, description="Previous task status"
    )
    estimate: int | None = Field(None, description="Estimated duration in minutes")
    priority: int | None = Field(default=0, description="Current priority")
    progress: int | None = Field(None, description="Task completion percentage")
    motivation: TaskMotivation | str | None = Field(
        None, description="Task motivation level (must, should, want, unknown)"
    )
    eisenhower: int | None = Field(default=None, description="Eisenhower matrix quadrant")
    source: Source | None = Field(None, description="Task source information")
    scheduled_on: date | None = Field(
        None, description="Date when task is scheduled (YYYY-MM-DD format, date-only)"
    )
    completed_at: datetime | None = Field(None, description="Task completion timestamp")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")

    # Note: 'name' and 'note' fields are not included due to E2E encryption
    # and are not returned in GET responses from the LunaTask API


class TaskPayload(BaseModel):
    """Shared request payload fields for task create/update.

    This base model centralizes field declarations and validation constraints
    common to both `TaskCreate` and `TaskUpdate` without prescribing defaults.
    Subclasses are responsible for applying operation-specific defaults and
    required-ness (e.g., `TaskCreate.name` required).

    Notes:
        - Enum and bounds validation live here so both subclasses stay in sync.
        - Outbound serialization uses enum string values (`use_enum_values=True`).
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    # Shared relational/context fields
    area_id: str | None = Field(default=None, description="Area ID the task belongs to")
    goal_id: str | None = Field(
        default=None,
        description=(
            "ID of the goal where the task should belong to (optional, "
            "can be found in our apps in the goal's settings)"
        ),
    )

    # Encrypted content fields (present in write payloads only)
    name: str | None = Field(default=None, description="Task name (gets encrypted client-side)")
    note: str | None = Field(
        default=None, description="Task note in Markdown (encrypted client-side)"
    )

    # State and prioritization
    status: TaskStatus | None = Field(default=None, description="Task status")
    motivation: TaskMotivation | None = Field(default=None, description="Task motivation level")
    eisenhower: int | None = Field(
        default=None,
        ge=MIN_EISENHOWER,
        le=MAX_EISENHOWER,
        description=f"Eisenhower matrix quadrant [{MIN_EISENHOWER}, {MAX_EISENHOWER}]",
    )
    priority: int | None = Field(
        default=None,
        ge=MIN_PRIORITY,
        le=MAX_PRIORITY,
        description=f"Task priority level [{MIN_PRIORITY}, {MAX_PRIORITY}]",
    )

    # Scheduling/completion timestamps
    scheduled_on: date | None = Field(
        default=None, description="Scheduled date (YYYY-MM-DD, date-only)"
    )
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp (ISO-8601)"
    )

    # Source metadata
    source: Source | None = Field(default=None, description="Task source information")


class TaskCreate(TaskPayload):
    """Request model for creating new tasks in LunaTask.

    Inherits shared fields and validation from `TaskPayload` and applies
    create-time defaults and requirements. Ensures `name` is provided and
    sets defaults for `status`, `priority`, and `motivation` when omitted.
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    # Field present in create payload only (not shared by update)
    estimate: int | None = Field(default=None, description="Estimated duration in minutes")

    @model_validator(mode="before")
    @classmethod
    def _apply_create_defaults_and_requirements(cls, data: object) -> object:
        """Enforce required name and set create-time defaults.

        - Require `name` to be provided and non-empty.
        - Default `status` to later, `priority` to 0, `motivation` to unknown.
        """
        if isinstance(data, dict):
            d = cast(dict[str, object], data)
            name = d.get("name")
            # Require that name is provided (may be empty string; API performs content validation)
            if name is None:
                raise ValueError("name is required")  # noqa: TRY003

            d.setdefault("status", TaskStatus.LATER)
            d.setdefault("priority", 0)
            d.setdefault("motivation", TaskMotivation.UNKNOWN)
            return d
        return data

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]


class TaskUpdate(TaskPayload):
    """Partial update payload for existing tasks.

    Inherits all shared request fields and constraints from `TaskPayload` with
    all attributes optional to support PATCH semantics. Outbound serialization
    relies on `model_dump(exclude_none=True)` at call sites to send only changed
    fields.
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]
