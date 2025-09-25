"""Unit tests for PeopleTools.create_person_timeline_note_tool()."""

from __future__ import annotations

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
from lunatask_mcp.api.models_people import (
    PersonTimelineNoteCreate,
    PersonTimelineNoteResponse,
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.people import PeopleTools


class TestCreatePersonTimelineNoteTool:
    """Test suite for create_person_timeline_note MCP tool behavior."""

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_tool_success(self, mocker: MockerFixture) -> None:
        """Tool should delegate to client and return note identifier on success."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        note_response = PersonTimelineNoteResponse(
            id="timeline-note-123",
            date_on="2025-09-22",
            created_at="2025-09-22T10:15:00Z",
            updated_at="2025-09-22T10:15:00Z",
        )

        mocker.patch.object(client, "create_person_timeline_note", return_value=note_response)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_timeline_note_tool(
            mock_ctx,
            person_id="person-123",
            content="Called mom to check in",
            date_on="2025-09-22",
        )

        assert result == {
            "success": True,
            "person_timeline_note_id": "timeline-note-123",
            "message": "Person timeline note created successfully",
        }

        client.create_person_timeline_note.assert_called_once()  # type: ignore[attr-defined]
        call_payload = client.create_person_timeline_note.call_args[0][0]  # type: ignore[attr-defined]
        assert isinstance(call_payload, PersonTimelineNoteCreate)
        assert call_payload.person_id == "person-123"
        assert call_payload.content == "Called mom to check in"
        assert call_payload.date_on is not None

        mock_ctx.info.assert_any_call("Creating person timeline note")
        mock_ctx.info.assert_any_call("Person timeline note created: timeline-note-123")

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_tool_requires_person_id(
        self, mocker: MockerFixture
    ) -> None:
        """Empty person_id should return validation error without client call."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        mocked_create = mocker.patch.object(client, "create_person_timeline_note")

        result = await people_tools.create_person_timeline_note_tool(
            mock_ctx,
            person_id="",
            content="Something",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "person_id" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]
        mocked_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_tool_requires_content(
        self, mocker: MockerFixture
    ) -> None:
        """Blank content should return validation error without invoking client."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        mocked_create = mocker.patch.object(client, "create_person_timeline_note")

        result = await people_tools.create_person_timeline_note_tool(
            mock_ctx,
            person_id="person-123",
            content="   ",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "content" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]
        mocked_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_tool_validates_date(
        self, mocker: MockerFixture
    ) -> None:
        """Invalid ISO date strings should return validation errors."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        mocked_create = mocker.patch.object(client, "create_person_timeline_note")

        result = await people_tools.create_person_timeline_note_tool(
            mock_ctx,
            person_id="person-123",
            content="Note",
            date_on="2025/09/22",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid date_on" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]
        mocked_create.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("exception", "error_key"),
        [
            (LunaTaskValidationError("Invalid body"), "validation_error"),
            (LunaTaskSubscriptionRequiredError("Upgrade required"), "subscription_required"),
            (LunaTaskAuthenticationError("Invalid token"), "authentication_error"),
            (LunaTaskRateLimitError("Rate limit"), "rate_limit_error"),
            (LunaTaskServerError("Server exploded"), "server_error"),
            (LunaTaskServiceUnavailableError("Maintenance"), "server_error"),
            (LunaTaskTimeoutError("Timeout"), "timeout_error"),
            (LunaTaskNetworkError("Network down"), "network_error"),
        ],
    )
    async def test_create_person_timeline_note_tool_maps_known_exceptions(
        self, mocker: MockerFixture, exception: Exception, error_key: str
    ) -> None:
        """Known exceptions from client should produce structured error payloads."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "create_person_timeline_note", side_effect=exception)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_timeline_note_tool(
            mock_ctx,
            person_id="person-abc",
            content="Note",
        )

        assert result["success"] is False
        assert result["error"] == error_key
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_tool_handles_api_error(
        self, mocker: MockerFixture
    ) -> None:
        """API errors should bubble as api_error payloads."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client, "create_person_timeline_note", side_effect=LunaTaskAPIError("Boom")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_timeline_note_tool(
            mock_ctx,
            person_id="person-abc",
            content="Note",
        )

        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "Boom" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_tool_handles_unexpected_error(
        self, mocker: MockerFixture
    ) -> None:
        """Unexpected exceptions should map to unexpected_error payload."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "create_person_timeline_note", side_effect=ValueError("boom"))
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_timeline_note_tool(
            mock_ctx,
            person_id="person-abc",
            content="Note",
        )

        assert result["success"] is False
        assert result["error"] == "unexpected_error"
        assert "boom" in result["message"]
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]
