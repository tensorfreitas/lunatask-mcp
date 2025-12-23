"""Tests for LunaTaskClient.delete_note()."""

from __future__ import annotations

import urllib.parse
from datetime import UTC, datetime
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
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import NoteResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, INVALID_TOKEN, VALID_TOKEN


class TestLunaTaskClientDeleteNote:
    """Test suite for LunaTaskClient.delete_note() method."""

    @pytest.mark.asyncio
    async def test_delete_note_success_200_with_wrapped_response(
        self, mocker: MockerFixture
    ) -> None:
        """Test successful note deletion with 200 response and wrapped note data."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "92a960ba-54f5-42db-bd0c-596dced80644"

        # Mock 200 response with wrapped note data including deleted_at
        mock_response: dict[str, Any] = {
            "note": {
                "id": "92a960ba-54f5-42db-bd0c-596dced80644",
                "notebook_id": "notebook-123",
                "date_on": "2025-12-23",
                "sources": [],
                "created_at": "2025-12-23T17:15:12.941Z",
                "deleted_at": "2025-12-23T17:15:47.398Z",
                "updated_at": "2025-12-23T17:15:47.398Z",
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_note(note_id)

        assert isinstance(result, NoteResponse)
        assert result.id == "92a960ba-54f5-42db-bd0c-596dced80644"
        assert result.notebook_id == "notebook-123"
        assert result.deleted_at == datetime(2025, 12, 23, 17, 15, 47, 398000, tzinfo=UTC)
        assert result.created_at == datetime(2025, 12, 23, 17, 15, 12, 941000, tzinfo=UTC)
        assert result.updated_at == datetime(2025, 12, 23, 17, 15, 47, 398000, tzinfo=UTC)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskNotFoundError on 404 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "nonexistent-note"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError("Note not found"),
        )

        with pytest.raises(LunaTaskNotFoundError, match="Note not found"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        note_id = "note-123"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "note-rate-limited"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_server_error_500(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "note-server-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_timeout_error(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "note-timeout"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_network_error(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskNetworkError on network error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "note-network-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network error"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network error"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_empty_string_id_validation(self, mocker: MockerFixture) -> None:
        """Test delete_note with empty note_id raises validation error before API call."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = ""

        # Mock should NOT be called due to early validation
        mock_request = mocker.patch.object(client, "make_request")

        with pytest.raises(LunaTaskValidationError, match="Note ID cannot be empty"):
            await client.delete_note(note_id)

        # Ensure API was NOT called due to validation failure
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_note_whitespace_id_validation(self, mocker: MockerFixture) -> None:
        """Test delete_note with whitespace note_id raises validation error before API call."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "   \t\n  "

        # Mock should NOT be called due to early validation
        mock_request = mocker.patch.object(client, "make_request")

        with pytest.raises(LunaTaskValidationError, match="Note ID cannot be empty"):
            await client.delete_note(note_id)

        # Ensure API was NOT called due to validation failure
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_note_url_encoding_special_characters(self, mocker: MockerFixture) -> None:
        """Test delete_note properly URL-encodes special characters in note_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        # Note ID with special characters that need URL encoding
        note_id = "note-with/special@chars&params=value"
        expected_encoded = urllib.parse.quote(note_id, safe="")

        mock_response: dict[str, Any] = {
            "note": {
                "id": note_id,
                "notebook_id": None,
                "date_on": None,
                "sources": [],
                "created_at": "2025-12-23T17:15:12.941Z",
                "deleted_at": "2025-12-23T17:15:47.398Z",
                "updated_at": "2025-12-23T17:15:47.398Z",
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_note(note_id)

        assert isinstance(result, NoteResponse)
        assert result.id == note_id

        # Verify the URL was properly encoded
        mock_request.assert_called_once_with("DELETE", f"notes/{expected_encoded}")

    @pytest.mark.asyncio
    async def test_delete_note_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test delete_note applies rate limiting through make_request delegation."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "rate-limited-delete-note"

        mock_response: dict[str, Any] = {
            "note": {
                "id": note_id,
                "notebook_id": None,
                "date_on": None,
                "sources": [],
                "created_at": "2025-12-23T17:15:12.941Z",
                "deleted_at": "2025-12-23T17:15:47.398Z",
                "updated_at": "2025-12-23T17:15:47.398Z",
            }
        }

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_note(note_id)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")
        assert isinstance(result, NoteResponse)

    @pytest.mark.asyncio
    async def test_delete_note_non_idempotent_behavior(self, mocker: MockerFixture) -> None:
        """Test delete_note non-idempotent behavior - second delete returns 404."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "note-already-deleted"

        # First call succeeds (note exists and gets deleted)
        mock_response: dict[str, Any] = {
            "note": {
                "id": note_id,
                "notebook_id": None,
                "date_on": None,
                "sources": [],
                "created_at": "2025-12-23T17:15:12.941Z",
                "deleted_at": "2025-12-23T17:15:47.398Z",
                "updated_at": "2025-12-23T17:15:47.398Z",
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_note(note_id)
        assert isinstance(result, NoteResponse)
        assert result.deleted_at is not None

        # Second call fails (note no longer exists)
        mock_request.side_effect = LunaTaskNotFoundError("Note not found")

        with pytest.raises(LunaTaskNotFoundError):
            await client.delete_note(note_id)

    @pytest.mark.asyncio
    async def test_delete_note_parse_error_missing_note_key(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskAPIError when response is missing 'note' key."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "note-parse-error"

        # Mock response without the expected 'note' wrapper
        mock_response = {"unexpected": {"id": note_id}}

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")

    @pytest.mark.asyncio
    async def test_delete_note_parse_error_malformed_note_data(self, mocker: MockerFixture) -> None:
        """Test delete_note raises LunaTaskAPIError when note data is malformed."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        note_id = "note-malformed-data"

        # Mock response with invalid note data (missing required fields)
        mock_response: dict[str, Any] = {
            "note": {
                "id": note_id,
                # Missing required fields like created_at, updated_at, etc.
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.delete_note(note_id)

        mock_request.assert_called_once_with("DELETE", f"notes/{note_id}")
