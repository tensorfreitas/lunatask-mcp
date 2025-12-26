"""Tests for NotesTools.delete_note_tool()."""

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
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.notes import NotesTools
from tests.factories import create_note_response


class TestDeleteNoteTool:
    """Test suite for the delete_note MCP tool."""

    @pytest.mark.asyncio
    async def test_delete_note_tool_success(self, mocker: MockerFixture) -> None:
        """Tool should return success payload with note_id and deleted_at on deletion."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        deleted_note = create_note_response(
            note_id="note-123",
            deleted_at=datetime(2025, 12, 23, 17, 15, 47, 398000, tzinfo=UTC),
        )

        mocker.patch.object(client, "delete_note", return_value=deleted_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result == {
            "success": True,
            "note_id": "note-123",
            "deleted_at": "2025-12-23T17:15:47.398000+00:00",
            "message": "Note deleted successfully",
        }

        client.delete_note.assert_called_once_with("note-123")  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_delete_note_tool_validation_empty_id(self, mocker: MockerFixture) -> None:
        """Tool should validate note ID and reject empty/whitespace IDs."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock the delete_note method to verify it's not called
        mock_delete_note = mocker.patch.object(client, "delete_note")

        # Test empty string
        result = await notes_tools.delete_note_tool(mock_ctx, note_id="")

        assert result == {
            "success": False,
            "error": "validation_error",
            "message": "Note ID cannot be empty",
        }

        # Test whitespace-only string
        result = await notes_tools.delete_note_tool(mock_ctx, note_id="   ")

        assert result == {
            "success": False,
            "error": "validation_error",
            "message": "Note ID cannot be empty",
        }

        # Verify no API calls were made
        mock_delete_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_note_tool_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Tool should handle 404 Not Found errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskNotFoundError("Note not found"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="nonexistent-note")

        assert result["success"] is False
        assert result["error"] == "not_found_error"
        assert "Note not found" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Tool should handle authentication errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskAuthenticationError("Invalid bearer token"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "authentication_error"
        assert "Invalid bearer token" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Tool should handle rate limit errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "rate_limit_error"
        assert "Rate limit exceeded" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_server_error_5xx(self, mocker: MockerFixture) -> None:
        """Tool should handle server errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskServerError("Internal server error", status_code=500),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "server_error"
        assert "Internal server error" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_service_unavailable_error_503(
        self, mocker: MockerFixture
    ) -> None:
        """Tool should handle service unavailable errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskServiceUnavailableError("Service temporarily unavailable"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "server_error"
        assert "Service temporarily unavailable" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_timeout_error(self, mocker: MockerFixture) -> None:
        """Tool should handle timeout errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "timeout_error"
        assert "Request timeout" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_network_error(self, mocker: MockerFixture) -> None:
        """Tool should handle network errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskNetworkError("Network connection failed"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "network_error"
        assert "Network connection failed" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_api_error(self, mocker: MockerFixture) -> None:
        """Tool should handle general API errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskAPIError("API error occurred"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "API error occurred" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_unexpected_error(self, mocker: MockerFixture) -> None:
        """Tool should handle unexpected exceptions correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=RuntimeError("Unexpected error"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "unexpected_error"
        assert "Unexpected error during note deletion" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_note_tool_context_logging_success(self, mocker: MockerFixture) -> None:
        """Tool should log success cases through FastMCP context."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        deleted_note = create_note_response(
            note_id="note-log-test",
            deleted_at=datetime(2025, 12, 23, 17, 15, 47, 398000, tzinfo=UTC),
        )

        mocker.patch.object(client, "delete_note", return_value=deleted_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        await notes_tools.delete_note_tool(mock_ctx, note_id="note-log-test")

        # Verify context logging calls
        mock_ctx.info.assert_any_call("Deleting note note-log-test")
        mock_ctx.info.assert_any_call("Successfully deleted note note-log-test")

    @pytest.mark.asyncio
    async def test_delete_note_tool_context_logging_error(self, mocker: MockerFixture) -> None:
        """Tool should log error cases through FastMCP context."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskNotFoundError("Note not found"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        await notes_tools.delete_note_tool(mock_ctx, note_id="nonexistent-note")

        # Verify context error logging
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert "Note not found" in error_message

    @pytest.mark.asyncio
    async def test_delete_note_tool_non_idempotent_behavior(self, mocker: MockerFixture) -> None:
        """Tool should handle non-idempotent behavior (second delete returns not found)."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # First delete succeeds
        deleted_note = create_note_response(
            note_id="note-123",
            deleted_at=datetime(2025, 12, 23, 17, 15, 47, 398000, tzinfo=UTC),
        )

        mocker.patch.object(client, "delete_note", return_value=deleted_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is True
        assert result["note_id"] == "note-123"

        # Second delete returns not found
        mocker.patch.object(
            client,
            "delete_note",
            side_effect=LunaTaskNotFoundError("Note not found"),
        )

        result = await notes_tools.delete_note_tool(mock_ctx, note_id="note-123")

        assert result["success"] is False
        assert result["error"] == "not_found_error"
