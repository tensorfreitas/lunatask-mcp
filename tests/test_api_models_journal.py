"""Tests for LunaTask journal entry models."""

import json
from datetime import UTC, date, datetime

from lunatask_mcp.api.models import JournalEntryCreate, JournalEntryResponse


def test_journal_entry_create_serializes_date_on_to_iso_string() -> None:
    """`JournalEntryCreate` should serialize date fields to ISO-8601 strings."""

    journal_entry = JournalEntryCreate(
        date_on=date(2025, 9, 21),
        name="Daily reflection",
        content="## Highlights\n- Wrapped up MCP tool plan",
    )

    payload = json.loads(journal_entry.model_dump_json(exclude_none=True))

    assert payload["date_on"] == "2025-09-21"
    assert payload["name"] == "Daily reflection"
    assert payload["content"] == "## Highlights\n- Wrapped up MCP tool plan"


def test_journal_entry_create_with_required_fields_serializes_minimal_payload() -> None:
    """Minimal payload should include only the required date_on field."""

    journal_entry = JournalEntryCreate(date_on=date(2025, 9, 21))

    payload = json.loads(journal_entry.model_dump_json(exclude_none=True))

    assert payload == {"date_on": "2025-09-21"}


def test_journal_entry_response_parses_datetimes_from_unwrapped_payload() -> None:
    """`JournalEntryResponse` should parse datetime fields from unwrapped payloads."""

    response_payload = {
        "id": "journal-123",
        "date_on": "2025-09-20",
        "created_at": "2025-09-20T10:39:25Z",
        "updated_at": "2025-09-20T11:10:05Z",
    }

    journal_entry = JournalEntryResponse.model_validate(response_payload)

    assert journal_entry.id == "journal-123"
    assert journal_entry.date_on == date(2025, 9, 20)
    assert journal_entry.created_at == datetime(2025, 9, 20, 10, 39, 25, tzinfo=UTC)
    assert journal_entry.updated_at == datetime(2025, 9, 20, 11, 10, 5, tzinfo=UTC)


def test_journal_entry_response_does_not_expose_encrypted_fields() -> None:
    """Responses should not expose encrypted fields like `name` or `content`."""

    journal_entry = JournalEntryResponse(
        id="journal-456",
        date_on=date(2025, 9, 19),
        created_at=datetime(2025, 9, 19, 6, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 9, 19, 6, 0, 0, tzinfo=UTC),
    )

    assert not hasattr(journal_entry, "name")
    assert not hasattr(journal_entry, "content")


def test_journal_entry_response_accepts_minimal_unwrapped_payload() -> None:
    """Minimal unwrapped payloads should parse when only required fields are present."""

    journal_entry = JournalEntryResponse.model_validate(
        {
            "id": "journal-789",
            "date_on": "2025-09-18",
            "created_at": "2025-09-18T09:00:00Z",
            "updated_at": "2025-09-18T09:15:00Z",
        }
    )

    assert journal_entry.id == "journal-789"
    assert journal_entry.date_on == date(2025, 9, 18)
