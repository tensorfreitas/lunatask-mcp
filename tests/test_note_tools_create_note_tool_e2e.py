"""End-to-end tests for NotesTools.create_note tool registration."""

import inspect

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskValidationError
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.notes import NotesTools
from tests.factories import create_note_response


class TestCreateNoteToolEndToEnd:
    """End-to-end validation for create_note MCP tool."""

    def test_create_note_tool_registration(self) -> None:
        """Tool should be registered with FastMCP and expose expected schema."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        NotesTools(mcp, client)

        tool_manager = mcp._tool_manager  # type: ignore[attr-defined]
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined]

        tool_names = [tool.name for tool in registered_tools]
        assert "create_note" in tool_names

        create_note_tool = next(tool for tool in registered_tools if tool.name == "create_note")
        assert create_note_tool.description is not None
        assert "Create a note" in create_note_tool.description

        try:
            if hasattr(create_note_tool, "input_schema"):
                schema = getattr(create_note_tool, "input_schema", None)
                if isinstance(schema, dict) and "properties" in schema:
                    properties = schema["properties"]  # type: ignore[index]
                    expected_params = {
                        "notebook_id",
                        "name",
                        "content",
                        "date_on",
                        "source",
                        "source_id",
                    }
                    for param in expected_params:
                        assert param in properties
        except (AttributeError, KeyError, TypeError):
            pass

    @pytest.mark.asyncio
    async def test_create_note_tool_full_execution_flow(self, mocker: MockerFixture) -> None:
        """Tool should execute end-to-end and return structured success payload."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        created_note = create_note_response(note_id="note-789", notebook_id="notebook-xyz")

        mocker.patch.object(client, "create_note", return_value=created_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.create_note_tool(
            ctx=mock_ctx,
            notebook_id="notebook-xyz",
            name="Weekly review",
            content="# Heading",
            date_on="2025-09-15",
            source="evernote",
            source_id="external-456",
        )

        assert result["success"] is True
        assert result["note_id"] == "note-789"
        assert result["message"] == "Note created successfully"

        client.create_note.assert_called_once()  # type: ignore[attr-defined]
        note_arg = client.create_note.call_args[0][0]  # type: ignore[attr-defined]
        assert note_arg.notebook_id == "notebook-xyz"  # type: ignore[attr-defined]
        assert note_arg.source == "evernote"  # type: ignore[attr-defined]
        assert note_arg.source_id == "external-456"  # type: ignore[attr-defined]

        mock_ctx.info.assert_any_call("Creating new note")
        mock_ctx.info.assert_any_call("Successfully created note note-789")

    @pytest.mark.asyncio
    async def test_create_note_tool_error_response_format(self, mocker: MockerFixture) -> None:
        """Tool should return structured error payloads on validation errors."""

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
            "create_note",
            side_effect=LunaTaskValidationError("Validation failed"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.create_note_tool(mock_ctx, name="Weekly review")

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Validation failed" in result["message"]

        mock_ctx.error.assert_called_once()
        error_call = mock_ctx.error.call_args[0][0]
        assert "Validation failed" in error_call

    def test_create_note_tool_signature(self) -> None:
        """Function signature should expose expected parameters."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        notes_tools = NotesTools(mcp, client)
        sig = inspect.signature(notes_tools.create_note_tool)
        params = list(sig.parameters.keys())

        assert params[0] == "ctx"
        for expected in ["notebook_id", "name", "content", "date_on", "source", "source_id"]:
            assert expected in params
