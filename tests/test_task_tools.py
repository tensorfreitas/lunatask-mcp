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
    LunaTaskTimeoutError,
)
from lunatask_mcp.api.models import Source, TaskResponse
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
        """Test that TaskTools registers both lunatask://tasks resources."""
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
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            priority=1,
            due_date=datetime(2025, 8, 25, 18, 0, 0, tzinfo=UTC),
            area_id="area-1",
            source=Source(type="manual", value="user_created"),
            tags=["work", "urgent"],
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
        assert task_data["tags"] == ["work", "urgent"]

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
            created_at=datetime(2025, 8, 18, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 19, 9, 0, 0, tzinfo=UTC),
            priority=None,
            due_date=None,
            area_id=None,
            source=None,
            tags=[],
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
        assert task_data["tags"] == []


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
        mock_make_request = mocker.patch.object(client, "make_request", return_value=[])

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
        mock_make_request = mocker.patch.object(client, "make_request", return_value=[])

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
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            priority=2,
            due_date=datetime(2025, 8, 25, 14, 30, 0, tzinfo=UTC),
            area_id="area-456",
            source=Source(type="manual", value="user_created"),
            tags=["work", "important"],
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
        assert task_data["tags"] == ["work", "important"]

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
            created_at=datetime(2025, 8, 18, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 19, 9, 0, 0, tzinfo=UTC),
            priority=None,
            due_date=None,
            area_id=None,
            source=None,
            tags=[],
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
        assert task_data["tags"] == []

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
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=None,
            source=None,
            tags=[],
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
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            area_id=None,
            priority=None,
            due_date=None,
            source=None,
            tags=[],
            # Note: name and notes fields intentionally missing
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
        assert "notes" not in task_data

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
            created_at=datetime(2025, 8, 21, 9, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 11, 30, 0, tzinfo=UTC),
            priority=3,
            due_date=datetime(2025, 8, 28, 17, 0, 0, tzinfo=UTC),
            area_id="work-area-789",
            source=Source(type="integration", value="github_issue"),
            tags=["bug-fix", "high-priority", "backend"],
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
        assert task_data["tags"] == ["bug-fix", "high-priority", "backend"]

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
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            priority=None,
            due_date=None,
            area_id=None,
            source=None,
            tags=[],
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

        # Create task that simulates E2E encryption (missing name/notes fields)
        encrypted_task = TaskResponse(
            id="encrypted-task-e2e",
            status="open",
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            priority=1,
            due_date=datetime(2025, 8, 30, 16, 0, 0, tzinfo=UTC),
            area_id="secure-area",
            source=Source(type="secure", value="encrypted_source"),
            tags=["confidential"],
            # Importantly: name and notes fields are not present due to E2E encryption
        )

        mocker.patch.object(client, "get_task", return_value=encrypted_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the complete flow
        result = await task_tools.get_task_resource(mock_ctx, task_id="encrypted-task-e2e")

        # Validate that encrypted fields are properly absent
        task_data = result["task"]
        assert "name" not in task_data
        assert "notes" not in task_data

        # Validate that other fields are present
        assert task_data["id"] == "encrypted-task-e2e"
        assert task_data["status"] == "open"
        assert task_data["priority"] == 1
        assert task_data["area_id"] == "secure-area"
        assert task_data["tags"] == ["confidential"]

        # Validate metadata indicates encryption
        assert "E2E encryption" in result["metadata"]["encrypted_fields_note"]
