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

    # Optional persisted custom fields that may be returned
    email: str | None = Field(default=None, description="Person's email address")
    birthday: date | None = Field(default=None, description="Person's birthday")
    phone: str | None = Field(default=None, description="Person's phone number")

    def __init__(self, **data: object) -> None:
        """Pydantic-compatible initializer with permissive typing for tools/tests."""
        super().__init__(**data)  # type: ignore[arg-type]
