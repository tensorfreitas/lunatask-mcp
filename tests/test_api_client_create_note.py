"""Tests for LunaTaskClient.create_note()."""

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
from lunatask_mcp.api.models import NoteCreate, NoteResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, VALID_TOKEN


class TestLunaTaskClientCreateNote:
    """Test suite for LunaTaskClient.create_note()."""

    @pytest.mark.asyncio
    async def test_create_note_success_all_fields(self, mocker: MockerFixture) -> None:
        """Client should deserialize wrapped note response on success."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_payload = NoteCreate(
            notebook_id="notebook-123",
            name="Weekly review",
            content="## Notes\n- item",
            date_on=date(2025, 9, 15),
            source="evernote",
            source_id="external-352f",
        )

        mock_response: dict[str, Any] = {
            "note": {
                "id": "note-123",
                "notebook_id": "notebook-123",
                "date_on": "2025-09-15",
                "sources": [
                    {"source": "evernote", "source_id": "external-352f"},
                ],
                "created_at": "2025-09-10T10:39:25Z",
                "updated_at": "2025-09-10T10:39:25Z",
                "deleted_at": None,
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.create_note(note_payload)

        assert isinstance(result, NoteResponse)
        assert result.id == "note-123"
        assert result.notebook_id == "notebook-123"
        assert result.date_on == date(2025, 9, 15)
        assert result.source == "evernote"
        assert result.source_id == "external-352f"
        assert result.created_at == datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC)

        mock_make_request.assert_called_once_with(
            "POST",
            "notes",
            data={
                "notebook_id": "notebook-123",
                "name": "Weekly review",
                "content": "## Notes\n- item",
                "date_on": "2025-09-15",
                "source": "evernote",
                "source_id": "external-352f",
            },
        )

    @pytest.mark.asyncio
    async def test_create_note_duplicate_returns_none(self, mocker: MockerFixture) -> None:
        """204 duplicates should return None to signal no new note was created."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mock_make_request = mocker.patch.object(client, "make_request", return_value={})

        result = await client.create_note(note_payload)

        assert result is None
        mock_make_request.assert_called_once_with("POST", "notes", data={"name": "Weekly review"})

    @pytest.mark.asyncio
    async def test_create_note_parse_error_missing_note_key(self, mocker: MockerFixture) -> None:
        """Missing wrapped note should raise a LunaTaskAPIError parse error."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(client, "make_request", return_value={"unexpected": {}})

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_validation_error(self, mocker: MockerFixture) -> None:
        """Propagate validation errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskValidationError("Entity validation failed"),
        )

        with pytest.raises(LunaTaskValidationError, match="Entity validation failed"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_subscription_required(self, mocker: MockerFixture) -> None:
        """Propagate subscription required errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskSubscriptionRequiredError("Upgrade required"),
        )

        with pytest.raises(LunaTaskSubscriptionRequiredError, match="Upgrade required"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_authentication_error(self, mocker: MockerFixture) -> None:
        """Propagate authentication errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Propagate rate limit errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_server_error(self, mocker: MockerFixture) -> None:
        """Propagate server errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal error", status_code=500),
        )

        with pytest.raises(LunaTaskServerError, match="Internal error"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_service_unavailable_error(self, mocker: MockerFixture) -> None:
        """Propagate service unavailable errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServiceUnavailableError("Maintenance"),
        )

        with pytest.raises(LunaTaskServiceUnavailableError, match="Maintenance"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_timeout_error(self, mocker: MockerFixture) -> None:
        """Propagate timeout errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Timeout"):
            await client.create_note(note_payload)

    @pytest.mark.asyncio
    async def test_create_note_network_error(self, mocker: MockerFixture) -> None:
        """Propagate network errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Weekly review")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network error"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network error"):
            await client.create_note(note_payload)
