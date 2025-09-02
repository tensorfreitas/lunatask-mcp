"""Priority input handling tests for update_task tool with parametrization.

Covers valid numeric inputs across full range [-2..2] as ints and strings,
and various invalid string inputs.
"""

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.models import TaskUpdate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


class TestUpdateTaskToolPriorityInput:
    """Tests for coercing and validating priority input values."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            (-2, -2),
            (-1, -1),
            (0, 0),
            (1, 1),
            (2, 2),
            ("-2", -2),
            ("-1", -1),
            ("0", 0),
            ("1", 1),
            ("2", 2),
        ],
    )
    async def test_accepts_numeric_priority_and_coerces_when_string(
        self, mocker: MockerFixture, input_value: int | str, expected: int
    ) -> None:
        """Valid priority values are accepted whether int or numeric string."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        async_ctx = mocker.AsyncMock()

        updated_task = create_task_response(task_id="task-123", status="open", priority=expected)
        mocker.patch.object(client, "update_task", return_value=updated_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.update_task_tool(async_ctx, id="task-123", priority=input_value)

        assert result["success"] is True
        client.update_task.assert_called_once()  # type: ignore[attr-defined]
        call_args = client.update_task.call_args  # type: ignore[attr-defined]
        task_update: TaskUpdate = call_args[0][1]  # type: ignore[misc]
        assert isinstance(task_update, TaskUpdate)
        assert task_update.priority == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid",
        [
            "high",
            "low",
            "medium",
            "two",
            "2.5",
            "++2",
            "--1",
            "1,0",
            "1 0",
            "NaN",
        ],
    )
    async def test_rejects_invalid_priority_strings(
        self, mocker: MockerFixture, invalid: str
    ) -> None:
        """Invalid string priority is rejected with validation_error; API not called."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        async_ctx = mocker.AsyncMock()

        mock_update = mocker.patch.object(client, "update_task")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.update_task_tool(async_ctx, id="task-123", priority=invalid)

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "priority" in result["message"].lower()
        mock_update.assert_not_called()
