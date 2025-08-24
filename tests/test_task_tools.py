"""Tests for TaskTools MCP resource implementation.

This module contains tests for the TaskTools class that provides
MCP resources for LunaTask integration.
"""

import inspect
from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import Source, TaskCreate, TaskResponse, TaskUpdate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


class TestTaskToolsInitialization:
    """Test TaskTools initialization and resource registration."""

    def test_task_tools_initialization(self) -> None:
        """Test that TaskTools initializes correctly with MCP and client."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Should initialize without error
        task_tools = TaskTools(mcp, client)

        assert task_tools.mcp is mcp
        assert task_tools.lunatask_client is client

    def test_task_tools_registers_resources(self, mocker: MockerFixture) -> None:
        """Test that TaskTools registers both lunatask://tasks resources and all MCP tools."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource and tool registration
        mock_resource = mocker.patch.object(mcp, "resource")
        mock_tool = mocker.patch.object(mcp, "tool")

        TaskTools(mcp, client)

        # Verify both resources were registered
        mock_resource.assert_any_call("lunatask://tasks")
        mock_resource.assert_any_call("lunatask://tasks/{task_id}")
        expected_resource_count = 2
        assert mock_resource.call_count == expected_resource_count

        # Verify all tools were registered
        mock_tool.assert_any_call("create_task")
        mock_tool.assert_any_call("update_task")
        mock_tool.assert_any_call("delete_task")
        expected_tool_count = 3
        assert mock_tool.call_count == expected_tool_count


