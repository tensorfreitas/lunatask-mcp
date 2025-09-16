"""Tests for area-scoped alias resources (now/today/overdue/etc.).

Covers registration and minimal behavior: correct parameter mapping to
LunaTaskClient.get_tasks and minimal projection in the response.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskBadRequestError
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from lunatask_mcp.tools.tasks_resources import list_tasks_area_alias
from tests.factories import create_task_response


class TestAreaAliasRegistration:
    """Verify TaskTools registers area-scoped alias resources."""

    def test_registers_area_alias_resources(self, mocker: MockerFixture) -> None:
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        called_uris: list[str] = []

        def capture(uri: str) -> object:
            called_uris.append(uri)

            def deco(fn: object) -> object:
                return fn

            return deco

        mocker.patch.object(mcp, "resource", side_effect=capture)

        TaskTools(mcp, client)

        expected = {
            "lunatask://area/{area_id}/now",
            "lunatask://area/{area_id}/today",
            "lunatask://area/{area_id}/overdue",
            "lunatask://area/{area_id}/next-7-days",
            "lunatask://area/{area_id}/high-priority",
            "lunatask://area/{area_id}/recent-completions",
        }
        assert expected.issubset(set(called_uris))


class TestAreaAliasBehavior:
    """Verify alias handlers call the client with correct params and shape output."""

    @pytest.mark.asyncio
    async def test_area_today_calls_client_with_params(self, mocker: MockerFixture) -> None:
        max_limit = 50
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Capture registered resources to invoke wrapper
        registry: dict[str, object] = {}

        def capture(uri: str) -> object:
            def deco(fn: object) -> object:
                registry[uri] = fn
                return fn

            return deco

        mocker.patch.object(mcp, "resource", side_effect=capture)
        TaskTools(mcp, client)

        # Sample tasks
        t1 = create_task_response(
            task_id="t1",
            status="started",
            area_id="area-1",
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 11, 0, 0, tzinfo=UTC),
        )

        mock_get_tasks = mocker.patch.object(client, "get_tasks", return_value=[t1])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Invoke wrapper for area today
        fn = cast(
            Any, registry["lunatask://area/{area_id}/today"]
        )  # signature: (area_id: str, ctx: Context)

        class Ctx:
            async def info(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())
        result = await fn("area-1", ctx)

        # Client called with canonical params
        mock_get_tasks.assert_awaited_once()
        _, kwargs = mock_get_tasks.call_args
        assert kwargs["area_id"] == "area-1"
        assert kwargs["window"] == "today"
        assert kwargs["status"] == "open"
        assert kwargs["limit"] == max_limit

        # Minimal projection shape
        assert "items" in result
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == "t1"
        assert result["items"][0]["detail_uri"] == "lunatask://tasks/t1"

    @pytest.mark.asyncio
    async def test_area_today_scopes_and_filters_scheduled_on(self, mocker: MockerFixture) -> None:
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

        target_area = "area-123"
        other_area = "area-999"
        today = datetime.now(UTC)
        tomorrow = today + timedelta(days=1)

        # Mixed tasks across areas and days; upstream might ignore filters
        t_today_a = create_task_response(
            task_id="a-today-2",
            status="started",
            priority=2,
            area_id=target_area,
            scheduled_on=today.date(),
        )
        t_today_b = create_task_response(
            task_id="a-today-0",
            status="started",
            priority=0,
            area_id=target_area,
            scheduled_on=today.date(),
        )
        t_other_area_today = create_task_response(
            task_id="b-today",
            status="started",
            priority=2,
            area_id=other_area,
            scheduled_on=today.date(),
        )
        t_other_area_tomorrow = create_task_response(
            task_id="b-tmr",
            status="started",
            priority=1,
            area_id=other_area,
            scheduled_on=tomorrow.date(),
        )
        t_unscheduled_same_area = create_task_response(
            task_id="a-none",
            status="started",
            priority=1,
            area_id=target_area,
            scheduled_on=None,
        )

        mocker.patch.object(
            client,
            "get_tasks",
            return_value=[
                t_other_area_tomorrow,
                t_today_b,
                t_unscheduled_same_area,
                t_today_a,
                t_other_area_today,
            ],
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        fn = cast(Any, registry["lunatask://area/{area_id}/today"])  # (area_id, ctx)

        class Ctx:
            async def info(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())
        result = await fn(target_area, ctx)

        ids_in_order = [i["id"] for i in result["items"]]
        assert ids_in_order == ["a-today-2", "a-today-0"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("alias", "expected_limit"),
        [
            ("now", 25),
            ("overdue", 50),
            ("next_7_days", 50),
            ("high_priority", 50),
            ("recent_completions", 50),
        ],
    )
    async def test_all_area_alias_wrappers(
        self, mocker: MockerFixture, alias: str, expected_limit: int
    ) -> None:
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

        mocker.patch.object(client, "get_tasks", return_value=[])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        uri_by_alias = {
            "now": "lunatask://area/{area_id}/now",
            "overdue": "lunatask://area/{area_id}/overdue",
            "next_7_days": "lunatask://area/{area_id}/next-7-days",
            "high_priority": "lunatask://area/{area_id}/high-priority",
            "recent_completions": "lunatask://area/{area_id}/recent-completions",
        }

        fn = registry[uri_by_alias[alias]]

        class Ctx:
            async def info(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())
        result = await cast(Any, fn)("area-2", ctx)
        assert result["limit"] == expected_limit

    @pytest.mark.asyncio
    async def test_area_alias_missing_area_id_raises(self) -> None:
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        TaskTools(mcp, client)

        class Ctx:
            async def info(self, _: str) -> None:
                return

            async def error(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())

        with pytest.raises(LunaTaskBadRequestError):
            await list_tasks_area_alias(client, ctx, area_id="", alias="today")

    @pytest.mark.asyncio
    async def test_area_alias_invalid_alias_raises(self) -> None:
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        TaskTools(mcp, client)

        class Ctx:
            async def info(self, _: str) -> None:
                return

            async def error(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())

        with pytest.raises(LunaTaskBadRequestError):
            await list_tasks_area_alias(client, ctx, area_id="area-x", alias="bogus")
