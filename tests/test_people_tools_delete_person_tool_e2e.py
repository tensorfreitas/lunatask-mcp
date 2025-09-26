"""Tests for PeopleTools delete person tool end-to-end validation.

This module contains end-to-end validation tests for the PeopleTools delete_person tool
that validate complete MCP tool functionality from client perspective.
"""

import inspect
from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskNotFoundError
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.people import PeopleTools
from tests.factories import create_person_response


class TestDeletePersonToolEndToEnd:
    """End-to-end validation tests for delete_person tool discoverability and execution."""

    def test_delete_person_tool_registered_with_mcp(self) -> None:
        """Test that delete_person tool is properly registered and discoverable via MCP."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Initialize PeopleTools to register delete_person tool
        PeopleTools(mcp, client)

        # Verify tool is registered in the MCP server
        tool_manager = mcp._tool_manager  # type: ignore[attr-defined] # Testing internal API
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined] # Testing internal API
        tool_names = [tool.name for tool in registered_tools]

        assert "delete_person" in tool_names

        # Verify tool has proper schema
        delete_person_tool = next(tool for tool in registered_tools if tool.name == "delete_person")
        assert delete_person_tool.description is not None
        assert "Delete a person/contact in LunaTask" in delete_person_tool.description

        # Verify tool has expected parameters - using try/except for optional schema inspection
        try:
            if hasattr(delete_person_tool, "input_schema"):
                schema = getattr(delete_person_tool, "input_schema", None)  # type: ignore[attr-defined] # Optional attribute inspection
                if isinstance(schema, dict) and "properties" in schema:
                    properties = schema["properties"]  # type: ignore[index] # Dict access for schema validation

                    # Required parameters
                    assert "person_id" in properties

        except (AttributeError, KeyError, TypeError):
            # Schema inspection is optional - tool registration is the main validation
            pass

    @pytest.mark.asyncio
    async def test_delete_person_tool_complete_execution_flow(self, mocker: MockerFixture) -> None:
        """Test complete tool execution flow from MCP client perspective."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        # Mock context and successful API response
        mock_ctx = mocker.AsyncMock()
        deleted_person = create_person_response(
            person_id="e2e-person-123",
            deleted_at=datetime(2025, 9, 25, 17, 15, 47, 398000, tzinfo=UTC),
        )

        mocker.patch.object(client, "delete_person", return_value=deleted_person)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test tool execution
        result = await people_tools.delete_person_tool(
            ctx=mock_ctx,
            person_id="e2e-person-123",
        )

        # Verify successful response structure
        assert result["success"] is True
        assert result["person_id"] == "e2e-person-123"
        assert result["deleted_at"] == "2025-09-25T17:15:47.398000+00:00"
        assert result["message"] == "Person deleted successfully"

        # Verify client was called correctly
        client.delete_person.assert_called_once_with("e2e-person-123")  # type: ignore[attr-defined]

        # Verify context logging was called
        mock_ctx.info.assert_any_call("Deleting person e2e-person-123")
        mock_ctx.info.assert_any_call("Successfully deleted person e2e-person-123")

    @pytest.mark.asyncio
    async def test_delete_person_tool_not_found_workflow(self, mocker: MockerFixture) -> None:
        """Test complete not found error workflow."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock not found response
        mocker.patch.object(
            client, "delete_person", side_effect=LunaTaskNotFoundError("Person not found")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.delete_person_tool(
            ctx=mock_ctx,
            person_id="nonexistent-person-456",
        )

        # Verify not found response structure
        assert result["success"] is False
        assert result["error"] == "not_found_error"
        assert "Person not found" in result["message"]

        # Verify context logging for error
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert "Person not found" in error_message

    @pytest.mark.asyncio
    async def test_delete_person_tool_validation_workflow(self, mocker: MockerFixture) -> None:
        """Test complete validation workflow before API call."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock client to ensure it's not called due to validation failure
        mock_delete_person = mocker.patch.object(client, "delete_person")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test empty ID validation
        result = await people_tools.delete_person_tool(
            ctx=mock_ctx,
            person_id="",
        )

        # Verify validation error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Person ID cannot be empty" in result["message"]

        # Verify client was not called due to pre-validation failure
        mock_delete_person.assert_not_called()

        # Verify error was logged to context
        mock_ctx.error.assert_called_once()

    def test_delete_person_tool_integration_with_fastmcp_context(self) -> None:
        """Test that tool properly integrates with FastMCP context system."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Initialize PeopleTools
        people_tools = PeopleTools(mcp, client)

        # Verify the tool method has proper signature for FastMCP
        delete_person_method = people_tools.delete_person_tool
        signature = inspect.signature(delete_person_method)

        # Verify first parameter is context
        parameters = list(signature.parameters.values())
        min_params = 2  # ctx, person_id minimum
        assert len(parameters) >= min_params
        assert parameters[0].name == "ctx"

        # Verify required parameters
        param_names = [param.name for param in parameters]
        assert "person_id" in param_names

    @pytest.mark.asyncio
    async def test_delete_person_tool_logging_output_verification(
        self, mocker: MockerFixture
    ) -> None:
        """Test logging output verification through complete execution."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock logger to capture stderr logging
        mock_logger = mocker.patch("lunatask_mcp.tools.people.logger")

        deleted_person = create_person_response(
            person_id="log-test-789",
            deleted_at=datetime(2025, 9, 25, 17, 15, 47, 398000, tzinfo=UTC),
        )

        mocker.patch.object(client, "delete_person", return_value=deleted_person)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        await people_tools.delete_person_tool(mock_ctx, person_id="log-test-789")

        # Verify stderr logging calls
        mock_logger.info.assert_called_with("Successfully deleted person %s", "log-test-789")

        # Verify FastMCP context logging calls
        mock_ctx.info.assert_any_call("Deleting person log-test-789")
        mock_ctx.info.assert_any_call("Successfully deleted person log-test-789")

        # Verify no error logging occurred for success case
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_person_tool_non_idempotent_workflow(self, mocker: MockerFixture) -> None:
        """Test non-idempotent behavior workflow (second delete returns not found)."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # First call succeeds
        deleted_person = create_person_response(
            person_id="idempotent-test-123",
            deleted_at=datetime(2025, 9, 25, 17, 15, 47, 398000, tzinfo=UTC),
        )

        delete_call_count = 0

        def mock_delete_side_effect(*_args: object, **_kwargs: object) -> object:
            nonlocal delete_call_count
            delete_call_count += 1
            if delete_call_count == 1:
                return deleted_person
            msg = "Person not found"
            raise LunaTaskNotFoundError(msg)

        mocker.patch.object(client, "delete_person", side_effect=mock_delete_side_effect)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # First delete succeeds
        result1 = await people_tools.delete_person_tool(
            ctx=mock_ctx,
            person_id="idempotent-test-123",
        )

        assert result1["success"] is True
        assert result1["person_id"] == "idempotent-test-123"

        # Second delete fails with not found
        result2 = await people_tools.delete_person_tool(
            ctx=mock_ctx,
            person_id="idempotent-test-123",
        )

        assert result2["success"] is False
        assert result2["error"] == "not_found_error"
        assert "Person not found" in result2["message"]
