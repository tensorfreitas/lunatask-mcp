"""Tests for person timeline note Pydantic models."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from lunatask_mcp.api.models_people import (
    PersonTimelineNoteCreate,
    PersonTimelineNoteResponse,
)


def test_person_timeline_note_create_serializes_fields() -> None:
    """PersonTimelineNoteCreate should serialize optional fields to primitives."""

    payload = PersonTimelineNoteCreate(
        person_id="person-123",
        content="## Memory\n- Detail",
        date_on=date(2025, 9, 20),
    )

    serialized = json.loads(payload.model_dump_json(exclude_none=True))

    assert serialized == {
        "person_id": "person-123",
        "content": "## Memory\n- Detail",
        "date_on": "2025-09-20",
    }


def test_person_timeline_note_create_drops_none_fields() -> None:
    """None values should be omitted when serializing the create payload."""

    payload = PersonTimelineNoteCreate(person_id="person-456", content=None, date_on=None)

    serialized = json.loads(payload.model_dump_json(exclude_none=True))

    assert serialized == {"person_id": "person-456"}


def test_person_timeline_note_create_rejects_unknown_fields() -> None:
    """Unexpected fields should raise a validation error."""

    with pytest.raises(ValidationError):
        PersonTimelineNoteCreate(person_id="person-789", content="Note", unexpected="value")


def test_person_timeline_note_response_parses_dates_and_timestamps() -> None:
    """Wrapped response data should parse ISO dates and timestamps."""

    response = PersonTimelineNoteResponse(
        id="note-123",
        date_on="2025-09-21",
        created_at="2025-09-21T15:39:25Z",
        updated_at="2025-09-22T10:15:00Z",
    )

    assert response.id == "note-123"
    assert response.date_on == date(2025, 9, 21)
    assert response.created_at == datetime(2025, 9, 21, 15, 39, 25, tzinfo=UTC)
    assert response.updated_at == datetime(2025, 9, 22, 10, 15, tzinfo=UTC)


def test_person_timeline_note_response_ignores_unknown_fields() -> None:
    """Extra response keys from LunaTask should be ignored for forward compatibility."""

    response = PersonTimelineNoteResponse(
        id="note-456",
        date_on="2025-09-21",
        created_at="2025-09-21T15:39:25Z",
        updated_at="2025-09-22T10:15:00Z",
        extra_field="ignored",
    )

    assert response.id == "note-456"
    assert not hasattr(response, "extra_field")
