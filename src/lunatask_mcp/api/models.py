"""Data models for LunaTask API responses.

This module contains Pydantic models for parsing and validating
LunaTask API responses, particularly focusing on task data.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Enums for request validation
TaskStatus = Literal["later", "next", "started", "waiting", "completed"]
TaskMotivation = Literal["must", "should", "want", "unknown"]

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

    id: str = Field(..., description="Unique task identifier")
    area_id: str | None = Field(None, description="Area ID the task belongs to")
    status: str = Field(..., description="Task status (e.g., 'open', 'completed')")
    priority: int | None = Field(None, description="Task priority level")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")
    source: Source | None = Field(None, description="Task source information")
    goal_id: str | None = Field(None, description="Goal ID the task belongs to")
    estimate: int | None = Field(None, description="Estimated duration in minutes")
    motivation: str | None = Field(
        None, description="Task motivation level (must, should, want, unknown)"
    )
    eisenhower: int | None = Field(None, description="Eisenhower matrix quadrant (0-4)")
    previous_status: str | None = Field(None, description="Previous task status")
    progress: int | None = Field(None, description="Task completion percentage")
    scheduled_on: date | None = Field(
        None, description="Date when task is scheduled (YYYY-MM-DD format, date-only)"
    )
    completed_at: datetime | None = Field(None, description="Task completion timestamp")

    # Note: 'name' and 'note' fields are not included due to E2E encryption
    # and are not returned in GET responses from the LunaTask API


class TaskCreate(BaseModel):
    """Request model for creating new tasks in LunaTask.

    This model represents the data required to create a new task via POST /v1/tasks.
    Note: name and note fields CAN be included in POST requests (they get encrypted client-side).
    """

    name: str = Field(..., description="Task name (required, gets encrypted client-side)")
    note: str | None = Field(
        default=None, description="Task note (optional, gets encrypted client-side)"
    )
    area_id: str | None = Field(default=None, description="Area ID the task belongs to")
    status: TaskStatus = Field(default="later", description="Task status (default: 'later')")
    priority: int = Field(default=0, description="Task priority level (default: 0)")
    scheduled_on: date | None = Field(
        default=None, description="Date when task is scheduled (YYYY-MM-DD format, date-only)"
    )
    source: Source | None = Field(default=None, description="Task source information")
    motivation: TaskMotivation = Field(
        default="unknown", description="Task motivation (default: 'unknown')"
    )
    eisenhower: int | None = Field(default=None, description="Eisenhower matrix quadrant (0-4)")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Validate priority is within bounds [-2, 2]."""
        if v < MIN_PRIORITY or v > MAX_PRIORITY:
            msg = f"Priority must be between {MIN_PRIORITY} and {MAX_PRIORITY}"
            raise ValueError(msg)
        return v

    @field_validator("eisenhower")
    @classmethod
    def validate_eisenhower(cls, v: int | None) -> int | None:
        """Validate eisenhower is within bounds [0, 4]."""
        if v is not None and (v < MIN_EISENHOWER or v > MAX_EISENHOWER):
            msg = f"Eisenhower must be between {MIN_EISENHOWER} and {MAX_EISENHOWER}"
            raise ValueError(msg)
        return v


class TaskUpdate(BaseModel):
    """Request model for updating existing tasks in LunaTask.

    This model supports partial updates via PATCH /v1/tasks/{id}.
    All fields are optional to allow selective updates.
    Note: name and note fields CAN be included in PATCH requests (they get encrypted client-side).
    """

    name: str | None = Field(default=None, description="Task name (gets encrypted client-side)")
    note: str | None = Field(default=None, description="Task note (gets encrypted client-side)")
    area_id: str | None = Field(default=None, description="Area ID the task belongs to")
    status: TaskStatus | None = Field(default=None, description="Task status")
    priority: int | None = Field(default=None, description="Task priority level")
    scheduled_on: date | None = Field(
        default=None, description="Date when task is scheduled (YYYY-MM-DD format, date-only)"
    )
    source: Source | None = Field(default=None, description="Task source information")
    motivation: TaskMotivation | None = Field(default=None, description="Task motivation")
    eisenhower: int | None = Field(default=None, description="Eisenhower matrix quadrant (0-4)")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int | None) -> int | None:
        """Validate priority is within bounds [-2, 2]."""
        if v is not None and (v < MIN_PRIORITY or v > MAX_PRIORITY):
            msg = f"Priority must be between {MIN_PRIORITY} and {MAX_PRIORITY}"
            raise ValueError(msg)
        return v

    @field_validator("eisenhower")
    @classmethod
    def validate_eisenhower(cls, v: int | None) -> int | None:
        """Validate eisenhower is within bounds [0, 4]."""
        if v is not None and (v < MIN_EISENHOWER or v > MAX_EISENHOWER):
            msg = f"Eisenhower must be between {MIN_EISENHOWER} and {MAX_EISENHOWER}"
            raise ValueError(msg)
        return v
