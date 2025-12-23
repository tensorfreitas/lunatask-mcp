"""Tests for LunaTaskClient.update_note()."""

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
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import NoteResponse, NoteUpdate
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, VALID_TOKEN


class TestLunaTaskClientUpdateNote:
    """Test suite for LunaTaskClient.update_note()."""

    @pytest.mark.asyncio
    async def test_update_note_success_all_fields(self, mocker: MockerFixture) -> None:
        """Client should deserialize wrapped note response on success with all fields."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_update = NoteUpdate(
            id="note-123",
            notebook_id="notebook-456",
            name="Updated weekly review",
            content="## Updated Notes\n- new item",
            date_on=date(2025, 9, 20),
        )

        mock_response: dict[str, Any] = {
            "note": {
                "id": "note-123",
                "notebook_id": "notebook-456",
                "date_on": "2025-09-20",
                "sources": [
                    {"source": "evernote", "source_id": "external-352f"},
                ],
                "created_at": "2025-09-10T10:39:25Z",
                "updated_at": "2025-09-20T14:22:10Z",
                "deleted_at": None,
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.update_note("note-123", note_update)

        assert isinstance(result, NoteResponse)
        assert result.id == "note-123"
        assert result.notebook_id == "notebook-456"
        assert result.date_on == date(2025, 9, 20)
        assert result.created_at == datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC)
        assert result.updated_at == datetime(2025, 9, 20, 14, 22, 10, tzinfo=UTC)

        mock_make_request.assert_called_once_with(
            "PUT",
            "notes/note-123",
            data={
                "id": "note-123",
                "notebook_id": "notebook-456",
                "name": "Updated weekly review",
                "content": "## Updated Notes\n- new item",
                "date_on": "2025-09-20",
            },
        )

    @pytest.mark.asyncio
    async def test_update_note_success_minimal_fields(self, mocker: MockerFixture) -> None:
        """Client should handle minimal update with only name field."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_update = NoteUpdate(
            id="note-123",
            name="Just update the name",
        )

        mock_response: dict[str, Any] = {
            "note": {
                "id": "note-123",
                "notebook_id": "notebook-456",
                "date_on": "2025-09-15",
                "sources": [],
                "created_at": "2025-09-10T10:39:25Z",
                "updated_at": "2025-09-20T14:22:10Z",
                "deleted_at": None,
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.update_note("note-123", note_update)

        assert isinstance(result, NoteResponse)
        assert result.id == "note-123"

        # Verify exclude_none=True excludes None fields from JSON
        mock_make_request.assert_called_once_with(
            "PUT",
            "notes/note-123",
            data={
                "id": "note-123",
                "name": "Just update the name",
            },
        )

    @pytest.mark.asyncio
    async def test_update_note_success_date_serialization(self, mocker: MockerFixture) -> None:
        """Client should serialize date_on to ISO-8601 format."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_update = NoteUpdate(
            id="note-123",
            date_on=date(2025, 12, 25),
        )

        mock_response: dict[str, Any] = {
            "note": {
                "id": "note-123",
                "notebook_id": None,
                "date_on": "2025-12-25",
                "sources": [],
                "created_at": "2025-09-10T10:39:25Z",
                "updated_at": "2025-09-20T14:22:10Z",
                "deleted_at": None,
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.update_note("note-123", note_update)

        assert result.date_on == date(2025, 12, 25)

        # Verify date is serialized as ISO string
        mock_make_request.assert_called_once_with(
            "PUT",
            "notes/note-123",
            data={
                "id": "note-123",
                "date_on": "2025-12-25",
            },
        )

    @pytest.mark.asyncio
    async def test_update_note_not_found_error(self, mocker: MockerFixture) -> None:
        """Propagate not found errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-nonexistent", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError("Note not found"),
        )

        with pytest.raises(LunaTaskNotFoundError, match="Note not found"):
            await client.update_note("note-nonexistent", note_update)

    @pytest.mark.asyncio
    async def test_update_note_validation_error(self, mocker: MockerFixture) -> None:
        """Propagate validation errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskValidationError("Entity validation failed"),
        )

        with pytest.raises(LunaTaskValidationError, match="Entity validation failed"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_authentication_error(self, mocker: MockerFixture) -> None:
        """Propagate authentication errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Propagate rate limit errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_server_error(self, mocker: MockerFixture) -> None:
        """Propagate server errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal error", status_code=500),
        )

        with pytest.raises(LunaTaskServerError, match="Internal error"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_service_unavailable_error(self, mocker: MockerFixture) -> None:
        """Propagate service unavailable errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServiceUnavailableError("Maintenance"),
        )

        with pytest.raises(LunaTaskServiceUnavailableError, match="Maintenance"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_timeout_error(self, mocker: MockerFixture) -> None:
        """Propagate timeout errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Timeout"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_network_error(self, mocker: MockerFixture) -> None:
        """Propagate network errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network error"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network error"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_api_error_generic(self, mocker: MockerFixture) -> None:
        """Propagate generic API errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAPIError("Generic API error"),
        )

        with pytest.raises(LunaTaskAPIError, match="Generic API error"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_parse_error_missing_note_key(self, mocker: MockerFixture) -> None:
        """Missing wrapped note should raise a LunaTaskAPIError parse error."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        mocker.patch.object(client, "make_request", return_value={"unexpected": {}})

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.update_note("note-123", note_update)

    @pytest.mark.asyncio
    async def test_update_note_parse_error_malformed_response(self, mocker: MockerFixture) -> None:
        """Malformed response should raise a LunaTaskAPIError parse error."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_update = NoteUpdate(id="note-123", name="Update")

        # Mock response with note key but invalid data structure
        mocker.patch.object(
            client,
            "make_request",
            return_value={"note": {"id": "note-123", "created_at": "invalid-date-format"}},
        )

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.update_note("note-123", note_update)
