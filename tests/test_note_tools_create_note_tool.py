"""Tests for NotesTools.create_note_tool()."""

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
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import NoteCreate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.notes import NotesTools
from tests.factories import create_note_response


class TestCreateNoteTool:
    """Test suite for the create_note MCP tool."""

    @pytest.mark.asyncio
    async def test_create_note_tool_success(self, mocker: MockerFixture) -> None:
        """Tool should return success payload and note_id on creation."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        created_note = create_note_response(
            note_id="note-123",
            notebook_id="notebook-abc",
            created_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
        )

        mocker.patch.object(client, "create_note", return_value=created_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.create_note_tool(mock_ctx, name="Weekly review")

        assert result == {
            "success": True,
            "note_id": "note-123",
            "message": "Note created successfully",
        }

        client.create_note.assert_called_once()  # type: ignore[attr-defined]
        call_arg = client.create_note.call_args[0][0]  # type: ignore[attr-defined]
        assert isinstance(call_arg, NoteCreate)
        assert call_arg.name == "Weekly review"

    @pytest.mark.asyncio
    async def test_create_note_tool_duplicate(self, mocker: MockerFixture) -> None:
        """Duplicate detection should return success with duplicate flag."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "create_note", return_value=None)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.create_note_tool(
            mock_ctx,
            notebook_id="notebook-xyz",
            name="Weekly review",
            source="evernote",
            source_id="external-123",
        )

        assert result == {
            "success": True,
            "duplicate": True,
            "message": ("Note already exists for this source/source_id in the provided notebook"),
        }

    @pytest.mark.asyncio
    async def test_create_note_tool_invalid_date(self, mocker: MockerFixture) -> None:
        """Invalid date_on must return structured validation error."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        result = await notes_tools.create_note_tool(
            mock_ctx, name="Weekly review", date_on="2025/09/15"
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid date_on format" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("exception", "error_key"),
        [
            (LunaTaskValidationError("Invalid body"), "validation_error"),
            (LunaTaskSubscriptionRequiredError("Upgrade required"), "subscription_required"),
            (LunaTaskAuthenticationError("Invalid token"), "authentication_error"),
            (LunaTaskRateLimitError("Too many requests"), "rate_limit_error"),
            (LunaTaskServerError("Internal error"), "server_error"),
            (LunaTaskServiceUnavailableError("Maintenance"), "server_error"),
            (LunaTaskTimeoutError("Timeout"), "timeout_error"),
            (LunaTaskNetworkError("Network error"), "network_error"),
        ],
    )
    async def test_create_note_tool_maps_known_exceptions(
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

        mocker.patch.object(client, "create_note", side_effect=exception)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.create_note_tool(mock_ctx, name="Weekly review")

        assert result["success"] is False
        assert result["error"] == error_key
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_create_note_tool_unexpected_error(self, mocker: MockerFixture) -> None:
        """Unexpected exceptions should surface as api_error payloads."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "create_note", side_effect=LunaTaskAPIError("Boom"))
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.create_note_tool(mock_ctx, name="Weekly review")

        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "Boom" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]
