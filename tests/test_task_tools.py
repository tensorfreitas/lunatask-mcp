"""Tests for TaskTools MCP resource implementation.

This module contains tests for the TaskTools class that provides
MCP resources for LunaTask integration.
"""

from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskAPIError
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
        """Test that TaskTools registers the lunatask://tasks resource."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource registration
        mock_resource = mocker.patch.object(mcp, "resource")

        TaskTools(mcp, client)

        # Verify resource was registered with correct URI
        mock_resource.assert_called_once_with("lunatask://tasks")


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
