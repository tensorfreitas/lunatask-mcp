"""Data models for LunaTask API responses.

This module contains Pydantic models for parsing and validating
LunaTask API responses, particularly focusing on task data.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source information for task origin."""

    type: str = Field(..., description="Type of source (e.g., 'email', 'web', 'manual')")
    value: str | None = Field(None, description="Source value or identifier")


class TaskResponse(BaseModel):
    """Response model for LunaTask task data.

    This model represents a task as returned by the LunaTask API.
    Note: Encrypted fields (name, notes) are not included due to E2E encryption.
    """

    id: str = Field(..., description="Unique task identifier")
    area_id: str | None = Field(None, description="Area ID the task belongs to")
    status: str = Field(..., description="Task status (e.g., 'open', 'completed')")
    priority: int | None = Field(None, description="Task priority level")
    due_date: datetime | None = Field(None, description="Task due date")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")
    source: Source | None = Field(None, description="Task source information")
    tags: list[str] = Field(default_factory=list, description="Task tags")

    # Note: 'name' and 'notes' fields are not included due to E2E encryption
    # and are not returned in GET responses from the LunaTask API
