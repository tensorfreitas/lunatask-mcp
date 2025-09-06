"""Test that the task filtering fix works correctly.

This test verifies that the global/area aliases now properly filter tasks
client-side and return only the expected subset instead of all tasks.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


@pytest.mark.asyncio
async def test_global_now_returns_only_custom_undated_set(
    mocker: MockerFixture,
) -> None:
    """global/now returns only UNDated tasks meeting custom criteria.

    Criteria (any): status==started OR priority==2 OR motivation=="must" OR eisenhower==1.
    Always excludes completed tasks. Dated tasks are excluded.
    """
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)

    # Capture registered functions
    registry: dict[str, object] = {}

    def capture(uri: str) -> object:
        def deco(fn: object) -> object:
            registry[uri] = fn
            return fn

        return deco

    mocker.patch.object(mcp, "resource", side_effect=capture)
    TaskTools(mcp, client)

    # Create sample data: mix of tasks that should and shouldn't be in "now"
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Included (undated + any rule)
    undated_started = create_task_response(
        task_id="undated-started",
        status="started",
        priority=0,
        due_date=None,
    )
    undated_priority2 = create_task_response(
        task_id="undated-prio2",
        status="next",
        priority=2,
        due_date=None,
    )
    undated_must = create_task_response(
        task_id="undated-must",
        status="waiting",
        motivation="must",
        due_date=None,
    )
    undated_e1 = create_task_response(
        task_id="undated-e1",
        status="later",
        eisenhower=1,
        due_date=None,
    )

    # Excluded
    dated_today = create_task_response(
        task_id="dated-today",
        status="started",
        priority=2,
        due_date=today_start + timedelta(hours=14),
    )
    dated_overdue = create_task_response(
        task_id="dated-overdue",
        status="next",
        due_date=today_start - timedelta(days=1),
    )
    undated_low = create_task_response(
        task_id="undated-low",
        status="next",
        priority=1,
        due_date=None,
    )
    undated_completed = create_task_response(
        task_id="undated-completed",
        status="completed",
        priority=2,
        due_date=None,
    )

    # Mock the API to return ALL tasks (simulating the real API behavior)
    all_tasks = [
        undated_started,
        undated_priority2,
        undated_must,
        undated_e1,
        dated_today,
        dated_overdue,
        undated_low,
        undated_completed,
    ]
    mock_get_tasks = mocker.patch.object(client, "get_tasks", return_value=all_tasks)
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    # Invoke global now
    fn = registry["lunatask://global/now"]

    class Ctx:
        async def info(self, _: str) -> None:
            return

        async def error(self, _: str) -> None:
            return

    ctx = Ctx()
    result: dict[str, Any] = await fn(ctx)  # type: ignore[misc] # Mock function signature

    # Verify the fix: API is called with NO filtering parameters
    mock_get_tasks.assert_awaited_once()
    _, kwargs = mock_get_tasks.call_args
    assert not kwargs, "API should be called with no parameters"  # Fixed!

    # The result should now contain ONLY the filtered undated tasks
    expected_task_count = 4
    assert len(result["items"]) == expected_task_count  # type: ignore[arg-type] # Mock data types

    returned_ids = {item["id"] for item in result["items"]}  # type: ignore[misc] # Mock data types

    # Should include these (undated + any rule):
    assert "undated-started" in returned_ids
    assert "undated-prio2" in returned_ids
    assert "undated-must" in returned_ids
    assert "undated-e1" in returned_ids

    # Should NOT include these:
    assert "dated-today" not in returned_ids  # dated → excluded
    assert "dated-overdue" not in returned_ids  # dated → excluded
    assert "undated-low" not in returned_ids  # undated but no rule matched
    assert "undated-completed" not in returned_ids  # completed → excluded

    # Check the limit is applied correctly
    expected_limit = 25
    assert result["limit"] == expected_limit  # "now" should have limit of 25


@pytest.mark.asyncio
async def test_global_high_priority_returns_only_high_priority_tasks(
    mocker: MockerFixture,
) -> None:
    """Test that high-priority alias returns only high-priority tasks (priority >= 1)."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)

    registry: dict[str, object] = {}

    def capture(uri: str) -> object:
        def deco(fn: object) -> object:
            registry[uri] = fn
            return fn

        return deco

    mocker.patch.object(mcp, "resource", side_effect=capture)
    TaskTools(mcp, client)

    # Mix of different priority tasks (remember: priority range is -2 to 2)
    high_priority_1 = create_task_response(task_id="high1", status="later", priority=2)
    high_priority_2 = create_task_response(task_id="high2", status="started", priority=1)
    medium_priority = create_task_response(task_id="medium", status="next", priority=0)
    low_priority_1 = create_task_response(task_id="low1", status="waiting", priority=-1)
    low_priority_2 = create_task_response(task_id="low2", status="later", priority=-2)
    completed_high = create_task_response(
        task_id="completed", status="completed", priority=2
    )  # Should be filtered out by status

    all_tasks = [
        high_priority_1,
        high_priority_2,
        medium_priority,
        low_priority_1,
        low_priority_2,
        completed_high,
    ]
    mocker.patch.object(client, "get_tasks", return_value=all_tasks)
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    fn = registry["lunatask://global/high-priority"]

    class Ctx:
        async def info(self, _: str) -> None:
            return

        async def error(self, _: str) -> None:
            return

    ctx = Ctx()
    result: dict[str, Any] = await fn(ctx)  # type: ignore[misc] # Mock function signature

    # Should return only high priority (>= 1) AND not completed
    expected_high_priority_count = 2
    assert len(result["items"]) == expected_high_priority_count  # type: ignore[arg-type] # Mock data types

    returned_ids = {item["id"] for item in result["items"]}  # type: ignore[misc] # Mock data types

    # Should include high priority, open tasks:
    assert "high1" in returned_ids  # Priority 2, status "later" (open)
    assert "high2" in returned_ids  # Priority 1, status "started" (open)

    # Should NOT include these:
    assert "medium" not in returned_ids  # Priority 0 - too low!
    assert "low1" not in returned_ids  # Priority -1 - too low!
    assert "low2" not in returned_ids  # Priority -2 - too low!
    assert "completed" not in returned_ids  # Priority 2 but status "completed" - filtered out!

    # Check limit and sort
    expected_high_priority_limit = 50
    assert result["limit"] == expected_high_priority_limit  # High priority should have limit of 50
    assert result["sort"] == "priority.desc,due_date.asc,id.asc"


