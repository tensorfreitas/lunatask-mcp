"""Data models for LunaTask People API requests and responses.

This module defines Pydantic models and enums for people/contact management
in LunaTask. Follows the same patterns as the main models module with
StrEnum for relationship strength and BaseSourceResponse for consistency.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from .models import BaseSourceResponse


class PersonRelationshipStrength(StrEnum):
    """Relationship strength values accepted by LunaTask person creation."""

    FAMILY = "family"
    INTIMATE_FRIENDS = "intimate-friends"
    CLOSE_FRIENDS = "close-friends"
    CASUAL_FRIENDS = "casual-friends"
    ACQUAINTANCES = "acquaintances"
    BUSINESS_CONTACTS = "business-contacts"
    ALMOST_STRANGERS = "almost-strangers"


class PersonCreate(BaseModel):
    """Request model for creating new people in LunaTask.

    Follows the LunaTask people API specification with required name fields
    and optional relationship metadata and custom fields.
    """

    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    first_name: str = Field(description="Person's first name")
    last_name: str = Field(description="Person's last name")
    relationship_strength: PersonRelationshipStrength = Field(
        default=PersonRelationshipStrength.CASUAL_FRIENDS,
        description="Relationship strength level",
    )
    source: str | None = Field(
        default=None,
        description="Identifier of external system where the person originated",
    )
    source_id: str | None = Field(
        default=None,
        description="Identifier of the person record in the external system",
    )
    email: str | None = Field(default=None, description="Person's email address")
    birthday: date | None = Field(default=None, description="Person's birthday (ISO-8601 date)")
    phone: str | None = Field(default=None, description="Person's phone number")

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]


class PersonResponse(BaseSourceResponse):
    """Response model for LunaTask person data.

    The LunaTask API returns created people wrapped inside `{"person": {...}}`.
    Inherits source normalization logic from BaseSourceResponse.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(min_length=1, description="Unique identifier of the person (UUID)")
    relationship_strength: PersonRelationshipStrength = Field(
        description="Relationship strength level"
    )
    created_at: datetime = Field(description="Timestamp when the person was created")
    updated_at: datetime = Field(description="Timestamp when the person was last updated")
    deleted_at: datetime | None = Field(
        default=None, description="Timestamp when the person was deleted"
    )

    # Optional persisted custom fields that may be returned
    email: str | None = Field(default=None, description="Person's email address")
    birthday: date | None = Field(default=None, description="Person's birthday")
    phone: str | None = Field(default=None, description="Person's phone number")

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]


class PersonTimelineNoteCreate(BaseModel):
    """Request model for creating a person timeline note in LunaTask.

    The LunaTask API requires a person identifier, with optional content and
    date information. Fields set to ``None`` are excluded from the serialized
    payload to keep requests minimal.
    """

    model_config = ConfigDict(extra="forbid")

    person_id: str = Field(min_length=1, description="Identifier of the person the note belongs to")
    content: str | None = Field(
        default=None,
        description="Markdown content of the timeline note",
    )
    date_on: date | None = Field(
        default=None,
        description="Optional ISO-8601 date string for when the note occurred",
    )

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]


class PersonTimelineNoteResponse(BaseModel):
    """Response model for person timeline note creation.

    The LunaTask API wraps created notes inside ``{"person_timeline_note": {...}}``
    payloads. This model captures the stable fields the client depends on while
    ignoring any additional attributes sent by the API for forward compatibility.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, description="Unique identifier for the timeline note")
    date_on: date = Field(description="Date associated with the timeline note")
    created_at: datetime = Field(description="Timestamp when the note was created")
    updated_at: datetime = Field(description="Timestamp when the note was last updated")

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]
