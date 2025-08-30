"""Coercion tests for update_task tool.

Verifies that invalid status/motivation inputs are ignored (omitted) by mapping
to None in the TaskUpdate sent to the client, as per Tasks 8 and 9.
"""

import pytest
from pytest_mock import AsyncMockType, MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.models import TaskUpdate
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


class TestUpdateTaskToolCoercion:
    """Unit tests asserting coercion/omission behavior in update_task tool."""

    @pytest.mark.asyncio
    async def test_invalid_status_is_ignored_not_sent(
        self,
        task_tools: TaskTools,
        client: LunaTaskClient,
        async_ctx: AsyncMockType,
        mocker: MockerFixture,
    ) -> None:
        """Invalid status input is coerced to None and not sent to API (Task 8)."""
        # Arrange
        updated_task = create_task_response(task_id="task-123", status="open")
        mocker.patch.object(client, "update_task", return_value=updated_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Act
        result = await task_tools.update_task_tool(async_ctx, id="task-123", status="invalid")

        # Assert result shape
        assert result["success"] is True
        assert result["task_id"] == "task-123"

        # Assert coercion: TaskUpdate.status is None in call args
        client.update_task.assert_called_once()  # type: ignore[attr-defined]
        call_args = client.update_task.call_args  # type: ignore[attr-defined]
        task_update: TaskUpdate = call_args[0][1]  # type: ignore[misc]
        assert isinstance(task_update, TaskUpdate)
        assert task_update.status is None

    @pytest.mark.asyncio
    async def test_invalid_motivation_is_ignored_not_sent(
        self,
        task_tools: TaskTools,
        client: LunaTaskClient,
        async_ctx: AsyncMockType,
        mocker: MockerFixture,
    ) -> None:
        """Invalid motivation input is coerced to None and not sent (Task 9)."""
        # Arrange
        updated_task = create_task_response(task_id="task-456", status="open")
        mocker.patch.object(client, "update_task", return_value=updated_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Act
        result = await task_tools.update_task_tool(async_ctx, id="task-456", motivation="nope")

        # Assert result shape
        assert result["success"] is True
        assert result["task_id"] == "task-456"

        # Assert coercion: TaskUpdate.motivation is None in call args
        client.update_task.assert_called_once()  # type: ignore[attr-defined]
        call_args = client.update_task.call_args  # type: ignore[attr-defined]
        task_update: TaskUpdate = call_args[0][1]  # type: ignore[misc]
        assert isinstance(task_update, TaskUpdate)
        assert task_update.motivation is None