@pytest.mark.asyncio
async def test_area_alias_filters_by_area_and_criteria(
    mocker: MockerFixture,
) -> None:
    """Test that area aliases filter by both area_id and the specific criteria."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)

    registry: dict[str, object] = {}

    def capture(uri: str) -> object:
        def deco(fn: object) -> object:
            registry[uri] = fn
            return fn

        return deco

    mocker.patch.object(mcp, "resource", side_effect=capture)
    TaskTools(mcp, client)

    # Tasks in different areas with different priorities
    area1_high = create_task_response(
        task_id="area1-high", status="later", priority=2, area_id="area-1"
    )
    area1_low = create_task_response(
        task_id="area1-low", status="next", priority=0, area_id="area-1"
    )
    area2_high = create_task_response(
        task_id="area2-high", status="started", priority=2, area_id="area-2"
    )
    no_area_high = create_task_response(
        task_id="no-area-high", status="waiting", priority=2, area_id=None
    )

    all_tasks = [area1_high, area1_low, area2_high, no_area_high]
    mocker.patch.object(client, "get_tasks", return_value=all_tasks)
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    fn = registry["lunatask://area/{area_id}/high-priority"]

    class Ctx:
        async def info(self, _: str) -> None:
            return

        async def error(self, _: str) -> None:
            return

    ctx = Ctx()
    result: dict[str, Any] = await fn("area-1", ctx)  # type: ignore[misc] # Mock function signature

    # Should return only area-1 tasks that are high priority
    expected_area_task_count = 1
    assert len(result["items"]) == expected_area_task_count  # type: ignore[arg-type] # Mock data types

    returned_ids = {item["id"] for item in result["items"]}  # type: ignore[misc] # Mock data types

    # Should include:
    assert "area1-high" in returned_ids  # Area-1, high priority

    # Should NOT include:
    assert "area1-low" not in returned_ids  # Area-1 but low priority
    assert "area2-high" not in returned_ids  # High priority but wrong area
    assert "no-area-high" not in returned_ids  # High priority but no area
