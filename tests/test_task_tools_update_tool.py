"""Tests for TaskTools update task tool implementation.

This module contains tests for the TaskTools class that provides
MCP tool for updating LunaTask tasks.
"""

from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskNotFoundError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import (
    MAX_EISENHOWER,
    TaskUpdate,
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


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
        updated_task = create_task_response(
            task_id="update-task-123",
            status="completed",  # Changed from open to completed
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 22, 14, 30, 0, tzinfo=UTC),
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
        mock_update_task = client.update_task  # type: ignore[attr-defined] # Mock method reference added by mocker.patch.object
        # Mock method added by pytest-mock, type system doesn't recognize it
        mock_update_task.assert_called_once()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object

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
        mock_update_task.assert_called_with("update-task-123", expected_update)  # type: ignore[attr-defined] # Mock method added by mocker.patch.object

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
        updated_task = create_task_response(
            task_id="date-task-789",
            status="later",
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 22, 15, 30, 0, tzinfo=UTC),
            due_date=expected_due_date,
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
        mock_update_task = client.update_task  # type: ignore[attr-defined] # Mock method reference added by mocker.patch.object
        expected_update = TaskUpdate(
            name=None,
            note=None,
            area_id=None,
            status=None,
            priority=None,
            due_date=expected_due_date,
        )
        # Mock method added by pytest-mock, type system doesn't recognize it
        mock_update_task.assert_called_with("date-task-789", expected_update)  # type: ignore[attr-defined] # Mock method added by mocker.patch.object

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
        result = await task_tools.update_task_tool(mock_ctx, id="validation-task", status="started")

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

    @pytest.mark.asyncio
    async def test_update_task_tool_accepts_motivation_field(self, mocker: MockerFixture) -> None:
        """Test update_task tool accepts and forwards motivation field."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task update response
        updated_task = create_task_response(
            task_id="task-456",
            status="started",
            created_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 26, 11, 0, 0, tzinfo=UTC),
            motivation="must",
        )

        mocker.patch.object(client, "update_task", return_value=updated_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the update_task tool with motivation
        result = await task_tools.update_task_tool(mock_ctx, id="task-456", motivation="must")

        # Verify success
        assert result["success"] is True
        assert result["task_id"] == "task-456"

        # Verify the client was called with motivation field
        client.update_task.assert_called_once()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object
        call_args = client.update_task.call_args  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        task_update: TaskUpdate = call_args[0][1]  # type: ignore[misc] # Type annotation for test clarity, call_args is dynamic mock data
        assert isinstance(task_update, TaskUpdate)
        assert task_update.motivation == "must"

    @pytest.mark.asyncio
    async def test_update_task_tool_accepts_eisenhower_field(self, mocker: MockerFixture) -> None:
        """Test update_task tool accepts and forwards eisenhower field."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock successful task update response
        updated_task = create_task_response(
            task_id="task-789",
            status="next",
            created_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 26, 11, 0, 0, tzinfo=UTC),
            eisenhower=MAX_EISENHOWER - 1,
        )

        mocker.patch.object(client, "update_task", return_value=updated_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the update_task tool with eisenhower
        result = await task_tools.update_task_tool(
            mock_ctx, id="task-789", eisenhower=MAX_EISENHOWER - 1
        )

        # Verify success
        assert result["success"] is True
        assert result["task_id"] == "task-789"

        # Verify the client was called with eisenhower field
        client.update_task.assert_called_once()  # type: ignore[attr-defined] # Mock method added by mocker.patch.object
        call_args = client.update_task.call_args  # type: ignore[attr-defined] # Mock attribute added by mocker.patch.object
        task_update: TaskUpdate = call_args[0][1]  # type: ignore[misc] # Type annotation for test clarity, call_args is dynamic mock data
        assert isinstance(task_update, TaskUpdate)
        assert task_update.eisenhower == MAX_EISENHOWER - 1

    @pytest.mark.asyncio
    async def test_update_task_tool_invalid_motivation_enum_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test update_task tool returns structured MCP error for invalid motivation enum."""
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
            client, "update_task", side_effect=LunaTaskValidationError("Invalid motivation value")
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute with invalid motivation enum - this should fail with Pydantic validation error
        result = await task_tools.update_task_tool(mock_ctx, id="task-123", motivation="invalid")

        # Verify structured MCP error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid motivation value" in result["message"]

    @pytest.mark.asyncio
    async def test_update_task_tool_invalid_eisenhower_range_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test update_task tool returns structured MCP error for invalid eisenhower range."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Execute with invalid eisenhower range - this should fail with Pydantic validation error
        result = await task_tools.update_task_tool(mock_ctx, id="task-123", eisenhower=-1)

        # Verify structured MCP error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "eisenhower" in result["message"]
        assert "between 0 and 4" in result["message"]
