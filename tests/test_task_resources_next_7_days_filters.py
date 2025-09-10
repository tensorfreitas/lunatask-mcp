"""Focused tests for next-7-days filtering in task resources.

These tests ensure that:
- Global next-7-days returns only tasks due within the next 7 days (open only),
  excluding overdue and today
- Area next-7-days scopes by area_id and applies the same window

They simulate an upstream that ignores the window parameter so client-side
filtering must kick in.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


@pytest.mark.asyncio
async def test_global_next_7_days_filters_only_future_window(mocker: MockerFixture) -> None:
    """Global next-7-days should include only tasks scheduled in next 7 days.

    Excludes overdue and today-scheduled tasks; includes tasks with scheduled_on >= tomorrow
    and <= today + 7 days.
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

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_date = today_start.date()

    # Build tasks across windows using scheduled_on semantics
    # Excluded: scheduled today or overdue or beyond 7 days
    overdue = create_task_response(
        task_id="od", status="later", scheduled_on=today_date - timedelta(days=1)
    )
    today_scheduled = create_task_response(task_id="today", status="next", scheduled_on=today_date)
    in_2_days = create_task_response(
        task_id="d2", status="waiting", scheduled_on=today_date + timedelta(days=2)
    )
    in_6_days = create_task_response(
        task_id="d6", status="later", scheduled_on=today_date + timedelta(days=6)
    )
    in_7_days_edge = create_task_response(
        task_id="d7",
        status="later",
        scheduled_on=today_date + timedelta(days=7),
    )
    beyond_7 = create_task_response(
        task_id="d8", status="later", scheduled_on=today_date + timedelta(days=8)
    )

    # Simulate upstream returning mixed data even with window param
    mocker.patch.object(
        client,
        "get_tasks",
        return_value=[overdue, beyond_7, today_scheduled, in_6_days, in_2_days, in_7_days_edge],
    )
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    fn = cast(Any, registry["lunatask://global/next-7-days"])  # signature: (ctx)

    class Ctx:
        async def info(self, _: str) -> None:
            return

    ctx = cast(Context, Ctx())
    result = await fn(ctx)

    # Verify client called with canonical params including window; client-side filtering applies
    call = cast(Any, client.get_tasks)
    _, kwargs = call.call_args  # type: ignore[assignment]
    assert kwargs["scope"] == "global"
    assert kwargs["window"] == "next_7_days"
    assert kwargs["status"] == "open"
    assert kwargs["limit"] == 50  # noqa: PLR2004 Magic value used in comparison

    returned_ids = [i["id"] for i in result["items"]]
    # Only items strictly within (today, today+7] by scheduled_on
    assert set(returned_ids) == {"d2", "d6", "d7"}


@pytest.mark.asyncio
async def test_area_next_7_days_scopes_and_filters(mocker: MockerFixture) -> None:
    """Area next-7-days: scope by area, then include only next-window open tasks."""
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

    area = "area-1"
    other = "area-2"
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_date = today_start.date()

    a_overdue = create_task_response(
        task_id="a-od", status="later", area_id=area, scheduled_on=today_date - timedelta(days=1)
    )
    a_today = create_task_response(
        task_id="a-today", status="later", area_id=area, scheduled_on=today_date
    )
    a_in3 = create_task_response(
        task_id="a-3", status="waiting", area_id=area, scheduled_on=today_date + timedelta(days=3)
    )
    a_in7 = create_task_response(
        task_id="a-7", status="later", area_id=area, scheduled_on=today_date + timedelta(days=7)
    )
    b_in4 = create_task_response(
        task_id="b-4", status="later", area_id=other, scheduled_on=today_date + timedelta(days=4)
    )
    a_beyond = create_task_response(
        task_id="a-10", status="later", area_id=area, scheduled_on=today_date + timedelta(days=10)
    )

    mocker.patch.object(
        client,
        "get_tasks",
        return_value=[a_beyond, a_today, a_overdue, b_in4, a_in7, a_in3],
    )
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    fn = cast(Any, registry["lunatask://area/{area_id}/next-7-days"])  # signature: (area_id, ctx)

    class Ctx:
        async def info(self, _: str) -> None:
            return

    ctx = cast(Context, Ctx())
    result = await fn(area, ctx)

    # API called with window and area, but client-side window filtering applies
    call = cast(Any, client.get_tasks)
    _, kwargs = call.call_args  # type: ignore[assignment]
    assert kwargs["area_id"] == area
    assert kwargs["window"] == "next_7_days"
    assert kwargs["status"] == "open"
    assert kwargs["limit"] == 50  # noqa: PLR2004 Magic value used in comparison

    ids = [i["id"] for i in result["items"]]
    assert set(ids) == {"a-3", "a-7"}
