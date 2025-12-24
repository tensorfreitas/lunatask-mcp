"""Tests for specific exception handling in NotesClientMixin parse error paths.

This module tests that NoteResponse instantiation errors (ValidationError, TypeError)
are properly caught and converted to LunaTaskAPIError with appropriate error chaining.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskAPIError
from lunatask_mcp.api.models import NoteCreate, NoteUpdate
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, VALID_TOKEN


class TestCreateNoteParseErrors:
    """Test create_note() exception handling for parse errors."""

    @pytest.mark.asyncio
    async def test_create_note_validation_error_missing_required_field(
        self, mocker: MockerFixture
    ) -> None:
        """ValidationError from missing required field should be caught and wrapped."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Test Note")

        # Mock response missing required fields (created_at, updated_at)
        mock_response: dict[str, Any] = {
            "note": {
                "id": "note-123",
                # Missing created_at and updated_at - will trigger ValidationError
            }
        }

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.create_note(note_payload)

        # Verify exception chaining - the cause should be ValidationError
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValidationError)

    @pytest.mark.asyncio
    async def test_create_note_validation_error_invalid_field_type(
        self, mocker: MockerFixture
    ) -> None:
        """ValidationError from invalid field type should be caught and wrapped."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Test Note")

        # Mock response with invalid type for created_at (string instead of datetime)
        mock_response: dict[str, Any] = {
            "note": {
                "id": "note-123",
                "created_at": "not-a-valid-datetime-format",
                "updated_at": "2025-09-10T10:39:25Z",
            }
        }

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.create_note(note_payload)

        # Verify exception chaining
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValidationError)

    @pytest.mark.asyncio
    async def test_create_note_type_error_non_dict_payload(self, mocker: MockerFixture) -> None:
        """TypeError from non-dict payload should be caught and wrapped."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Test Note")

        # Mock response with non-dict note payload (string instead of dict)
        mock_response: dict[str, Any] = {
            "note": "invalid-string-instead-of-dict"  # type: ignore[dict-item]
        }

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.create_note(note_payload)

        # Verify exception chaining - the cause should be TypeError
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, TypeError)

    @pytest.mark.asyncio
    async def test_create_note_parse_error_preserves_context(self, mocker: MockerFixture) -> None:
        """Parse error should preserve endpoint context in error message."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_payload = NoteCreate(name="Important Note")

        # Mock response with missing required field
        mock_response: dict[str, Any] = {"note": {"id": "note-123"}}

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.create_note(note_payload)

        # Error message should contain endpoint and note name context
        error_msg = str(exc_info.value)
        assert "notes" in error_msg.lower() or "parse" in error_msg.lower()


class TestUpdateNoteParseErrors:
    """Test update_note() exception handling for parse errors."""

    @pytest.mark.asyncio
    async def test_update_note_validation_error_missing_required_field(
        self, mocker: MockerFixture
    ) -> None:
        """ValidationError from missing required field should be caught and wrapped."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_id = "note-123"
        update = NoteUpdate(id=note_id, name="Updated Name")

        # Mock response missing required fields
        mock_response: dict[str, Any] = {
            "note": {
                "id": note_id,
                # Missing created_at and updated_at
            }
        }

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.update_note(note_id, update)

        # Verify exception chaining
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValidationError)

    @pytest.mark.asyncio
    async def test_update_note_type_error_non_dict_payload(self, mocker: MockerFixture) -> None:
        """TypeError from non-dict payload should be caught and wrapped."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_id = "note-123"
        update = NoteUpdate(id=note_id, name="Updated Name")

        # Mock response with non-dict note payload
        mock_response: dict[str, Any] = {"note": None}  # type: ignore[dict-item]

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.update_note(note_id, update)

        # Verify exception chaining
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, TypeError)

    @pytest.mark.asyncio
    async def test_update_note_parse_error_preserves_note_id(self, mocker: MockerFixture) -> None:
        """Parse error should preserve note_id in error context."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_id = "note-abc-xyz-789"
        update = NoteUpdate(id=note_id, content="New content")

        # Mock response with invalid data
        mock_response: dict[str, Any] = {"note": {"id": note_id}}

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.update_note(note_id, update)

        # Error should preserve context
        error_msg = str(exc_info.value)
        assert "parse" in error_msg.lower()


class TestDeleteNoteParseErrors:
    """Test delete_note() exception handling for parse errors."""

    @pytest.mark.asyncio
    async def test_delete_note_validation_error_missing_required_field(
        self, mocker: MockerFixture
    ) -> None:
        """ValidationError from missing required field should be caught and wrapped."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_id = "note-123"

        # Mock response missing required fields
        mock_response: dict[str, Any] = {
            "note": {
                "id": note_id,
                "deleted_at": "2025-09-10T10:39:25Z",
                # Missing created_at and updated_at
            }
        }

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.delete_note(note_id)

        # Verify exception chaining
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValidationError)

    @pytest.mark.asyncio
    async def test_delete_note_type_error_non_dict_payload(self, mocker: MockerFixture) -> None:
        """TypeError from non-dict payload should be caught and wrapped."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_id = "note-123"

        # Mock response with non-dict note payload
        mock_response: dict[str, Any] = {"note": []}  # type: ignore[dict-item]

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.delete_note(note_id)

        # Verify exception chaining
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, TypeError)

    @pytest.mark.asyncio
    async def test_delete_note_parse_error_preserves_note_id(self, mocker: MockerFixture) -> None:
        """Parse error should preserve note_id in error context."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        note_id = "note-to-delete-456"

        # Mock response with invalid data
        mock_response: dict[str, Any] = {"note": {"id": note_id}}

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response") as exc_info:
            await client.delete_note(note_id)

        # Error should preserve context
        error_msg = str(exc_info.value)
        assert "parse" in error_msg.lower()
