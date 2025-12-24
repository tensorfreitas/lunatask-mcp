"""Tests for NotesTools update_note tool end-to-end validation.

This module contains end-to-end validation tests for the NotesTools update_note tool
that validate complete MCP tool functionality from client perspective.
"""

from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskNotFoundError
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.notes import NotesTools
from tests.factories import create_note_response


class TestUpdateNoteToolEndToEnd:
    """End-to-end validation tests for update_note tool discoverability and execution."""

    def test_update_note_tool_registered_with_mcp(self) -> None:
        """Test that update_note tool is properly registered and discoverable via MCP."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Initialize NotesTools to register update_note tool
        NotesTools(mcp, client)

        # Verify tool is registered in the MCP server
        tool_manager = mcp._tool_manager  # type: ignore[attr-defined] # Testing internal API
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined] # Testing internal API
        tool_names = [tool.name for tool in registered_tools]

        assert "update_note" in tool_names

        # Verify tool has proper schema
        update_note_tool = next(tool for tool in registered_tools if tool.name == "update_note")
        assert update_note_tool.description is not None
        assert "Update an existing note" in update_note_tool.description

        # Verify tool has expected parameters - using try/except for optional schema inspection
        try:
            if hasattr(update_note_tool, "input_schema"):
                schema = getattr(update_note_tool, "input_schema", None)  # type: ignore[attr-defined] # Optional attribute inspection
                if isinstance(schema, dict) and "properties" in schema:
                    properties = schema["properties"]  # type: ignore[index] # Dict access for schema validation

                    # Required parameters
                    assert "note_id" in properties

                    # Optional parameters
                    assert "name" in properties
                    assert "content" in properties
                    assert "notebook_id" in properties
                    assert "date_on" in properties

        except (AttributeError, KeyError, TypeError):
            # Schema inspection is optional - tool registration is the main validation
            pass

    @pytest.mark.asyncio
    async def test_update_note_tool_complete_execution_flow_all_fields(
        self, mocker: MockerFixture
    ) -> None:
        """Test complete tool execution flow with all fields from MCP client perspective."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        # Mock context and successful API response
        mock_ctx = mocker.AsyncMock()
        updated_note = create_note_response(
            note_id="e2e-note-update-123",
            notebook_id="notebook-updated",
            created_at=datetime(2025, 9, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2025, 12, 23, 17, 30, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "update_note", return_value=updated_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test tool execution with all fields
        result = await notes_tools.update_note_tool(
            ctx=mock_ctx,
            note_id="e2e-note-update-123",
            name="Updated Title",
            content="Updated content here",
            notebook_id="notebook-updated",
            date_on="2025-12-24",
        )

        # Verify successful response structure
        assert result["success"] is True
        assert result["note_id"] == "e2e-note-update-123"
        assert result["message"] == "Note updated successfully"

        # Verify nested note object structure
        assert "note" in result
        note = result["note"]
        assert note["id"] == "e2e-note-update-123"
        assert note["notebook_id"] == "notebook-updated"
        assert "created_at" in note
        assert "updated_at" in note

        # Verify client was called correctly
        client.update_note.assert_called_once()  # type: ignore[attr-defined]

        # Verify context logging was called
        mock_ctx.info.assert_any_call("Updating note e2e-note-update-123")
        mock_ctx.info.assert_any_call("Successfully updated note e2e-note-update-123")

    @pytest.mark.asyncio
    async def test_update_note_tool_single_field_patch_semantics(
        self, mocker: MockerFixture
    ) -> None:
        """Test PATCH semantics with single field update (name only)."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        updated_note = create_note_response(
            note_id="e2e-patch-note-456",
            updated_at=datetime(2025, 12, 23, 17, 30, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "update_note", return_value=updated_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test with only name field
        result = await notes_tools.update_note_tool(
            ctx=mock_ctx,
            note_id="e2e-patch-note-456",
            name="New Title Only",
        )

        # Verify successful response
        assert result["success"] is True
        assert result["note_id"] == "e2e-patch-note-456"

        # Verify client was called
        client.update_note.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_content_only_patch(self, mocker: MockerFixture) -> None:
        """Test PATCH semantics with content field only."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        updated_note = create_note_response(
            note_id="e2e-content-note-789",
            updated_at=datetime(2025, 12, 23, 17, 30, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "update_note", return_value=updated_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test with only content field
        result = await notes_tools.update_note_tool(
            ctx=mock_ctx,
            note_id="e2e-content-note-789",
            content="## New Markdown\n- Item 1\n- Item 2",
        )

        # Verify successful response
        assert result["success"] is True
        assert result["note_id"] == "e2e-content-note-789"

        # Verify note response includes proper structure
        assert "note" in result
        assert result["note"]["id"] == "e2e-content-note-789"

    @pytest.mark.asyncio
    async def test_update_note_tool_not_found_error_workflow(self, mocker: MockerFixture) -> None:
        """Test complete not found error workflow."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock not found response
        mocker.patch.object(
            client, "update_note", side_effect=LunaTaskNotFoundError("Note not found")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await notes_tools.update_note_tool(
            ctx=mock_ctx,
            note_id="nonexistent-note",
            name="Try to update",
        )

        # Verify not found response structure
        assert result["success"] is False
        assert result["error"] == "not_found_error"
        assert "Note not found" in result["message"]

        # Verify context logging for error
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert "Note not found" in error_message

        # Verify client was called (not a validation error)
        client.update_note.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_note_tool_validation_errors_workflow(self, mocker: MockerFixture) -> None:
        """Test complete validation workflow before API call."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock client to ensure it's not called due to validation failure
        mock_update_note = mocker.patch.object(client, "update_note")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test 1: Empty ID validation
        result = await notes_tools.update_note_tool(
            ctx=mock_ctx,
            note_id="",
            name="Update",
        )

        # Verify validation error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Note ID cannot be empty" in result["message"]

        # Verify client was not called due to pre-validation failure
        mock_update_note.assert_not_called()

        # Verify error was logged to context
        assert mock_ctx.error.call_count >= 1

        # Reset mocks for next test
        mock_ctx.reset_mock()
        mock_update_note.reset_mock()

        # Test 2: No fields provided validation
        result = await notes_tools.update_note_tool(
            ctx=mock_ctx,
            note_id="valid-id",
        )

        # Verify validation error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "At least one field must be provided" in result["message"]

        # Verify client was not called
        mock_update_note.assert_not_called()

        # Reset mocks for next test
        mock_ctx.reset_mock()
        mock_update_note.reset_mock()

        # Test 3: Invalid date format validation
        result = await notes_tools.update_note_tool(
            ctx=mock_ctx,
            note_id="valid-id",
            date_on="2025/12/24",
        )

        # Verify validation error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid date_on format" in result["message"]

        # Verify client was not called
        mock_update_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_note_tool_logging_verification(self, mocker: MockerFixture) -> None:
        """Test logging output verification through complete execution."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        notes_tools = NotesTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock logger to capture stderr logging
        mock_logger = mocker.patch("lunatask_mcp.tools.notes.logger")

        updated_note = create_note_response(
            note_id="log-test-xyz",
            updated_at=datetime(2025, 12, 23, 17, 30, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "update_note", return_value=updated_note)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        await notes_tools.update_note_tool(
            mock_ctx,
            note_id="log-test-xyz",
            name="Logging verification",
        )

        # Verify stderr logging calls
        mock_logger.info.assert_called_with("Successfully updated note %s", "log-test-xyz")

        # Verify FastMCP context logging calls
        mock_ctx.info.assert_any_call("Updating note log-test-xyz")
        mock_ctx.info.assert_any_call("Successfully updated note log-test-xyz")

        # Verify no error logging occurred for success case
        mock_ctx.error.assert_not_called()
