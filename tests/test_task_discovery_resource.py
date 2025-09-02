"""Tests for the discovery (read-only) tasks resource.

Validates that the discovery resource returns a JSON structure describing
parameters, defaults, limits, projection, sorts, aliases (area and global),
and guardrails. This test is unit-level and does not require network I/O.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from lunatask_mcp.tools.tasks_resources import tasks_discovery_resource


@pytest.mark.asyncio
async def test_tasks_discovery_resource_minimal_contract() -> None:
    """Discovery resource returns required top-level fields and alias families."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)
    _ = TaskTools(mcp, client)

    class Ctx:
        async def info(self, _: str) -> None:
            """Stub."""
            return

    ctx = cast(Context, Ctx())

    body = await tasks_discovery_resource(client, ctx)

    # Required top-level keys
    for key in (
        "resource_type",
        "params",
        "defaults",
        "limits",
        "projection",
        "sorts",
        "aliases",
        "guardrails",
    ):
        assert key in body

    assert body["resource_type"] == "lunatask_tasks_discovery"

    # Defaults and params basics
    assert body["defaults"]["status"] == "open"
    assert body["defaults"]["limit"] == body["limits"]["max_limit"]
    assert body["defaults"]["sort"] == "priority.desc,due_date.asc,id.asc"
    assert body["defaults"]["tz"] == "UTC"

    # Aliases include both families
    families = {a.get("family") for a in body["aliases"]}
    assert {"area", "global"}.issubset(families)

    # Projection includes detail_uri and core fields
    for field in ("id", "due_date", "priority", "status", "area_id", "detail_uri"):
        assert field in body["projection"]


def test_tasks_discovery_resource_registered_uri(mocker: MockerFixture) -> None:
    """TaskTools registers a discovery resource at a non-breaking URI."""
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

    assert "lunatask://tasks/discovery" in called_uris


@pytest.mark.asyncio
async def test_tasks_uri_is_discovery_only(mocker: MockerFixture) -> None:
    """lunatask://tasks returns discovery payload."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)

    # Capture registered resources
    registry: dict[str, object] = {}

    def capture(uri: str) -> object:
        def deco(fn: object) -> object:
            registry[uri] = fn
            return fn

        return deco

    mocker.patch.object(mcp, "resource", side_effect=capture)

    TaskTools(mcp, client)

    assert "lunatask://tasks" in registry
    assert "lunatask://tasks/discovery" in registry

    # Call both wrappers; they should return discovery payloads
    class Ctx:
        async def info(self, _: str) -> None:
            return

    ctx = cast(Context, Ctx())

    tasks_body = await cast(Any, registry["lunatask://tasks"])(ctx)
    disc_body = await cast(Any, registry["lunatask://tasks/discovery"])(ctx)

    for body in (tasks_body, disc_body):
        assert body["resource_type"] == "lunatask_tasks_discovery"
        for key in ("params", "defaults", "limits", "aliases", "guardrails"):
            assert key in body
