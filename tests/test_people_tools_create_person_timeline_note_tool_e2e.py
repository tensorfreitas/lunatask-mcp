"""End-to-end tests for the create_person_timeline_note MCP tool."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskValidationError
from lunatask_mcp.api.models_people import PersonTimelineNoteResponse
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.people import PeopleTools


class TestCreatePersonTimelineNoteToolEndToEnd:
    """E2E validation for create_person_timeline_note tool registration and execution."""

    def test_tool_registered_with_mcp(self) -> None:
        """Tool should be discoverable with descriptive metadata and schema."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        PeopleTools(mcp, client)

        tool_manager = mcp._tool_manager  # type: ignore[attr-defined]  # testing internal API
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined]
        tool_names = [tool.name for tool in registered_tools]

        assert "create_person_timeline_note" in tool_names

        create_tool = next(
            tool for tool in registered_tools if tool.name == "create_person_timeline_note"
        )
        assert create_tool.description is not None
        assert "Create a timeline note" in create_tool.description

        try:
            if hasattr(create_tool, "input_schema"):
                schema = getattr(create_tool, "input_schema", None)  # type: ignore[attr-defined]
                if isinstance(schema, dict) and "properties" in schema:
                    properties = schema["properties"]  # type: ignore[index]
                    assert "person_id" in properties
                    assert "content" in properties
                    assert "date" in properties
        except (AttributeError, KeyError, TypeError):
            pass

    @pytest.mark.asyncio
    async def test_tool_success_flow(self, mocker: MockerFixture) -> None:
        """Tool should run end-to-end and return structured success payload."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        note_response = PersonTimelineNoteResponse(
            id="timeline-note-789",
            date_on="2025-09-21",
            created_at="2025-09-21T09:00:00Z",
            updated_at="2025-09-21T09:00:00Z",
        )

        mocker.patch.object(client, "create_person_timeline_note", return_value=note_response)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_timeline_note_tool(
            ctx=mock_ctx,
            person_id="person-xyz",
            content="Called dad to confirm travel plans",
            date_on="2025-09-21",
        )

        assert result == {
            "success": True,
            "person_timeline_note_id": "timeline-note-789",
            "message": "Person timeline note created successfully",
        }

        client.create_person_timeline_note.assert_called_once()  # type: ignore[attr-defined]
        mock_ctx.info.assert_any_call("Creating person timeline note")
        mock_ctx.info.assert_any_call("Person timeline note created: timeline-note-789")

    @pytest.mark.asyncio
    async def test_tool_handles_validation_error(self, mocker: MockerFixture) -> None:
        """Client validation errors should propagate through structured response."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person_timeline_note",
            side_effect=LunaTaskValidationError("Invalid body"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_timeline_note_tool(
            ctx=mock_ctx,
            person_id="person-xyz",
            content="Called dad to confirm travel plans",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        mock_ctx.error.assert_awaited_once()  # type: ignore[attr-defined]
