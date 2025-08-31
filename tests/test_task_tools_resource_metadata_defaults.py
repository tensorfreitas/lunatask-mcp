"""Tests for metadata defaults in TaskTools resources.

Covers AC: 10 — metadata.retrieved_at defaults to "unknown" when ctx lacks session_id.
"""

from datetime import UTC, datetime
from typing import cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_task_response


@pytest.mark.asyncio
async def test_get_task_resource_metadata_defaults_without_session_id(
    mocker: MockerFixture,
) -> None:
    """Single-task resource sets metadata.retrieved_at to 'unknown' without session_id."""
    mcp = FastMCP("test-server")
    config = ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )
    client = LunaTaskClient(config)
    task_tools = TaskTools(mcp, client)

    # Context without a session_id attribute; provide awaitable info/error
    class Ctx:
        async def info(self, _: str) -> None:
            """Stub."""
            return

        async def error(self, _: str) -> None:
            """Stub."""
            return

    mock_ctx = Ctx()

    # Minimal task response
    sample_task = create_task_response(
        task_id="task-unknown-meta",
        status="open",
        created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
    )

    mocker.patch.object(client, "get_task", return_value=sample_task)
    mocker.patch.object(client, "__aenter__", return_value=client)
    mocker.patch.object(client, "__aexit__", return_value=None)

    result = await task_tools.get_task_resource(
        cast(Context, mock_ctx), task_id="task-unknown-meta"
    )

    assert result["metadata"]["retrieved_at"] == "unknown"
