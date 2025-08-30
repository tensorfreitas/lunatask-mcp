"""Additional error handling tests for TaskTools update task tool."""

from typing import Any

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
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


class FakeValidationError(Exception):
    """Simple exception mimicking Pydantic's ValidationError."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("validation error")
        self._errors = errors

    def errors(self) -> list[dict[str, Any]]:
        """Return stored validation errors."""
        return self._errors


@pytest.fixture
def setup_tools(mocker: MockerFixture) -> tuple[TaskTools, LunaTaskClient, Any]:
    """Provide initialized TaskTools, client, and mock context."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)
    task_tools = TaskTools(mcp, client)
    ctx = mocker.AsyncMock()
    return task_tools, client, ctx


@pytest.mark.asyncio
async def test_update_task_tool_authentication_error(
    setup_tools: tuple[TaskTools, LunaTaskClient, Any], mocker: MockerFixture
) -> None:
    """Tool returns structured error when authentication fails."""
    task_tools, client, ctx = setup_tools
    mocker.patch.object(client, "update_task", side_effect=LunaTaskAuthenticationError("bad token"))
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await task_tools.update_task_tool(ctx, id="task-1", status="next")

    assert result["success"] is False
    assert result["error"] == "authentication_error"
    assert "Authentication failed" in result["message"]


@pytest.mark.asyncio
async def test_update_task_tool_rate_limit_error(
    setup_tools: tuple[TaskTools, LunaTaskClient, Any], mocker: MockerFixture
) -> None:
    """Tool surfaces rate limit errors from the API."""
    task_tools, client, ctx = setup_tools
    mocker.patch.object(client, "update_task", side_effect=LunaTaskRateLimitError("slow down"))
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await task_tools.update_task_tool(ctx, id="task-1", status="next")

    assert result["success"] is False
    assert result["error"] == "rate_limit_error"
    assert "Rate limit exceeded" in result["message"]


@pytest.mark.asyncio
async def test_update_task_tool_server_error(
    setup_tools: tuple[TaskTools, LunaTaskClient, Any], mocker: MockerFixture
) -> None:
    """Tool handles server errors gracefully."""
    task_tools, client, ctx = setup_tools
    mocker.patch.object(client, "update_task", side_effect=LunaTaskServerError("boom"))
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await task_tools.update_task_tool(ctx, id="task-1", status="next")

    assert result["success"] is False
    assert result["error"] == "server_error"
    assert "Server error" in result["message"]


@pytest.mark.asyncio
async def test_update_task_tool_api_error(
    setup_tools: tuple[TaskTools, LunaTaskClient, Any], mocker: MockerFixture
) -> None:
    """Tool surfaces unexpected API errors."""
    task_tools, client, ctx = setup_tools
    mocker.patch.object(client, "update_task", side_effect=LunaTaskAPIError("oops"))
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await task_tools.update_task_tool(ctx, id="task-1", status="next")

    assert result["success"] is False
    assert result["error"] == "api_error"
    assert "API error" in result["message"]


@pytest.mark.asyncio
async def test_update_task_tool_priority_validation_error(
    setup_tools: tuple[TaskTools, LunaTaskClient, Any], mocker: MockerFixture
) -> None:
    """Invalid priority values return detailed validation errors."""
    task_tools, client, ctx = setup_tools
    mock_update = mocker.patch.object(client, "update_task")

    result = await task_tools.update_task_tool(ctx, id="task-1", priority=5)

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "priority" in result["message"]
    assert "-2 and 2" in result["message"]
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_tool_custom_validation_messages(
    setup_tools: tuple[TaskTools, LunaTaskClient, Any], mocker: MockerFixture
) -> None:
    """Custom validation messages are returned for status and motivation."""
    task_tools, client, ctx = setup_tools

    def raise_error(*args: object, **kwargs: object) -> None:  # noqa: ARG001 - required by patch
        raise FakeValidationError(
            [
                {"loc": ("status",), "msg": "invalid"},
                {"loc": ("motivation",), "msg": "invalid"},
            ]
        )

    mocker.patch("lunatask_mcp.tools.tasks_update.TaskUpdate", side_effect=raise_error)
    mock_update = mocker.patch.object(client, "update_task")

    result = await task_tools.update_task_tool(ctx, id="task-1", status="bad", motivation="worse")

    assert result["success"] is False
    assert result["error"] == "validation_error"
    msg = result["message"]
    assert "status: Must be one of: later, next, started, waiting, completed" in msg
    assert "motivation: Must be one of: must, should, want, unknown" in msg
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_tool_unexpected_error(
    setup_tools: tuple[TaskTools, LunaTaskClient, Any], mocker: MockerFixture
) -> None:
    """Unexpected exceptions are reported with a generic error."""
    task_tools, client, ctx = setup_tools
    mocker.patch.object(client, "update_task", side_effect=RuntimeError("boom"))
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await task_tools.update_task_tool(ctx, id="task-1", status="next")

    assert result["success"] is False
    assert result["error"] == "unexpected_error"
    assert "Unexpected error updating task: boom" in result["message"]
