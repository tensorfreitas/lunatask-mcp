"""Guardrails and canonicalization tests for list resources.

Covers:
- Enforcing list guardrails in `LunaTaskClient.get_tasks` (limit cap, deny expand,
  require scope when params present).
- Canonicalization in discovery alias URIs (sorted params and explicit scope).
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskBadRequestError
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from lunatask_mcp.tools.tasks_resources import tasks_discovery_resource


@pytest.mark.asyncio
async def test_discovery_alias_canonical_params_sorted() -> None:
    """Discovery aliases use sorted params and explicit scope for globals."""
    mcp = FastMCP("test-server")
    client = LunaTaskClient(
        ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
    )
    _ = TaskTools(mcp, client)

    class Ctx:
        async def info(self, _: str) -> None:  # stderr-only logging stub
            return

    ctx = cast(Context, Ctx())
    body = await tasks_discovery_resource(client, ctx)
    aliases: list[dict[str, Any]] = cast(list[dict[str, Any]], body["aliases"])

    # Find one area and one global alias
    area_now = next(a for a in aliases if a["family"] == "area" and a["name"] == "now")
    global_overdue = next(a for a in aliases if a["family"] == "global" and a["name"] == "overdue")

    # Expect canonical URIs to have params sorted by key
    assert area_now["canonical"] == "lunatask://tasks?area_id={area_id}&limit=25&status=open"
    assert global_overdue["canonical"] == (
        "lunatask://tasks?limit=50&scope=global&sort=due_date.asc,priority.desc,id.asc"
        "&status=open&window=overdue"
    )


MAX_LIMIT = 50


@pytest.mark.asyncio
async def test_client_get_tasks_caps_limit_and_sorts_params(mocker: MockerFixture) -> None:
    """get_tasks caps limit to 50 and orders params consistently."""
    client = LunaTaskClient(
        ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
    )

    async def fake_request(
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert method == "GET"
        assert endpoint == "tasks"
        assert params is not None
        # Params keys are sorted by key when iterated (insertion order)
        assert list(params.keys()) == sorted(params.keys())
        assert params["limit"] == MAX_LIMIT  # capped
        return {"tasks": []}

    mocker.patch.object(client, "make_request", side_effect=fake_request)

    # Provide params without area_id/scope to avoid breaking legacy list resource;
    # scope requirement is validated in separate test where params are present.
    await client.get_tasks(scope="global", status="open", limit=999, sort="priority.desc")


@pytest.mark.asyncio
async def test_client_get_tasks_denies_expand_param(mocker: MockerFixture) -> None:
    """get_tasks rejects unsupported 'expand' parameter."""
    client = LunaTaskClient(
        ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
    )

    mocker.patch.object(client, "make_request", return_value={"tasks": []})

    with pytest.raises(LunaTaskBadRequestError):
        await client.get_tasks(scope="global", expand="subtasks")  # type: ignore[arg-type]
