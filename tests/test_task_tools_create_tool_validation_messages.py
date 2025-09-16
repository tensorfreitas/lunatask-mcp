"""Additional tests for create_task tool error handling and messages.

This module focuses on improving coverage for validation error message mapping
and the unexpected error fallback path in `tasks_create.create_task_tool`.
"""

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


class FakeValidationError(Exception):
    """Lightweight stand-in mimicking Pydantic's ValidationError shape for tests."""

    def __init__(self, errors: list[dict[str, object]]) -> None:
        # No message needed; the tool formats messages from `errors()`
        super().__init__("validation failed")
        self._errors = errors

    def errors(self) -> list[dict[str, object]]:
        return self._errors


@pytest.mark.asyncio
async def test_create_task_tool_pydantic_error_message_mapping(mocker: MockerFixture) -> None:
    """Map Pydantic-style errors to friendly field messages (motivation/priority/status)."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)
    task_tools = TaskTools(mcp, client)

    mock_ctx = mocker.AsyncMock()

    # Simulate a Pydantic ValidationError-like exception from the client call
    fake_err = FakeValidationError(
        [
            {"loc": ["motivation"], "msg": "invalid value"},
            {"loc": ["priority"], "msg": "out of range"},
            {"loc": ["status"], "msg": "invalid value"},
        ]
    )

    mocker.patch.object(client, "create_task", side_effect=fake_err)
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    # Execute: should format custom messages per field using mapping in the tool
    result = await task_tools.create_task_tool(
        mock_ctx,
        name="Test Task",
        area_id="test-area-id",
        status="invalid-status",  # gets coerced, but error is raised by client
        motivation="invalid-motivation",  # coerced, message mapping still applied
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"

    # Verify friendly messages are present for each field
    msg = result["message"]
    assert "motivation: Must be one of: must, should, want, unknown" in msg
    assert "priority: Must be between -2 and 2" in msg
    assert "status: Must be one of: later, next, started, waiting, completed" in msg


@pytest.mark.asyncio
async def test_create_task_tool_unexpected_error_fallback(mocker: MockerFixture) -> None:
    """Return unexpected_error when an unknown exception bubbles up from the client."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)
    task_tools = TaskTools(mcp, client)

    mock_ctx = mocker.AsyncMock()

    mocker.patch.object(client, "create_task", side_effect=RuntimeError("Boom!"))
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await task_tools.create_task_tool(mock_ctx, name="Test Task", area_id="test-area-id")

    assert result["success"] is False
    assert result["error"] == "unexpected_error"
    assert result["message"] == "Unexpected error creating task: Boom!"


@pytest.mark.asyncio
async def test_create_task_tool_invalid_priority_type_error(
    mocker: MockerFixture,
) -> None:
    """Return structured error when priority cannot be coerced to int."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)
    task_tools = TaskTools(mcp, client)

    mock_ctx = mocker.AsyncMock()

    result = await task_tools.create_task_tool(
        mock_ctx, name="Test Task", area_id="test-area-id", priority="high"
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "priority" in result["message"]
    assert "integer between -2 and 2" in result["message"]


@pytest.mark.asyncio
async def test_create_task_tool_invalid_eisenhower_type_error(
    mocker: MockerFixture,
) -> None:
    """Return structured error when eisenhower cannot be coerced to int."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)
    task_tools = TaskTools(mcp, client)

    mock_ctx = mocker.AsyncMock()

    result = await task_tools.create_task_tool(
        mock_ctx, name="Test Task", area_id="test-area-id", eisenhower="urgent"
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "eisenhower" in result["message"]
    assert "integer between 0 and 4" in result["message"]
