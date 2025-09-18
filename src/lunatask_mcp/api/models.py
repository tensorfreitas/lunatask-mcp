"""Data models for LunaTask API requests and responses.

This module defines Pydantic models and enums used to parse and validate
LunaTask API data. Request models use field constraints for numeric bounds
and `StrEnum` for string enums to generate clearer schemas and consistent
validation errors.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from datetime import date, datetime
from enum import StrEnum
from typing import cast

from pydantic import BaseModel, Field, computed_field, model_validator
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


class TaskPayload(BaseModel):
    """Shared request payload fields for task create/update.

    This base model centralizes field declarations and validation constraints
    common to both `TaskCreate` and `TaskUpdate`. Fields that need defaults
    for creation are overridden in `TaskCreate` with proper non-None defaults.

    Notes:
        - Enum and bounds validation live here so both subclasses stay in sync.
        - Outbound serialization uses enum string values (`use_enum_values=True`).
    """

    # Ensure outbound JSON uses enum string values and reject unsupported fields
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    # Shared relational/context fields
    goal_id: str | None = Field(
        default=None,
        description=(
            "ID of the goal where the task should belong to (optional, "
            "can be found in our apps in the goal's settings)"
        ),
    )

    # State and prioritization - kept as None for TaskUpdate's PATCH semantics
    # TaskCreate will override these with proper defaults
    status: TaskStatus | None = Field(default=None, description="Task status")
    estimate: int | None = Field(default=None, description="Estimated duration in minutes")
    priority: int | None = Field(
        default=None,
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
    # Optional encrypted content fields
    name: str | None = Field(default=None, description="Task name (gets encrypted client-side)")
    note: str | None = Field(
        default=None, description="Task note in Markdown (encrypted client-side)"
    )


class TaskSource(BaseModel):
    """Source metadata entry associated with a task."""

    source: str | None = Field(
        default=None,
        description="Identifier of the system where the task originated (e.g., 'github')",
    )
    source_id: str | None = Field(
        default=None,
        description="Identifier of the task within the external system",
    )


def _empty_task_sources() -> list[TaskSource]:
    """Return an empty list typed for TaskSource default factory."""

    return []


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
    status: TaskStatus = Field(default=TaskStatus.LATER, description="Task status")
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
    sources: list[TaskSource] = Field(
        default_factory=_empty_task_sources,
        description="Collection of source metadata entries associated with the task",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_sources(cls, data: object) -> object:
        """Normalize legacy source fields into the sources array format."""

        if not isinstance(data, MutableMapping):
            return data

        mapping_data = cast(MutableMapping[str, object], data)
        normalized: dict[str, object] = dict(mapping_data)

        if "sources" in normalized:
            normalized["sources"] = cls._normalize_sources_payload(normalized.get("sources"))
            normalized.pop("source", None)
            normalized.pop("source_id", None)
            return normalized

        source_value = cast(str | None, normalized.pop("source", None))
        source_id_value = cast(str | None, normalized.pop("source_id", None))

        if source_value is None and source_id_value is None:
            normalized["sources"] = []
            return normalized

        normalized["sources"] = [
            {
                "source": source_value,
                "source_id": source_id_value,
            }
        ]
        return normalized

    @staticmethod
    def _normalize_sources_payload(raw_sources: object) -> list[dict[str, str | None]]:
        """Convert arbitrary sources payloads into normalized dictionaries."""

        if isinstance(raw_sources, Mapping):
            mapping_entry = cast(Mapping[str, object], raw_sources)
            return [
                {
                    "source": cast(str | None, mapping_entry.get("source")),
                    "source_id": cast(str | None, mapping_entry.get("source_id")),
                }
            ]

        if isinstance(raw_sources, Sequence) and not isinstance(raw_sources, str | bytes):
            entries = cast(Sequence[Mapping[str, object]], raw_sources)
            return [
                {
                    "source": cast(str | None, entry.get("source")),
                    "source_id": cast(str | None, entry.get("source_id")),
                }
                for entry in entries
            ]

        return []

    @computed_field(return_type=str | None)
    @property
    def source(self) -> str | None:
        """Primary source identifier for backwards compatibility."""

        if not self.sources:
            return None
        return self.sources[0].source

    @computed_field(return_type=str | None)
    @property
    def source_id(self) -> str | None:
        """Primary source identifier from the first source entry."""

        if not self.sources:
            return None
        return self.sources[0].source_id

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

    area_id: str = Field(description="Area ID the task belongs to")
    source: str | None = Field(
        default=None,
        description=(
            "Identification of external system where the task originated (e.g., 'github')."
        ),
    )
    source_id: str | None = Field(
        default=None,
        description="Identifier of the record in the external system (e.g., issue ID)",
    )

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]


class TaskUpdate(TaskPayload):
    """Partial update payload for existing tasks.

    Keeps inheritance from ``TaskPayload`` while preserving PATCH semantics:
    - Override update-sensitive fields to be optional (``None`` by default) so that
      omitted values are not serialized and do not reset server state.
    - Call sites serialize with ``model_dump(exclude_none=True)``; with these
      overrides, missing fields remain ``None`` and are excluded.

    This approach avoids unintentional resets like ``status='later'`` or
    ``priority=0`` being sent when the caller didn't set those fields.
    """

    # Ensure outbound JSON uses enum string values
    model_config = ConfigDict(use_enum_values=True)

    # Required identifier for updates
    id: str = Field(description="The ID of the task (UUID)")

    # Optional relation for moves
    area_id: str | None = Field(default=None, description="Area ID the task belongs to")

    # Override update-sensitive fields from TaskPayload to support partial updates
    status: TaskStatus | None = Field(default=None, description="Task status")
    priority: int | None = Field(
        default=None,
        ge=MIN_PRIORITY,
        le=MAX_PRIORITY,
        description=f"Task priority level [{MIN_PRIORITY}, {MAX_PRIORITY}]",
    )

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]
