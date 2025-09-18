"""Focused tests for new create_task fields (estimate, progress, goal_id, scheduled_on).

These tests specifically validate the coercion and validation logic that was
added to the create task tool when the new optional parameters were introduced.
"""

from typing import cast

import pytest
from pytest_mock import AsyncMockType, MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.models import TaskCreate
from lunatask_mcp.tools.tasks_create import create_task_tool
from tests.factories import (
    VALID_ESTIMATE_MINUTES,
    VALID_GOAL_ID,
    VALID_PROGRESS_PERCENT,
    VALID_SCHEDULED_ON,
    build_validation_error,
    create_task_response,
)


@pytest.mark.asyncio
async def test_create_task_tool_coerces_new_fields(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """String inputs for estimate/progress are coerced and scheduled_on parses to date."""

    created_task = create_task_response(
        task_id="task-new-fields",
        estimate=VALID_ESTIMATE_MINUTES,
        progress=VALID_PROGRESS_PERCENT,
        goal_id=VALID_GOAL_ID,
        scheduled_on=VALID_SCHEDULED_ON,
    )

    mocker.patch.object(client, "create_task", return_value=created_task)
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await create_task_tool(
        client,
        async_ctx,
        name="Test Task",
        area_id="area-1",
        estimate=str(VALID_ESTIMATE_MINUTES),
        progress=str(VALID_PROGRESS_PERCENT),
        goal_id=VALID_GOAL_ID,
        scheduled_on="2025-09-01",
    )

    assert result["success"] is True
    assert result["task_id"] == "task-new-fields"

    client.create_task.assert_called_once()  # type: ignore[attr-defined]
    sent_payload = cast(TaskCreate, client.create_task.call_args.args[0])  # type: ignore[attr-defined]
    assert sent_payload.estimate == VALID_ESTIMATE_MINUTES
    assert sent_payload.progress == VALID_PROGRESS_PERCENT
    assert sent_payload.goal_id == VALID_GOAL_ID
    assert sent_payload.scheduled_on == VALID_SCHEDULED_ON


@pytest.mark.asyncio
async def test_create_task_tool_invalid_estimate_returns_validation_error(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Invalid estimate input returns validation error response and skips client call."""

    mocker.patch.object(client, "create_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await create_task_tool(
        client,
        async_ctx,
        name="Invalid Estimate",
        area_id="area-1",
        estimate="not-a-number",
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "Invalid estimate" in result["message"]
    client.create_task.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_create_task_tool_invalid_progress_returns_validation_error(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Invalid progress input returns validation error response and skips client call."""

    mocker.patch.object(client, "create_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await create_task_tool(
        client,
        async_ctx,
        name="Invalid Progress",
        area_id="area-1",
        progress="not-a-number",
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "Invalid progress" in result["message"]
    client.create_task.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_create_task_tool_invalid_scheduled_on_returns_validation_error(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Invalid scheduled_on format is surfaced as validation error and stops execution."""

    mocker.patch.object(client, "create_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await create_task_tool(
        client,
        async_ctx,
        name="Invalid Scheduled",
        area_id="area-1",
        scheduled_on="2025/09/01",
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "Invalid scheduled_on format" in result["message"]
    client.create_task.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_create_task_tool_maps_pydantic_errors_for_new_fields(
    client: LunaTaskClient,
    async_ctx: AsyncMockType,
    mocker: MockerFixture,
) -> None:
    """Pydantic validation errors surface friendly messages for new fields."""

    validation_error = build_validation_error(
        "TaskCreate",
        (
            ("estimate", "value is not a positive integer", -5),
            ("progress", "value is out of range", 150),
            ("scheduled_on", "invalid date", "09-01-2025"),
        ),
    )

    mocker.patch("lunatask_mcp.tools.tasks_create.TaskCreate", side_effect=validation_error)
    mocker.patch.object(client, "create_task")
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await create_task_tool(
        client,
        async_ctx,
        name="Validation Failure",
        area_id="area-1",
        estimate=10,
        progress=20,
        scheduled_on="2025-09-01",
    )

    assert result["success"] is False
    assert result["error"] == "validation_error"
    assert "estimate: Must be a positive integer" in result["message"]
    assert "progress: Must be an integer between 0 and 100" in result["message"]
    assert "scheduled_on: Must be in YYYY-MM-DD format" in result["message"]
    client.create_task.assert_not_called()  # type: ignore[attr-defined]
    async_ctx.error.assert_called_once_with(result["message"])
