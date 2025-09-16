"""Tests for TaskTools create task tool end-to-end validation.

This module contains end-to-end validation tests for the TaskTools create_task tool
that validate complete MCP tool functionality from client perspective.
"""

import inspect
from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskValidationError
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


class TestCreateTaskToolEndToEnd:
    """End-to-end validation tests for create_task tool discoverability and execution."""

    def test_create_task_tool_registered_with_mcp(self) -> None:
        """Test that create_task tool is properly registered and discoverable via MCP."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Initialize TaskTools to register create_task tool
        TaskTools(mcp, client)

        # Verify tool is registered in the MCP server
        tool_manager = mcp._tool_manager  # type: ignore[attr-defined] # Testing internal API
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined] # Testing internal API
        tool_names = [tool.name for tool in registered_tools]

        assert "create_task" in tool_names

        # Verify tool has proper schema
        create_task_tool = next(tool for tool in registered_tools if tool.name == "create_task")
        assert create_task_tool.description is not None
        assert "Create a new task in LunaTask" in create_task_tool.description

        # Verify tool has expected parameters - using try/except for optional schema inspection
        try:
            if hasattr(create_task_tool, "input_schema"):
                schema = getattr(create_task_tool, "input_schema", None)  # type: ignore[attr-defined] # Optional attribute inspection
                if isinstance(schema, dict) and "properties" in schema:
                    properties = schema["properties"]  # type: ignore[index] # Dict access for schema validation

                    # Required parameter
                    assert "name" in properties

                    # Optional parameters
                    expected_optional_params = {"note", "area_id", "status", "priority"}
                    for param in expected_optional_params:
                        assert param in properties, f"Missing expected parameter: {param}"
        except (AttributeError, KeyError, TypeError):
            # Schema inspection is optional - tool registration is the main validation
            pass

    @pytest.mark.asyncio
    async def test_create_task_tool_complete_execution_flow(self, mocker: MockerFixture) -> None:
        """Test complete tool execution flow from MCP client perspective."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context and successful API response
        mock_ctx = mocker.AsyncMock()
        created_task = create_task_response(
            task_id="e2e-task-123",
            status="started",
            created_at=datetime(2025, 8, 22, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 22, 10, 0, 0, tzinfo=UTC),
            area_id="work-area",
            priority=2,
        )

        mocker.patch.object(client, "create_task", return_value=created_task)
        mock_context_manager = mocker.AsyncMock()
        mock_context_manager.__aenter__.return_value = client
        mock_context_manager.__aexit__.return_value = None
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test tool execution with full parameter set
        result = await task_tools.create_task_tool(
            ctx=mock_ctx,
            name="E2E Test Task",
            note="This is an end-to-end test task",
            area_id="work-area",
            status="started",
            priority=2,
        )

        # Verify successful response structure
        assert result["success"] is True
        assert result["task_id"] == "e2e-task-123"
        assert result["message"] == "Task created successfully"

        # Verify API was called with correct parameters
        client.create_task.assert_called_once()  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        call_args = client.create_task.call_args[0][0]  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object

        assert call_args.name == "E2E Test Task"  # type: ignore[attr-defined] # TaskCreate field access on mock call args
        assert call_args.note == "This is an end-to-end test task"  # type: ignore[attr-defined] # TaskCreate field access on mock call args
        assert call_args.area_id == "work-area"  # type: ignore[attr-defined] # TaskCreate field access on mock call args
        assert call_args.status == "started"  # type: ignore[attr-defined] # TaskCreate field access on mock call args
        expected_priority = 2
        assert call_args.priority == expected_priority  # type: ignore[attr-defined] # TaskCreate field access on mock call args

        # Verify logging calls
        mock_ctx.info.assert_any_call("Creating new task: E2E Test Task")
        mock_ctx.info.assert_any_call("Successfully created task e2e-task-123")

    @pytest.mark.asyncio
    async def test_create_task_tool_error_response_format(self, mocker: MockerFixture) -> None:
        """Test that tool error responses are properly formatted for MCP clients."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock validation error from API
        mocker.patch.object(
            client, "create_task", side_effect=LunaTaskValidationError("Task name is required")
        )
        mock_context_manager = mocker.AsyncMock()
        mock_context_manager.__aenter__.return_value = client
        mock_context_manager.__aexit__.return_value = None
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test error response structure
        result = await task_tools.create_task_tool(
            ctx=mock_ctx,
            name="",  # Invalid empty name
            area_id="test-area-id",
        )

        # Verify error response format
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Task validation failed" in result["message"]

        # Verify error logging
        mock_ctx.error.assert_called_once()
        error_call_args = mock_ctx.error.call_args[0][0]
        assert "Task validation failed" in error_call_args

    def test_create_task_tool_parameter_schema_validation(self) -> None:
        """Test that tool parameter schema matches TaskCreate model requirements."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Initialize TaskTools to register create_task tool
        TaskTools(mcp, client)

        # Get the create_task tool
        tool_manager = mcp._tool_manager  # type: ignore[attr-defined] # Testing internal API
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined] # Testing internal API
        create_task_tool = next(tool for tool in registered_tools if tool.name == "create_task")

        # Verify tool function signature matches expected parameters
        tool_func = create_task_tool.fn  # type: ignore[attr-defined] # Tool function access for signature validation
        sig = inspect.signature(tool_func)  # type: ignore[arg-type] # Function signature inspection

        # Check that all expected parameters are present
        param_names = list(sig.parameters.keys())

        # First parameter should be 'ctx' for Context
        assert param_names[0] == "ctx"

        # Required parameter
        assert "name" in param_names

        # Optional parameters with defaults
        expected_optional = {"note", "area_id", "status", "priority"}
        for param in expected_optional:
            assert param in param_names, f"Missing parameter: {param}"

        # Verify parameter types and defaults
        name_param = sig.parameters["name"]
        assert name_param.annotation is str
        assert name_param.default == inspect.Parameter.empty  # Required parameter

        status_param = sig.parameters["status"]
        assert status_param.default == "later"  # Default status

        # Verify optional parameters have proper defaults
        note_param = sig.parameters["note"]
        assert note_param.default is None
