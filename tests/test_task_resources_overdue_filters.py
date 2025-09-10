"""Focused tests for overdue filtering in task resources.

These tests ensure that:
- Global overdue returns only tasks due before now (open only)
- Area overdue returns only overdue tasks scoped to the given area

They use explicit construction and mock the client to return mixed data,
exercising client-side filtering regardless of upstream behavior.
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
async def test_global_overdue_filters_only_overdue_open_tasks(mocker: MockerFixture) -> None:
    """Global overdue should return only tasks due before now and not completed."""

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

    od1 = create_task_response(
        task_id="od1",
        status="later",
        scheduled_on=datetime.now(UTC).date() - timedelta(days=2),
    )
    od2 = create_task_response(
        task_id="od2",
        status="started",
        scheduled_on=datetime.now(UTC).date() - timedelta(days=1),
    )
    od3 = create_task_response(
        task_id="od3",
        status="waiting",
        scheduled_on=datetime.now(UTC).date() - timedelta(days=1),
    )

    # Scheduled later than today to ensure it's not considered overdue
    t_today = create_task_response(
        task_id="today",
        status="next",
        scheduled_on=datetime.now(UTC).date() + timedelta(days=1),
    )
    t_future = create_task_response(
        task_id="future",
        status="later",
        scheduled_on=datetime.now(UTC).date() + timedelta(days=3),
    )
    t_completed_overdue = create_task_response(
        task_id="done-od",
        status="completed",
        scheduled_on=datetime.now(UTC).date() - timedelta(days=3),
    )

    # Simulate upstream returning mixed results even when window=overdue
    mocker.patch.object(
        client,
        "get_tasks",
        return_value=[t_today, od3, t_future, od1, t_completed_overdue, od2],
    )
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    fn = cast(Any, registry["lunatask://global/overdue"])  # signature: (ctx: Context)

    class Ctx:
        async def info(self, _: str) -> None:  # logging to stderr via FastMCP in real run
            return

    ctx = cast(Context, Ctx())
    result = await fn(ctx)

    returned_ids = [i["id"] for i in result["items"]]
    # Should contain exactly the 3 overdue open tasks
    assert set(returned_ids) == {"od1", "od2", "od3"}
    # Ensure sort hint matches overdue
    assert result["sort"] == "scheduled_on.asc,priority.desc,id.asc"


@pytest.mark.asyncio
async def test_area_overdue_scopes_and_filters_overdue_only(mocker: MockerFixture) -> None:
    """Area overdue should first scope by area, then include only overdue open tasks."""

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

    area = "area-1"
    other_area = "area-2"

    # Target area: mix of overdue/open, today, future, and completed-overdue
    a1_od = create_task_response(
        task_id="a1-od",
        status="later",
        area_id=area,
        scheduled_on=datetime.now(UTC).date() - timedelta(days=1),
    )
    a1_od2 = create_task_response(
        task_id="a1-od2",
        status="started",
        area_id=area,
        scheduled_on=datetime.now(UTC).date() - timedelta(days=1),
    )
    a1_today = create_task_response(
        task_id="a1-today",
        status="next",
        area_id=area,
        scheduled_on=datetime.now(UTC).date() + timedelta(days=1),
    )
    a1_future = create_task_response(
        task_id="a1-future",
        status="waiting",
        area_id=area,
        scheduled_on=datetime.now(UTC).date() + timedelta(days=5),
    )
    a1_done_od = create_task_response(
        task_id="a1-done-od",
        status="completed",
        area_id=area,
        scheduled_on=datetime.now(UTC).date() - timedelta(days=2),
    )

    # Other area overdue (should be excluded by area filter)
    a2_od = create_task_response(
        task_id="a2-od",
        status="later",
        area_id=other_area,
        scheduled_on=datetime.now(UTC).date() - timedelta(days=1),
    )

    # Simulate upstream returning area-scoped tasks (but not filtering by window correctly)
    mocker.patch.object(
        client,
        "get_tasks",
        return_value=[a2_od, a1_today, a1_od, a1_future, a1_done_od, a1_od2],
    )
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    fn = cast(Any, registry["lunatask://area/{area_id}/overdue"])  # (area_id, ctx)

    class Ctx:
        async def info(self, _: str) -> None:
            return

    ctx = cast(Context, Ctx())
    result = await fn(area, ctx)

    returned_ids = [i["id"] for i in result["items"]]
    # Only overdue open tasks within area-1
    assert set(returned_ids) == {"a1-od", "a1-od2"}
    assert result["sort"] == "scheduled_on.asc,priority.desc,id.asc"
