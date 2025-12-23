"""Tests for NotesTools.update_note_tool()."""

from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
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
from lunatask_mcp.api.models import NoteUpdate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.notes import NotesTools
from tests.factories import create_note_response


class TestUpdateNoteTool:
    """Test suite for the update_note MCP tool."""

    @pytest.mark.asyncio
    async def test_update_note_tool_success_all_fields(self, mocker: MockerFixture) -> None:
        """Tool should return success payload with updated note data."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        updated_note = create_note_response(
            note_id="note-123",
            notebook_id="notebook-456",
            created_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2025, 9, 20, 14, 22, 10, tzinfo=UTC),
        )

        mocker.patch.object(client, "update_note", return_value=updated_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(
            mock_ctx,
            note_id="note-123",
            name="Updated name",
            content="Updated content",
            notebook_id="notebook-456",
            date_on="2025-09-20",
        )

        assert result["success"] is True
        assert result["note_id"] == "note-123"
        assert result["message"] == "Note updated successfully"
        assert "note" in result
        assert result["note"]["id"] == "note-123"

        client.update_note.assert_called_once()  # type: ignore[attr-defined]
        call_args = client.update_note.call_args  # type: ignore[attr-defined]
        assert call_args[0][0] == "note-123"  # note_id argument
        assert isinstance(call_args[0][1], NoteUpdate)  # NoteUpdate argument

    @pytest.mark.asyncio
    async def test_update_note_tool_success_single_field(self, mocker: MockerFixture) -> None:
        """Tool should handle updating only a single field."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        updated_note = create_note_response(
            note_id="note-123",
            notebook_id="notebook-456",
            created_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2025, 9, 20, 14, 22, 10, tzinfo=UTC),
        )

        mocker.patch.object(client, "update_note", return_value=updated_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(
            mock_ctx,
            note_id="note-123",
            name="Just update the name",
        )

        assert result["success"] is True
        assert result["note_id"] == "note-123"

        client.update_note.assert_called_once()  # type: ignore[attr-defined]
        call_args = client.update_note.call_args  # type: ignore[attr-defined]
        update_obj: NoteUpdate = call_args[0][1]  # type: ignore[misc]
        assert update_obj.name == "Just update the name"  # type: ignore[attr-defined]
        assert update_obj.content is None  # type: ignore[attr-defined]
        assert update_obj.notebook_id is None  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_success_content_only(self, mocker: MockerFixture) -> None:
        """Tool should handle updating only content field."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        updated_note = create_note_response(
            note_id="note-123",
            notebook_id="notebook-456",
            created_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2025, 9, 20, 14, 22, 10, tzinfo=UTC),
        )

        mocker.patch.object(client, "update_note", return_value=updated_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(
            mock_ctx,
            note_id="note-123",
            content="## New content\n- item 1",
        )

        assert result["success"] is True
        client.update_note.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_empty_note_id(self, mocker: MockerFixture) -> None:
        """Empty note_id must return validation error."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        result = await notes_tools.update_note_tool(mock_ctx, note_id="", name="Update")

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Note ID cannot be empty" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_whitespace_only_note_id(self, mocker: MockerFixture) -> None:
        """Whitespace-only note_id must return validation error."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        result = await notes_tools.update_note_tool(mock_ctx, note_id="   ", name="Update")

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Note ID cannot be empty" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_no_fields_provided(self, mocker: MockerFixture) -> None:
        """Must return validation error when no fields are provided for update."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        result = await notes_tools.update_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "At least one field must be provided" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_invalid_date_format(self, mocker: MockerFixture) -> None:
        """Invalid date_on must return structured validation error."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        result = await notes_tools.update_note_tool(
            mock_ctx, note_id="note-123", date_on="2025/09/20"
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid date_on format" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_note_not_found(self, mocker: MockerFixture) -> None:
        """Not found error should return not_found_error payload."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client, "update_note", side_effect=LunaTaskNotFoundError("Note not found")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(
            mock_ctx, note_id="note-nonexistent", name="Update"
        )

        assert result["success"] is False
        assert result["error"] == "not_found_error"
        assert "Note not found" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("exception", "error_key"),
        [
            (LunaTaskValidationError("Invalid body"), "validation_error"),
            (LunaTaskAuthenticationError("Invalid token"), "authentication_error"),
            (LunaTaskRateLimitError("Too many requests"), "rate_limit_error"),
            (LunaTaskServerError("Internal error"), "server_error"),
            (LunaTaskServiceUnavailableError("Maintenance"), "server_error"),
            (LunaTaskTimeoutError("Timeout"), "timeout_error"),
            (LunaTaskNetworkError("Network error"), "network_error"),
        ],
    )
    async def test_update_note_tool_maps_known_exceptions(
        self, mocker: MockerFixture, exception: Exception, error_key: str
    ) -> None:
        """Known exceptions must map to structured MCP error payloads."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "update_note", side_effect=exception)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(mock_ctx, note_id="note-123", name="Update")

        assert result["success"] is False
        assert result["error"] == error_key
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_api_error(self, mocker: MockerFixture) -> None:
        """Generic API exceptions should surface as api_error payloads."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "update_note", side_effect=LunaTaskAPIError("Boom"))
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(mock_ctx, note_id="note-123", name="Update")

        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "Boom" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_unexpected_error(self, mocker: MockerFixture) -> None:
        """Unexpected exceptions should surface as unexpected_error payloads."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "update_note", side_effect=RuntimeError("Unexpected"))
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(mock_ctx, note_id="note-123", name="Update")

        assert result["success"] is False
        assert result["error"] == "unexpected_error"
        assert "Unexpected" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]
