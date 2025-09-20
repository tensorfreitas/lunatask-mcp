"""Tests for LunaTask note models."""

import json
from datetime import UTC, date, datetime

from lunatask_mcp.api.models import NoteCreate, NoteResponse


def test_note_response_normalizes_legacy_source_fields() -> None:
    """Ensure legacy source fields are transformed into the sources list."""

    note = NoteResponse(
        id="note-123",
        notebook_id="notebook-001",
        date_on=None,
        source="evernote",
        source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
        created_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
        updated_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
        deleted_at=None,
    )

    assert len(note.sources) == 1
    source_entry = note.sources[0]
    assert source_entry.source == "evernote"
    assert source_entry.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"
    assert note.source == "evernote"
    assert note.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"


def test_note_response_computed_fields_return_none_when_no_sources() -> None:
    """Computed fields should return None when the payload lacks sources."""

    note = NoteResponse(
        id="note-789",
        notebook_id=None,
        date_on=None,
        created_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
        updated_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
        deleted_at=None,
    )

    assert note.sources == []
    assert note.source is None
    assert note.source_id is None


def test_note_create_serializes_date_on_to_iso_string() -> None:
    """NoteCreate should serialize date_on values to ISO-8601 strings."""

    note_create = NoteCreate(
        notebook_id="notebook-001",
        name="Sync planning notes",
        content="## Plan\n- item 1",
        date_on=date(2025, 9, 15),
        source="evernote",
        source_id="external-123",
    )

    payload = json.loads(note_create.model_dump_json(exclude_none=True))

    assert payload["notebook_id"] == "notebook-001"
    assert payload["name"] == "Sync planning notes"
    assert payload["content"] == "## Plan\n- item 1"
    assert payload["date_on"] == "2025-09-15"
    assert payload["source"] == "evernote"
    assert payload["source_id"] == "external-123"
