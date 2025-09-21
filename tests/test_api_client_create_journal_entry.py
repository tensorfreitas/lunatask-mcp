"""Tests for LunaTaskClient.create_journal_entry()."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNetworkError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import JournalEntryCreate, JournalEntryResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, VALID_TOKEN


class TestLunaTaskClientCreateJournalEntry:
    """Test suite for LunaTaskClient.create_journal_entry()."""

    @pytest.mark.asyncio
    async def test_create_journal_entry_success(self, mocker: MockerFixture) -> None:
        """Client should call POST /journal_entries and deserialize wrapped response."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        create_payload = JournalEntryCreate(
            date_on=date(2025, 9, 20),
            name="Day review",
            content="Gratitude list",
        )

        mock_response: dict[str, Any] = {
            "journal_entry": {
                "id": "journal-123",
                "date_on": "2025-09-20",
                "created_at": "2025-09-20T07:30:00Z",
                "updated_at": "2025-09-20T07:30:00Z",
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.create_journal_entry(create_payload)

        assert isinstance(result, JournalEntryResponse)
        assert result.id == "journal-123"
        assert result.date_on == date(2025, 9, 20)
        assert result.created_at == datetime(2025, 9, 20, 7, 30, tzinfo=UTC)
        assert result.updated_at == datetime(2025, 9, 20, 7, 30, tzinfo=UTC)

        mock_make_request.assert_called_once_with(
            "POST",
            "journal_entries",
            data={
                "date_on": "2025-09-20",
                "name": "Day review",
                "content": "Gratitude list",
            },
        )

    @pytest.mark.asyncio
    async def test_create_journal_entry_missing_key_parse_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Missing journal_entry wrapper should raise a parse error."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(client, "make_request", return_value={"unexpected": {}})

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_validation_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate validation errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskValidationError("Entity validation failed"),
        )

        with pytest.raises(LunaTaskValidationError, match="Entity validation failed"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_authentication_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate authentication errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_subscription_required(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate subscription required errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskSubscriptionRequiredError("Upgrade required"),
        )

        with pytest.raises(LunaTaskSubscriptionRequiredError, match="Upgrade required"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_rate_limit_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate rate limit errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_server_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate server errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal error", status_code=500),
        )

        with pytest.raises(LunaTaskServerError, match="Internal error"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_service_unavailable_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate service unavailable errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServiceUnavailableError("Maintenance"),
        )

        with pytest.raises(LunaTaskServiceUnavailableError, match="Maintenance"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_timeout_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate timeout errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Timeout"):
            await client.create_journal_entry(create_payload)

    @pytest.mark.asyncio
    async def test_create_journal_entry_network_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Propagate network errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        create_payload = JournalEntryCreate(date_on=date(2025, 9, 20))

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network error"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network error"):
            await client.create_journal_entry(create_payload)
