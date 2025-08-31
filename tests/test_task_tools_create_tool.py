"""Tests for TaskTools create task tool implementation.

This module contains tests for the TaskTools class that provides
MCP tool for creating LunaTask tasks.
"""

from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import TaskCreate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


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

        created_task = create_task_response(
            task_id="new-task-123",
            status="open",
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
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
        created_task = create_task_response(
            task_id="full-task-456",
            area_id="area-123",
            status="open",
            priority=1,
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
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
            status="started",
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
        assert call_args.status == "started"
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
        created_task = create_task_response(
            task_id="param-test-789",
            status="open",
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
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
            mock_ctx, name="Test with Nones", note=None, area_id=None
        )
        assert result["success"] is True

        # Verify None values are properly handled
        call_args = client.create_task.call_args[0][0]  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        assert call_args.name == "Test with Nones"  # type: ignore[attr-defined] # TaskCreate field access on mock call args

    @pytest.mark.asyncio
    async def test_create_task_tool_accepts_motivation_field(self, mocker: MockerFixture) -> None:
        """Test create_task tool accepts and forwards motivation field."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task creation response
        created_task = create_task_response(
            task_id="task-with-motivation",
            status="later",
            created_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
            motivation="must",
        )

        mocker.patch.object(client, "create_task", return_value=created_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool with motivation
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task", motivation="must")

        # Verify success
        assert result["success"] is True
        assert result["task_id"] == "task-with-motivation"

        # Verify the client was called with motivation field
        client.create_task.assert_called_once()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object
        call_args = client.create_task.call_args[0][0]  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        assert isinstance(call_args, TaskCreate)
        assert call_args.name == "Test Task"
        assert call_args.motivation == "must"

    @pytest.mark.asyncio
    async def test_create_task_tool_accepts_eisenhower_field(self, mocker: MockerFixture) -> None:
        """Test create_task tool accepts and forwards eisenhower field."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task creation response
        created_task = create_task_response(
            task_id="task-with-eisenhower",
            status="later",
            created_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
            eisenhower=2,
        )

        mocker.patch.object(client, "create_task", return_value=created_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the create_task tool with eisenhower
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task", eisenhower=2)

        # Verify success
        assert result["success"] is True
        assert result["task_id"] == "task-with-eisenhower"

        # Verify the client was called with eisenhower field
        client.create_task.assert_called_once()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object
        call_args = client.create_task.call_args[0][0]  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        assert isinstance(call_args, TaskCreate)
        assert call_args.name == "Test Task"
        expected_eisenhower = 2
        assert call_args.eisenhower == expected_eisenhower

    @pytest.mark.asyncio
    async def test_create_task_tool_invalid_motivation_enum_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test create_task tool returns structured MCP error for invalid motivation enum."""
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
            client, "create_task", side_effect=LunaTaskValidationError("Invalid motivation value")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute with invalid motivation enum - this should fail with Pydantic validation error
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task", motivation="invalid")

        # Verify structured MCP error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid motivation value" in result["message"]

    @pytest.mark.asyncio
    async def test_create_task_tool_invalid_eisenhower_range_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test create_task tool returns structured MCP error for invalid eisenhower range."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Execute with invalid eisenhower range - this should fail with Pydantic validation error
        result = await task_tools.create_task_tool(mock_ctx, name="Test Task", eisenhower=5)

        # Verify structured MCP error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "eisenhower" in result["message"]
        assert "between 0 and 4" in result["message"]
