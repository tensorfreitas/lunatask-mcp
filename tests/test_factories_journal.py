"""Tests for journal entry factories used in test suite."""

from __future__ import annotations

from datetime import UTC, date, datetime

from lunatask_mcp.api.models import JournalEntryResponse
from tests.factories import create_journal_entry_response


class TestCreateJournalEntryResponse:
    """Unit tests for create_journal_entry_response factory."""

    def test_returns_default_journal_entry_response(self) -> None:
        """Factory should produce a JournalEntryResponse with default values."""

        result = create_journal_entry_response()

        assert isinstance(result, JournalEntryResponse)
        assert result.id == "journal-entry-1"
        assert result.date_on == date(2025, 9, 20)
        assert result.created_at == datetime(2025, 9, 20, 7, 30, tzinfo=UTC)
        assert result.updated_at == datetime(2025, 9, 20, 7, 35, tzinfo=UTC)

    def test_supports_custom_field_overrides(self) -> None:
        """Factory should honor provided field overrides."""

        created_at = datetime(2025, 9, 19, 6, 0, tzinfo=UTC)
        updated_at = datetime(2025, 9, 19, 6, 5, tzinfo=UTC)

        result = create_journal_entry_response(
            entry_id="journal-entry-99",
            date_on=date(2025, 9, 19),
            created_at=created_at,
            updated_at=updated_at,
        )

        assert result.id == "journal-entry-99"
        assert result.date_on == date(2025, 9, 19)
        assert result.created_at is created_at
        assert result.updated_at is updated_at