class TestTaskResourceRetrieval:
    """Test the get_tasks_resource method."""

    @pytest.mark.asyncio
    async def test_get_tasks_resource_success(self, mocker: MockerFixture) -> None:
        """Test successful task retrieval from the resource."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "test-session-123"

        # Create sample task data
        sample_task = TaskResponse(
            id="task-1",
            status="open",
            created_at=datetime(
                2025,
                8,
                20,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            priority=1,
            due_date=datetime(2025, 8, 25, 18, 0, 0, tzinfo=UTC),
            area_id="area-1",
            source=Source(type="manual", value="user_created"),
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        # Mock the client's get_tasks method
        mock_get_tasks = mocker.patch.object(client, "get_tasks", return_value=[sample_task])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource method
        result = await task_tools.get_tasks_resource(mock_ctx)

        # Verify the result structure
        assert result["resource_type"] == "lunatask_tasks"
        assert result["total_count"] == 1
        assert len(result["tasks"]) == 1

        task_data = result["tasks"][0]
        assert task_data["id"] == "task-1"
        assert task_data["status"] == "open"
        assert task_data["priority"] == 1
        assert task_data["due_date"] == "2025-08-25T18:00:00+00:00"
        assert task_data["created_at"] == "2025-08-20T10:00:00+00:00"
        assert task_data["updated_at"] == "2025-08-20T10:30:00+00:00"
        assert task_data["area_id"] == "area-1"
        assert task_data["source"]["type"] == "manual"
        assert task_data["source"]["value"] == "user_created"

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["retrieved_at"] == "test-session-123"
        assert "E2E encryption" in metadata["encrypted_fields_note"]

        # Verify context logging calls
        mock_ctx.info.assert_any_call("Retrieving tasks from LunaTask API")
        mock_ctx.info.assert_any_call("Successfully retrieved 1 tasks from LunaTask")
        mock_get_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks_resource_empty_list(self, mocker: MockerFixture) -> None:
        """Test resource with empty task list."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "test-session-123"

        # Mock empty task list
        mocker.patch.object(client, "get_tasks", return_value=[])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_tasks_resource(mock_ctx)

        assert result["resource_type"] == "lunatask_tasks"
        assert result["total_count"] == 0
        assert result["tasks"] == []
        mock_ctx.info.assert_any_call("Successfully retrieved 0 tasks from LunaTask")

    @pytest.mark.asyncio
    async def test_get_tasks_resource_lunatask_api_error(self, mocker: MockerFixture) -> None:
        """Test resource handling of LunaTask API errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock API error
        api_error = LunaTaskAPIError("Authentication failed", 401)
        mocker.patch.object(client, "get_tasks", side_effect=api_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the API error
        with pytest.raises(LunaTaskAPIError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is api_error
        mock_ctx.error.assert_called_once()
        assert "Failed to retrieve tasks from LunaTask API" in mock_ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_tasks_resource_unexpected_error(self, mocker: MockerFixture) -> None:
        """Test resource handling of unexpected errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock unexpected error
        unexpected_error = ValueError("Unexpected error")
        mocker.patch.object(client, "get_tasks", side_effect=unexpected_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should wrap in LunaTaskAPIError
        with pytest.raises(LunaTaskAPIError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value.__cause__ is unexpected_error
        mock_ctx.error.assert_called_once()
        assert "Unexpected error retrieving tasks" in mock_ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_tasks_resource_with_null_optional_fields(
        self, mocker: MockerFixture
    ) -> None:
        """Test resource handles tasks with null optional fields."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task with null optional fields
        sample_task = TaskResponse(
            id="task-2",
            status="completed",
            created_at=datetime(
                2025,
                8,
                18,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 19, 9, 0, 0, tzinfo=UTC),
            priority=None,
            due_date=None,
            area_id=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "get_tasks", return_value=[sample_task])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_tasks_resource(mock_ctx)

        task_data = result["tasks"][0]
        assert task_data["id"] == "task-2"
        assert task_data["status"] == "completed"
        assert task_data["priority"] is None
        assert task_data["due_date"] is None
        assert task_data["area_id"] is None
        assert task_data["source"] is None


class TestTaskResourceErrorHandling:
    """Test comprehensive error handling in TaskTools resource methods."""

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of authentication errors (401)."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="invalid_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock authentication error
        auth_error = LunaTaskAuthenticationError("Authentication failed")
        mocker.patch.object(client, "get_tasks", side_effect=auth_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the authentication error
        with pytest.raises(LunaTaskAuthenticationError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is auth_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: Invalid or expired LunaTask API credentials"
        )

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of rate limit errors (429)."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock rate limit error
        rate_limit_error = LunaTaskRateLimitError("Rate limit exceeded")
        mocker.patch.object(client, "get_tasks", side_effect=rate_limit_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the rate limit error
        with pytest.raises(LunaTaskRateLimitError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is rate_limit_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: LunaTask API rate limit exceeded - please try again later"
        )

    @pytest.mark.asyncio
    async def test_server_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of server errors (5xx)."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock server error
        server_error = LunaTaskServerError("Internal server error", status_code=500)
        mocker.patch.object(client, "get_tasks", side_effect=server_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the server error
        with pytest.raises(LunaTaskServerError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is server_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: LunaTask server error (500) - please try again"
        )

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of timeout errors."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock timeout error
        timeout_error = LunaTaskTimeoutError("Request timeout", status_code=524)
        mocker.patch.object(client, "get_tasks", side_effect=timeout_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the timeout error
        with pytest.raises(LunaTaskTimeoutError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is timeout_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: Request to LunaTask API timed out - please try again"
        )

    @pytest.mark.asyncio
    async def test_error_logging_uses_ctx_error_method(self, mocker: MockerFixture) -> None:
        """Test that all error scenarios properly use ctx.error for MCP logging."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock a generic API error
        api_error = LunaTaskAPIError("Generic API error", status_code=400)
        mocker.patch.object(client, "get_tasks", side_effect=api_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the error
        with pytest.raises(LunaTaskAPIError):
            await task_tools.get_tasks_resource(mock_ctx)

        # Verify ctx.error was called with appropriate message format
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Failed to retrieve tasks from LunaTask API:" in error_call_msg
        assert "Generic API error" in error_call_msg


class TestTaskToolsPaginationAndFiltering:
    """Test pagination and filtering capabilities in TaskTools."""

    @pytest.mark.asyncio
    async def test_resource_uses_client_pagination_support(self, mocker: MockerFixture) -> None:
        """Test that TaskTools resource leverages LunaTaskClient's pagination support."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock the client's get_tasks method to verify it accepts parameters
        mock_get_tasks = mocker.patch.object(client, "get_tasks", return_value=[])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource method
        await task_tools.get_tasks_resource(mock_ctx)

        # Verify get_tasks was called (currently without parameters at resource level)
        # This confirms the foundation is in place for parameter support
        mock_get_tasks.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_client_pagination_parameter_forwarding(self, mocker: MockerFixture) -> None:
        """Test that LunaTaskClient properly forwards pagination parameters."""
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the make_request method to verify parameter forwarding
        mock_make_request = mocker.patch.object(client, "make_request", return_value={"tasks": []})

        # Test pagination parameter forwarding
        await client.get_tasks(limit=50, offset=100, status="open")

        # Verify parameters were forwarded correctly
        mock_make_request.assert_called_once_with(
            "GET", "tasks", params={"limit": 50, "offset": 100, "status": "open"}
        )

    @pytest.mark.asyncio
    async def test_client_filters_none_parameters(self, mocker: MockerFixture) -> None:
        """Test that client properly filters out None parameters."""
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the make_request method
        mock_make_request = mocker.patch.object(client, "make_request", return_value={"tasks": []})

        # Test with mixed parameters including None values
        await client.get_tasks(limit=25, offset=None, status="completed", priority=None)

        # Verify None parameters were filtered out
        mock_make_request.assert_called_once_with(
            "GET", "tasks", params={"limit": 25, "status": "completed"}
        )

    def test_pagination_api_documentation_compliance(self) -> None:
        """Test that pagination implementation follows API documentation patterns."""

        # This test documents the current state: MCP resources don't support parameters
        # but the underlying client does, enabling future tool implementations

        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Verify client method signature supports pagination
        signature = inspect.signature(client.get_tasks)

        # Should accept **params for flexibility
        param_names = list(signature.parameters.keys())
        assert "params" in param_names or any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()
        ), "get_tasks should accept **params for pagination/filtering"


class TestSingleTaskResource:
    """Test the single task resource template lunatask://tasks/{task_id}."""

    def test_single_task_resource_registration(self, mocker: MockerFixture) -> None:
        """Test that TaskTools registers the lunatask://tasks/{task_id} resource template."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource registration
        mock_resource = mocker.patch.object(mcp, "resource")

        TaskTools(mcp, client)

        # Verify both resources were registered
        mock_resource.assert_any_call("lunatask://tasks")
        mock_resource.assert_any_call("lunatask://tasks/{task_id}")
        expected_resource_count = 2
        assert mock_resource.call_count == expected_resource_count

    @pytest.mark.asyncio
    async def test_get_task_resource_success(self, mocker: MockerFixture) -> None:
        """Test successful single task retrieval from the resource template."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "test-session-456"

        # Create sample task data
        sample_task = TaskResponse(
            id="task-123",
            status="open",
            created_at=datetime(
                2025,
                8,
                20,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            priority=2,
            due_date=datetime(2025, 8, 25, 14, 30, 0, tzinfo=UTC),
            area_id="area-456",
            source=Source(type="manual", value="user_created"),
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        # Mock the client's get_task method
        mock_get_task = mocker.patch.object(client, "get_task", return_value=sample_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource method with task_id parameter
        result = await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        # Verify the result structure
        assert result["resource_type"] == "lunatask_task"
        assert result["task_id"] == "task-123"

        task_data = result["task"]
        assert task_data["id"] == "task-123"
        assert task_data["status"] == "open"
        expected_priority = 2
        assert task_data["priority"] == expected_priority
        assert task_data["due_date"] == "2025-08-25T14:30:00+00:00"
        assert task_data["created_at"] == "2025-08-20T10:00:00+00:00"
        assert task_data["updated_at"] == "2025-08-20T10:30:00+00:00"
        assert task_data["area_id"] == "area-456"
        assert task_data["source"]["type"] == "manual"
        assert task_data["source"]["value"] == "user_created"

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["retrieved_at"] == "test-session-456"
        assert "E2E encryption" in metadata["encrypted_fields_note"]

        # Verify context logging calls
        mock_ctx.info.assert_any_call("Retrieving task task-123 from LunaTask API")
        mock_ctx.info.assert_any_call("Successfully retrieved task task-123 from LunaTask")
        mock_get_task.assert_called_once_with("task-123")

    @pytest.mark.asyncio
    async def test_get_task_resource_minimal_data(self, mocker: MockerFixture) -> None:
        """Test single task resource with minimal task data."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task with minimal data
        minimal_task = TaskResponse(
            id="task-minimal",
            status="completed",
            created_at=datetime(
                2025,
                8,
                18,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 19, 9, 0, 0, tzinfo=UTC),
            priority=None,
            due_date=None,
            area_id=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "get_task", return_value=minimal_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_task_resource(mock_ctx, task_id="task-minimal")

        task_data = result["task"]
        assert task_data["id"] == "task-minimal"
        assert task_data["status"] == "completed"
        assert task_data["priority"] is None
        assert task_data["due_date"] is None
        assert task_data["area_id"] is None
        assert task_data["source"] is None

    @pytest.mark.asyncio
    async def test_get_task_resource_not_found_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles TaskNotFoundError (404)."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock task not found error

        not_found_error = LunaTaskNotFoundError("Task not found")
        mocker.patch.object(client, "get_task", side_effect=not_found_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the not found error
        with pytest.raises(LunaTaskNotFoundError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="nonexistent-task")

        assert exc_info.value is not_found_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Task nonexistent-task not found" in error_call_msg

    @pytest.mark.asyncio
    async def test_get_task_resource_authentication_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles authentication error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="invalid_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock authentication error
        auth_error = LunaTaskAuthenticationError("Authentication failed")
        mocker.patch.object(client, "get_task", side_effect=auth_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the authentication error
        with pytest.raises(LunaTaskAuthenticationError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is auth_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            "Failed to retrieve task task-123: Invalid or expired LunaTask API credentials"
            in error_call_msg
        )

    @pytest.mark.asyncio
    async def test_get_task_resource_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles rate limit error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock rate limit error
        rate_limit_error = LunaTaskRateLimitError("Rate limit exceeded")
        mocker.patch.object(client, "get_task", side_effect=rate_limit_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the rate limit error
        with pytest.raises(LunaTaskRateLimitError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is rate_limit_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            "Failed to retrieve task task-123: LunaTask API rate limit exceeded" in error_call_msg
        )

    @pytest.mark.asyncio
    async def test_get_task_resource_server_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles server error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock server error
        server_error = LunaTaskServerError("Internal server error", 500)
        mocker.patch.object(client, "get_task", side_effect=server_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the server error
        with pytest.raises(LunaTaskServerError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is server_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Failed to retrieve task task-123: LunaTask server error (500)" in error_call_msg

    @pytest.mark.asyncio
    async def test_get_task_resource_timeout_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles timeout error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock timeout error
        timeout_error = LunaTaskTimeoutError("Request timeout")
        mocker.patch.object(client, "get_task", side_effect=timeout_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the timeout error
        with pytest.raises(LunaTaskTimeoutError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is timeout_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            "Failed to retrieve task task-123: Request to LunaTask API timed out" in error_call_msg
        )

    @pytest.mark.asyncio
    async def test_get_task_resource_unexpected_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles unexpected errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock unexpected error
        unexpected_error = ValueError("Unexpected error")
        mocker.patch.object(client, "get_task", side_effect=unexpected_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should wrap in LunaTaskAPIError
        with pytest.raises(LunaTaskAPIError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value.__cause__ is unexpected_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Unexpected error retrieving task task-123" in error_call_msg

    @pytest.mark.asyncio
    async def test_get_task_resource_empty_task_id(self, mocker: MockerFixture) -> None:
        """Test single task resource with empty task_id parameter."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock client methods (should not be called due to early validation)
        mock_get_task = mocker.patch.object(client, "get_task")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should raise bad request error for empty task_id
        with pytest.raises(LunaTaskBadRequestError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="")

        # Verify defensive validation caught empty task_id
        assert str(exc_info.value) == "Task ID cannot be empty"
        mock_ctx.error.assert_called_once_with("Empty or invalid task_id parameter provided")

        # Client should not have been called due to early validation
        mock_get_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_task_resource_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test single task resource with special characters in task_id."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task with special characters in ID
        special_task = TaskResponse(
            id="task-with-special/chars",
            status="open",
            created_at=datetime(
                2025,
                8,
                20,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "get_task", return_value=special_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_task_resource(mock_ctx, task_id="task-with-special/chars")

        assert result["task_id"] == "task-with-special/chars"
        assert result["task"]["id"] == "task-with-special/chars"

    @pytest.mark.asyncio
    async def test_get_task_resource_handles_missing_encrypted_fields(
        self, mocker: MockerFixture
    ) -> None:
        """Test that single task resource gracefully handles absence of encrypted fields."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task without encrypted fields (as expected from E2E encryption)
        encrypted_task = TaskResponse(
            id="task-encrypted",
            status="open",
            created_at=datetime(
                2025,
                8,
                20,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
            # Note: name and note fields intentionally missing
        )

        mocker.patch.object(client, "get_task", return_value=encrypted_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_task_resource(mock_ctx, task_id="task-encrypted")

        task_data = result["task"]
        assert task_data["id"] == "task-encrypted"
        assert task_data["status"] == "open"
        # Encrypted fields should not be present
        assert "name" not in task_data
        assert "note" not in task_data

        # Metadata should note encryption
        assert "E2E encryption" in result["metadata"]["encrypted_fields_note"]


class TestEndToEndResourceValidation:
    """End-to-End validation testing for Story 2.2 Task 3.

    These tests validate complete MCP resource functionality from client perspective:
    - Resource discoverability
    - Complete resource access flow
    - MCP error response validation
    - Resource registration and URI template matching
    """

    def test_resource_discoverability_via_mcp_introspection(self, mocker: MockerFixture) -> None:
        """Test that lunatask://tasks/{task_id} resource is discoverable by MCP clients.

        Subtask 3.1: Verify resource is discoverable by MCP clients using resource listing
        """
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource registration to verify it was called correctly
        mock_resource = mocker.patch.object(mcp, "resource")

        # Initialize TaskTools to register resources
        TaskTools(mcp, client)

        # Verify both resource templates are registered and discoverable
        mock_resource.assert_any_call("lunatask://tasks")
        mock_resource.assert_any_call("lunatask://tasks/{task_id}")

        # Verify we have both resources registered
        expected_resource_count = 2
        assert mock_resource.call_count == expected_resource_count

        # Verify the resource functions were registered with correct signatures
        calls = mock_resource.call_args_list

        # Find the single task resource call
        single_task_call = None
        for call in calls:
            if call[0][0] == "lunatask://tasks/{task_id}":  # URI template
                single_task_call = call
                break

        assert single_task_call is not None, "Single task resource template not found"

        # Verify the decorator was called with correct URI template
        assert single_task_call[0][0] == "lunatask://tasks/{task_id}"

    @pytest.mark.asyncio
    async def test_complete_resource_access_flow_success(self, mocker: MockerFixture) -> None:
        """Test complete resource access flow from MCP client perspective with valid task_id.

        Subtask 3.2: Test complete resource access flow from MCP client with valid task ID
        """
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context for the resource call
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "e2e-test-session"

        # Create realistic task data that would come from LunaTask API
        test_task = TaskResponse(
            id="e2e-test-task-456",
            status="in_progress",
            created_at=datetime(
                2025,
                8,
                21,
                9,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 21, 11, 30, 0, tzinfo=UTC),
            priority=3,
            due_date=datetime(2025, 8, 28, 17, 0, 0, tzinfo=UTC),
            area_id="work-area-789",
            source=Source(type="integration", value="github_issue"),
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        # Mock the complete client flow
        mock_get_task = mocker.patch.object(client, "get_task", return_value=test_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the complete resource access flow
        result = await task_tools.get_task_resource(mock_ctx, task_id="e2e-test-task-456")

        # Validate complete MCP resource response structure
        assert isinstance(result, dict)
        assert result["resource_type"] == "lunatask_task"
        assert result["task_id"] == "e2e-test-task-456"

        # Validate task data structure and content
        task_data = result["task"]
        assert task_data["id"] == "e2e-test-task-456"
        assert task_data["status"] == "in_progress"
        expected_priority = 3
        assert task_data["priority"] == expected_priority
        assert task_data["due_date"] == "2025-08-28T17:00:00+00:00"
        assert task_data["area_id"] == "work-area-789"
        assert task_data["source"]["type"] == "integration"
        assert task_data["source"]["value"] == "github_issue"

        # Validate metadata structure
        metadata = result["metadata"]
        assert metadata["retrieved_at"] == "e2e-test-session"
        assert "E2E encryption" in metadata["encrypted_fields_note"]

        # Validate the complete call chain worked correctly
        mock_get_task.assert_called_once_with("e2e-test-task-456")
        mock_ctx.info.assert_any_call("Retrieving task e2e-test-task-456 from LunaTask API")
        mock_ctx.info.assert_any_call("Successfully retrieved task e2e-test-task-456 from LunaTask")

    @pytest.mark.asyncio
    async def test_mcp_error_response_validation_task_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """Test MCP error responses for TaskNotFoundError and other error scenarios.

        Subtask 3.3: Validate MCP error responses for TaskNotFoundError and other error scenarios
        """
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock TaskNotFoundError from client
        not_found_error = LunaTaskNotFoundError("Task not found")
        mocker.patch.object(client, "get_task", side_effect=not_found_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Verify that the error is properly propagated for MCP error handling
        with pytest.raises(LunaTaskNotFoundError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="nonexistent-task-123")

        # Validate the error is the exact same instance
        assert exc_info.value is not_found_error

        # Validate proper error logging occurred
        mock_ctx.error.assert_called_once()
        error_msg = mock_ctx.error.call_args[0][0]
        assert "Task nonexistent-task-123 not found" in error_msg

    @pytest.mark.asyncio
    async def test_mcp_error_response_validation_authentication_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test MCP error response validation for authentication errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="invalid_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock authentication error
        auth_error = LunaTaskAuthenticationError("Authentication failed")
        mocker.patch.object(client, "get_task", side_effect=auth_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Verify proper error propagation
        with pytest.raises(LunaTaskAuthenticationError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="test-task-999")

        assert exc_info.value is auth_error
        mock_ctx.error.assert_called_once()
        error_msg = mock_ctx.error.call_args[0][0]
        assert "Invalid or expired LunaTask API credentials" in error_msg

    @pytest.mark.asyncio
    async def test_mcp_error_response_validation_rate_limit_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test MCP error response validation for rate limit errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock rate limit error
        rate_limit_error = LunaTaskRateLimitError("Rate limit exceeded")
        mocker.patch.object(client, "get_task", side_effect=rate_limit_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Verify proper error propagation
        with pytest.raises(LunaTaskRateLimitError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="test-task-888")

        assert exc_info.value is rate_limit_error
        mock_ctx.error.assert_called_once()
        error_msg = mock_ctx.error.call_args[0][0]
        assert "LunaTask API rate limit exceeded" in error_msg

    def test_resource_registration_and_uri_template_matching(self, mocker: MockerFixture) -> None:
        """Test resource registration and proper URI template matching in running server.

        Subtask 3.4: Confirm resource registration and proper URI template matching in server
        """
        # Create the FastMCP instance and configuration as would happen in real server
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="production_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource decorator to capture registration details
        mock_resource_decorator = mocker.patch.object(mcp, "resource")

        # Initialize TaskTools as would happen in the actual server
        task_tools = TaskTools(mcp, client)

        # Verify that both resource templates were registered with correct URI patterns
        mock_resource_decorator.assert_any_call("lunatask://tasks")
        mock_resource_decorator.assert_any_call("lunatask://tasks/{task_id}")

        # Verify the correct number of resource registrations
        expected_resource_count = 2
        assert mock_resource_decorator.call_count == expected_resource_count

        # Verify that TaskTools instance maintains references correctly
        assert task_tools.mcp is mcp
        assert task_tools.lunatask_client is client

        # Verify the URI template pattern for single task resource
        single_task_calls = [
            call
            for call in mock_resource_decorator.call_args_list
            if call[0][0] == "lunatask://tasks/{task_id}"
        ]
        assert len(single_task_calls) == 1, (
            "Single task resource template should be registered exactly once"
        )

        # Validate URI template format matches MCP specification
        uri_template = single_task_calls[0][0][0]
        assert uri_template == "lunatask://tasks/{task_id}"
        assert "{task_id}" in uri_template
        assert uri_template.startswith("lunatask://")

    @pytest.mark.asyncio
    async def test_end_to_end_parameter_extraction_validation(self, mocker: MockerFixture) -> None:
        """Test that URI template parameter extraction works correctly end-to-end."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Create test task with a complex ID that tests parameter extraction
        test_task_id = "complex-task-id-with-dashes-123"
        test_task = TaskResponse(
            id=test_task_id,
            status="open",
            created_at=datetime(
                2025,
                8,
                21,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            priority=None,
            due_date=None,
            area_id=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mock_get_task = mocker.patch.object(client, "get_task", return_value=test_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource with the complex task ID
        result = await task_tools.get_task_resource(mock_ctx, task_id=test_task_id)

        # Verify parameter was extracted and passed correctly
        mock_get_task.assert_called_once_with(test_task_id)

        # Verify the response contains the correct task ID
        assert result["task_id"] == test_task_id
        assert result["task"]["id"] == test_task_id

    @pytest.mark.asyncio
    async def test_end_to_end_encrypted_fields_handling_validation(
        self, mocker: MockerFixture
    ) -> None:
        """Test end-to-end validation that encrypted fields are handled correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Create task that simulates E2E encryption (missing name/note fields)
        encrypted_task = TaskResponse(
            id="encrypted-task-e2e",
            status="open",
            created_at=datetime(
                2025,
                8,
                21,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            priority=1,
            due_date=datetime(2025, 8, 30, 16, 0, 0, tzinfo=UTC),
            area_id="secure-area",
            source=Source(type="secure", value="encrypted_source"),
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
            # Importantly: name and note fields are not present due to E2E encryption
        )

        mocker.patch.object(client, "get_task", return_value=encrypted_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the complete flow
        result = await task_tools.get_task_resource(mock_ctx, task_id="encrypted-task-e2e")

        # Validate that encrypted fields are properly absent
        task_data = result["task"]
        assert "name" not in task_data
        assert "note" not in task_data

        # Validate that other fields are present
        assert task_data["id"] == "encrypted-task-e2e"
        assert task_data["status"] == "open"
        assert task_data["priority"] == 1
        assert task_data["area_id"] == "secure-area"

        # Validate metadata indicates encryption
        assert "E2E encryption" in result["metadata"]["encrypted_fields_note"]


class TestCreateTaskTool:
    """Test suite for create_task MCP tool implementation."""

    @pytest.mark.asyncio
    async def test_create_task_tool_success_minimal_data(self, mocker: MockerFixture) -> None:
        """Test successful task creation with minimal required data."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task creation response
        created_task = TaskResponse(
            id="new-task-123",
            status="open",
            created_at=datetime(
                2025,
                8,
                21,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "create_task", return_value=created_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task")

        # Verify the result contains the task ID
        assert result["success"] is True
        assert result["task_id"] == "new-task-123"
        assert result["message"] == "Task created successfully"

        # Verify the client was called with correct data
        client.create_task.assert_called_once()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object
        call_args = client.create_task.call_args[0][0]  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        assert isinstance(call_args, TaskCreate)
        assert call_args.name == "Test Task"

    @pytest.mark.asyncio
    async def test_create_task_tool_success_full_data(self, mocker: MockerFixture) -> None:
        """Test successful task creation with all optional parameters."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task creation response
        created_task = TaskResponse(
            id="full-task-456",
            area_id="area-123",
            status="open",
            priority=1,
            created_at=datetime(
                2025,
                8,
                21,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            due_date=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "create_task", return_value=created_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool with all parameters
        result = await task_tools.create_task_tool(
            mock_ctx,
            name="Full Test Task",
            note="These are test note",
            area_id="area-123",
            status="open",
            priority=1,
        )

        # Verify the result
        assert result["success"] is True
        assert result["task_id"] == "full-task-456"
        assert result["message"] == "Task created successfully"

        # Verify the client was called with correct data
        client.create_task.assert_called_once()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object
        call_args = client.create_task.call_args[0][0]  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        assert isinstance(call_args, TaskCreate)
        assert call_args.name == "Full Test Task"
        assert call_args.note == "These are test note"
        assert call_args.area_id == "area-123"
        assert call_args.status == "open"
        assert call_args.priority == 1

    @pytest.mark.asyncio
    async def test_create_task_tool_validation_error_422(self, mocker: MockerFixture) -> None:
        """Test create_task tool handles validation errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock validation error from client
        mocker.patch.object(
            client, "create_task", side_effect=LunaTaskValidationError("Task name is required")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool
        result = await task_tools.create_task_tool(mock_ctx, name="")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Task name is required" in result["message"]

    @pytest.mark.asyncio
    async def test_create_task_tool_subscription_required_error_402(
        self, mocker: MockerFixture
    ) -> None:
        """Test create_task tool handles subscription required errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock subscription required error from client
        mocker.patch.object(
            client,
            "create_task",
            side_effect=LunaTaskSubscriptionRequiredError("Free plan limit reached"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "subscription_required"
        assert "Free plan limit reached" in result["message"]

    @pytest.mark.asyncio
    async def test_create_task_tool_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test create_task tool handles authentication errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="invalid_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock authentication error from client
        mocker.patch.object(
            client, "create_task", side_effect=LunaTaskAuthenticationError("Invalid bearer token")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "authentication_error"
        assert "Invalid bearer token" in result["message"]

    @pytest.mark.asyncio
    async def test_create_task_tool_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test create_task tool handles rate limit errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock rate limit error from client
        mocker.patch.object(
            client, "create_task", side_effect=LunaTaskRateLimitError("Rate limit exceeded")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "rate_limit_error"
        assert "Rate limit exceeded" in result["message"]

    @pytest.mark.asyncio
    async def test_create_task_tool_server_error_500(self, mocker: MockerFixture) -> None:
        """Test create_task tool handles server errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock server error from client
        mocker.patch.object(
            client, "create_task", side_effect=LunaTaskServerError("Internal server error")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "server_error"
        assert "Internal server error" in result["message"]

    @pytest.mark.asyncio
    async def test_create_task_tool_generic_api_error(self, mocker: MockerFixture) -> None:
        """Test create_task tool handles generic API errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock generic API error from client
        mocker.patch.object(
            client, "create_task", side_effect=LunaTaskAPIError("Generic API error")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "Generic API error" in result["message"]

    @pytest.mark.asyncio
    async def test_create_task_tool_parameter_validation(self, mocker: MockerFixture) -> None:
        """Test create_task tool with various parameter combinations."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task creation response
        created_task = TaskResponse(
            id="param-test-789",
            status="open",
            created_at=datetime(
                2025,
                8,
                21,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "create_task", return_value=created_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test with only name (required parameter)
        result = await task_tools.create_task_tool(mock_ctx, name="Required Only")
        assert result["success"] is True

        # Reset mock to check next call
        client.create_task.reset_mock()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object

        # Test with optional parameters as None (should be excluded)
        result = await task_tools.create_task_tool(
            mock_ctx, name="Test with Nones", note=None, area_id=None, priority=None
        )
        assert result["success"] is True

        # Verify None values are properly handled
        call_args = client.create_task.call_args[0][0]  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        assert call_args.name == "Test with Nones"  # type: ignore[attr-defined] # TaskCreate field access on mock call args


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
        created_task = TaskResponse(
            id="e2e-task-123",
            status="open",
            created_at=datetime(
                2025,
                8,
                22,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 22, 10, 0, 0, tzinfo=UTC),
            area_id="work-area",
            priority=3,
            due_date=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
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
            status="open",
            priority=3,
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
        assert call_args.status == "open"  # type: ignore[attr-defined] # TaskCreate field access on mock call args
        expected_priority = 3
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


class TestUpdateTaskTool:
    """Test suite for update_task MCP tool implementation."""

    @pytest.mark.asyncio
    async def test_update_task_tool_success_single_field(self, mocker: MockerFixture) -> None:
        """Test successful task update with single field change."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task update response
        updated_task = TaskResponse(
            id="update-task-123",
            status="completed",  # Changed from open to completed
            created_at=datetime(
                2025,
                8,
                21,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 22, 14, 30, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=None,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "update_task", return_value=updated_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the update_task tool with single field update
        result = await task_tools.update_task_tool(
            mock_ctx, id="update-task-123", status="completed"
        )

        # Verify the result structure
        assert result["success"] is True
        assert result["task_id"] == "update-task-123"
        assert result["message"] == "Task updated successfully"
        assert "task" in result

        # Verify task data structure
        task_data = result["task"]
        assert task_data["id"] == "update-task-123"
        assert task_data["status"] == "completed"
        assert task_data["updated_at"] == "2025-08-22T14:30:00+00:00"

        # Verify the client was called correctly
        # Mock object dynamically added by pytest-mock, hence type ignore needed
        mock_update_task = client.update_task  # type: ignore[attr-defined]
        # Mock method added by pytest-mock, type system doesn't recognize it
        mock_update_task.assert_called_once()  # type: ignore[attr-defined]

        # Verify call arguments using assert_called_with for type safety
        expected_update = TaskUpdate(
            name=None,
            note=None,
            area_id=None,
            status="completed",
            priority=None,
            due_date=None,
        )
        # Mock method added by pytest-mock, type system doesn't recognize it
        mock_update_task.assert_called_with("update-task-123", expected_update)  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_task_tool_due_date_parsing_valid_iso_8601(
        self, mocker: MockerFixture
    ) -> None:
        """Test update_task tool correctly parses valid ISO 8601 due_date strings."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task update response
        expected_due_date = datetime(2025, 12, 25, 14, 30, 0, tzinfo=UTC)
        updated_task = TaskResponse(
            id="date-task-789",
            status="later",
            created_at=datetime(
                2025,
                8,
                21,
                10,
                0,
                0,
                tzinfo=UTC,
            ),
            updated_at=datetime(2025, 8, 22, 15, 30, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=expected_due_date,
            source=None,
            goal_id=None,
            estimate=None,
            motivation=None,
            eisenhower=None,
            previous_status=None,
            progress=None,
            scheduled_on=None,
            completed_at=None,
        )

        mocker.patch.object(client, "update_task", return_value=updated_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test with valid ISO 8601 string
        result = await task_tools.update_task_tool(
            mock_ctx,
            id="date-task-789",
            due_date="2025-12-25T14:30:00+00:00",
        )

        # Verify successful parsing and update
        assert result["success"] is True
        assert result["task"]["due_date"] == "2025-12-25T14:30:00+00:00"

        # Verify the parsed datetime was passed correctly to client
        # Mock object dynamically added by pytest-mock, hence type ignore needed
        mock_update_task = client.update_task  # type: ignore[attr-defined]
        expected_update = TaskUpdate(
            name=None,
            note=None,
            area_id=None,
            status=None,
            priority=None,
            due_date=expected_due_date,
        )
        # Mock method added by pytest-mock, type system doesn't recognize it
        mock_update_task.assert_called_with("date-task-789", expected_update)  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_task_tool_due_date_parsing_invalid_format(
        self, mocker: MockerFixture
    ) -> None:
        """Test update_task tool handles invalid due_date format correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock client methods (should not be called due to validation error)
        mock_update = mocker.patch.object(client, "update_task")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test with invalid date format
        result = await task_tools.update_task_tool(
            mock_ctx,
            id="date-task-invalid",
            due_date="invalid-date-format",
        )

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid due_date format" in result["message"]

        # Verify client was not called due to validation error
        mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_tool_task_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test update_task tool handles TaskNotFoundError correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock task not found error from client
        mocker.patch.object(
            client, "update_task", side_effect=LunaTaskNotFoundError("Task not found")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the update_task tool
        result = await task_tools.update_task_tool(
            mock_ctx, id="nonexistent-task", status="completed"
        )

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "not_found_error"
        assert "Task not found" in result["message"]

    @pytest.mark.asyncio
    async def test_update_task_tool_validation_error_400(self, mocker: MockerFixture) -> None:
        """Test update_task tool handles validation errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock validation error from client
        mocker.patch.object(
            client, "update_task", side_effect=LunaTaskValidationError("Invalid status value")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the update_task tool
        result = await task_tools.update_task_tool(
            mock_ctx, id="validation-task", status="invalid_status"
        )

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid status value" in result["message"]

    @pytest.mark.asyncio
    async def test_update_task_tool_empty_task_id_validation(self, mocker: MockerFixture) -> None:
        """Test update_task tool validates empty task_id parameter."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock client methods (should not be called due to validation error)
        mock_update = mocker.patch.object(client, "update_task")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test with empty task_id
        result = await task_tools.update_task_tool(mock_ctx, id="", status="completed")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Task ID cannot be empty" in result["message"]

        # Verify client was not called due to validation error
        mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_tool_no_fields_to_update_validation(
        self, mocker: MockerFixture
    ) -> None:
        """Test update_task tool validates that at least one field is provided for update."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock client methods (should not be called due to validation error)
        mock_update = mocker.patch.object(client, "update_task")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test with only id parameter (no fields to update)
        result = await task_tools.update_task_tool(mock_ctx, id="no-fields-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "At least one field must be provided for update" in result["message"]

        # Verify client was not called due to validation error
        mock_update.assert_not_called()


class TestDeleteTaskTool:
    """Test suite for TaskTools.delete_task_tool() method."""

    @pytest.mark.asyncio
    async def test_delete_task_tool_success(self, mocker: MockerFixture) -> None:
        """Test successful task deletion."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock successful deletion
        client_mock = mocker.patch.object(client, "delete_task", return_value=True)

        result = await task_tools.delete_task_tool(mock_ctx, id="delete-task-123")

        # Verify the result structure
        assert result["success"] is True
        assert result["task_id"] == "delete-task-123"
        assert result["message"] == "Task deleted successfully"

        # Verify client was called
        client_mock.assert_called_once_with("delete-task-123")

    @pytest.mark.asyncio
    async def test_delete_task_tool_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles TaskNotFoundError correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock task not found error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskNotFoundError("Task not found")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="nonexistent-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "not_found_error"
        assert "Task not found" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles authentication errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="invalid_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock authentication error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskAuthenticationError("Invalid bearer token")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="auth-task-123")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "authentication_error"
        assert "Invalid bearer token" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles rate limit errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock rate limit error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskRateLimitError("Rate limit exceeded")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="rate-limited-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "rate_limit_error"
        assert "Rate limit exceeded" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_server_error_500(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles server errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock server error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskServerError("Internal server error")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="server-error-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "server_error"
        assert "Internal server error" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_timeout_error(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles timeout errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock timeout error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskTimeoutError("Request timeout")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="timeout-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "timeout_error"
        assert "Request timeout" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_generic_api_error(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles generic API errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock generic API error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskAPIError("Generic API error")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="api-error-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "Generic API error" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_empty_task_id_validation(self, mocker: MockerFixture) -> None:
        """Test delete_task tool validates empty task_id parameter."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock client method (should not be called)
        client_mock = mocker.patch.object(client, "delete_task")

        result = await task_tools.delete_task_tool(mock_ctx, id="")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Task ID cannot be empty" in result["message"]

        # Verify client was not called due to validation error
        client_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_task_tool_whitespace_only_task_id_validation(
        self, mocker: MockerFixture
    ) -> None:
        """Test delete_task tool validates whitespace-only task_id parameter."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock client method (should not be called)
        client_mock = mocker.patch.object(client, "delete_task")

        result = await task_tools.delete_task_tool(mock_ctx, id="   ")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Task ID cannot be empty" in result["message"]

        # Verify client was not called due to validation error
        client_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_task_tool_unexpected_error(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles unexpected errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock unexpected error
        mocker.patch.object(client, "delete_task", side_effect=Exception("Unexpected error"))

        result = await task_tools.delete_task_tool(mock_ctx, id="unexpected-error-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "unexpected_error"
        assert "Unexpected error" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_non_idempotent_behavior(self, mocker: MockerFixture) -> None:
        """Test delete_task tool non-idempotent behavior - second delete returns error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        task_id = "already-deleted-task"

        # First call succeeds
        mocker.patch.object(client, "delete_task", return_value=True)

        result = await task_tools.delete_task_tool(mock_ctx, id=task_id)
        assert result["success"] is True

        # Second call fails with not found error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskNotFoundError("Task not found")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id=task_id)
        assert result["success"] is False
        assert result["error"] == "not_found_error"
