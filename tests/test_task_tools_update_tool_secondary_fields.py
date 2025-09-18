"""Focused tests for new update_task fields (estimate, progress, goal_id, scheduled_on)."""

from typing import cast

import pytest
from pytest_mock import AsyncMockType, MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.models import TaskUpdate
from lunatask_mcp.tools.tasks_update import update_task_tool
from tests.factories import (
    VALID_ESTIMATE_MINUTES,
    VALID_GOAL_ID,
    VALID_PROGRESS_PERCENT,
    VALID_SCHEDULED_ON,
    build_validation_error,
    create_task_response,
)


@pytest.mark.asyncio
async def test_update_task_tool_includes_new_fields_when_valid(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Successful update sends coerced estimate/progress, goal_id, and scheduled_on."""

    updated_task = create_task_response(
        task_id="task-update-fields",
        estimate=VALID_ESTIMATE_MINUTES,
        progress=VALID_PROGRESS_PERCENT,
        goal_id=VALID_GOAL_ID,
        scheduled_on=VALID_SCHEDULED_ON,
    )

    mocker.patch.object(client, "update_task", return_value=updated_task)
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await update_task_tool(
        client,
        async_ctx,
        id="task-update-fields",
        area_id="area-1",
        estimate=str(VALID_ESTIMATE_MINUTES),
        progress=str(VALID_PROGRESS_PERCENT),
        goal_id=VALID_GOAL_ID,
        scheduled_on="2025-09-01",
    )

    assert result["success"] is True
    assert result["task_id"] == "task-update-fields"

    client.update_task.assert_called_once()  # type: ignore[attr-defined]
    _, sent_payload = client.update_task.call_args.args  # type: ignore[attr-defined]
    sent_payload = cast(TaskUpdate, sent_payload)
    assert sent_payload.estimate == VALID_ESTIMATE_MINUTES
    assert sent_payload.progress == VALID_PROGRESS_PERCENT
    assert sent_payload.goal_id == VALID_GOAL_ID
    assert sent_payload.scheduled_on == VALID_SCHEDULED_ON


@pytest.mark.asyncio
async def test_update_task_tool_invalid_estimate_returns_validation_error(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Invalid estimate input short-circuits with validation error."""

    mocker.patch.object(client, "update_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await update_task_tool(
        client,
        async_ctx,
        id="task-1",
        estimate="bad",
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "Invalid estimate" in result["message"]
    client.update_task.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_update_task_tool_invalid_progress_returns_validation_error(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Invalid progress input short-circuits with validation error."""

    mocker.patch.object(client, "update_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await update_task_tool(
        client,
        async_ctx,
        id="task-1",
        progress="bad",
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "Invalid progress" in result["message"]
    client.update_task.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_update_task_tool_invalid_scheduled_on_returns_validation_error(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Invalid scheduled_on format stops execution with validation error."""

    mocker.patch.object(client, "update_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await update_task_tool(
        client,
        async_ctx,
        id="task-1",
        scheduled_on="2025/09/01",
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "Invalid scheduled_on format" in result["message"]
    client.update_task.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_update_task_tool_maps_pydantic_errors_for_new_fields(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Pydantic validation errors map to friendly messages for new fields."""

    validation_error = build_validation_error(
        "TaskUpdate",
        (
            ("estimate", "value is not a positive integer", -10),
            ("progress", "value is out of range", 200),
        ),
    )

    mocker.patch("lunatask_mcp.tools.tasks_update.TaskUpdate", side_effect=validation_error)
    mocker.patch.object(client, "update_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await update_task_tool(
        client,
        async_ctx,
        id="task-validate",
        estimate=5,
        progress=10,
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "estimate: Must be a positive integer" in result["message"]
    assert "progress: Must be an integer between 0 and 100" in result["message"]
    client.update_task.assert_not_called()  # type: ignore[attr-defined]
    async_ctx.error.assert_called_once_with(result["message"])
