"""Tests for global alias resources (now/today/overdue/etc.).

Verifies registration and that handlers call the client with scope=global and
apply deterministic ordering when returning items.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


class TestGlobalAliasRegistration:
    """Verify TaskTools registers global alias resources."""

    def test_registers_global_alias_resources(self, mocker: MockerFixture) -> None:
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
            "lunatask://global/now",
            "lunatask://global/today",
            "lunatask://global/overdue",
            "lunatask://global/next-7-days",
            "lunatask://global/high-priority",
            "lunatask://global/recent-completions",
        }
        assert expected.issubset(set(called_uris))


class TestGlobalAliasBehavior:
    """Verify global alias handlers call the client with scope=global and sort results."""

    @pytest.mark.asyncio
    async def test_global_today_calls_client_with_params_and_sorts(
        self, mocker: MockerFixture
    ) -> None:
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

        # Build unsorted sample data to ensure handler sorts deterministically
        t1 = create_task_response(
            task_id="a",
            status="open",
            priority=0,
            due_date=datetime(2025, 8, 25, 10, 0, 0, tzinfo=UTC),
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
        )
        t2 = create_task_response(
            task_id="b",
            status="open",
            priority=2,
            due_date=datetime(2025, 8, 24, 10, 0, 0, tzinfo=UTC),
            created_at=datetime(2025, 8, 19, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 19, 10, 0, 0, tzinfo=UTC),
        )
        t3 = create_task_response(
            task_id="c",
            status="open",
            priority=2,
            due_date=datetime(2025, 8, 24, 10, 0, 0, tzinfo=UTC),
            created_at=datetime(2025, 8, 18, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 18, 10, 0, 0, tzinfo=UTC),
        )

        mock_get_tasks = mocker.patch.object(client, "get_tasks", return_value=[t1, t3, t2])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Invoke global today
        fn = cast(Any, registry["lunatask://global/today"])  # signature: (ctx: Context)

        class Ctx:
            async def info(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())
        result = await fn(ctx)

        # Client called with scope=global and params
        mock_get_tasks.assert_awaited_once()
        _, kwargs = mock_get_tasks.call_args
        assert kwargs["scope"] == "global"
        assert kwargs["window"] == "today"
        assert kwargs["status"] == "open"
        max_limit = 50
        assert kwargs["limit"] == max_limit

        # Sorted deterministically: priority.desc then due_date.asc then id.asc
        ids_in_order = [i["id"] for i in result["items"]]
        assert ids_in_order == ["b", "c", "a"]

    @pytest.mark.asyncio
    async def test_global_overdue_params_and_sort_hint(self, mocker: MockerFixture) -> None:
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

        fn = cast(Any, registry["lunatask://global/overdue"])  # (ctx)

        class Ctx:
            async def info(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())
        result = await fn(ctx)

        call = cast(Any, client.get_tasks)
        _, kwargs = call.call_args  # type: ignore[assignment]
        assert kwargs["scope"] == "global"
        assert kwargs["window"] == "overdue"
        assert kwargs["status"] == "open"
        max_limit = 50
        assert kwargs["limit"] == max_limit
        assert result["sort"] == "due_date.asc,priority.desc,id.asc"

    @pytest.mark.asyncio
    async def test_global_recent_completions_params(self, mocker: MockerFixture) -> None:
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

        fn = cast(Any, registry["lunatask://global/recent-completions"])  # (ctx)

        class Ctx:
            async def info(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())
        result = await fn(ctx)

        call = cast(Any, client.get_tasks)
        _, kwargs = call.call_args  # type: ignore[assignment]
        assert kwargs["scope"] == "global"
        assert kwargs["status"] == "completed"
        assert kwargs["completed_since"] == "-72h"
        assert result["sort"] == "completed_at.desc,id.asc"

    @pytest.mark.asyncio
    async def test_global_high_priority_params(self, mocker: MockerFixture) -> None:
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

        fn = cast(Any, registry["lunatask://global/high-priority"])  # (ctx)

        class Ctx:
            async def info(self, _: str) -> None:
                return

        ctx = cast(Context, Ctx())
        await fn(ctx)

        call = cast(Any, client.get_tasks)
        _, kwargs = call.call_args  # type: ignore[assignment]
        assert kwargs["min_priority"] == "high"
        assert kwargs["status"] == "open"
        max_limit = 50
        assert kwargs["limit"] == max_limit
