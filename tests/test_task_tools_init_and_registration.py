"""Tests for TaskTools initialization and registration.

This module contains tests for the TaskTools class initialization and
MCP resource/tool registration.
"""

from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


class TestTaskToolsInitialization:
    """Test TaskTools initialization and resource registration."""

    def test_task_tools_initialization(self) -> None:
        """Test that TaskTools initializes correctly with MCP and client."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Should initialize without error
        task_tools = TaskTools(mcp, client)

        assert task_tools.mcp is mcp
        assert task_tools.lunatask_client is client

    def test_task_tools_registers_resources(self, mocker: MockerFixture) -> None:
        """Test that TaskTools registers both lunatask://tasks resources and all MCP tools."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource and tool registration
        mock_resource = mocker.patch.object(mcp, "resource")
        mock_tool = mocker.patch.object(mcp, "tool")

        TaskTools(mcp, client)

        # Verify both resources were registered
        mock_resource.assert_any_call("lunatask://tasks")
        mock_resource.assert_any_call("lunatask://tasks/{task_id}")
        expected_resource_count = 2
        assert mock_resource.call_count == expected_resource_count

        # Verify all tools were registered
        mock_tool.assert_any_call("create_task")
        mock_tool.assert_any_call("update_task")
        mock_tool.assert_any_call("delete_task")
        expected_tool_count = 3
        assert mock_tool.call_count == expected_tool_count


class TestTaskToolsRegisteredWrappers:
    """Tests that registered wrapper functions delegate to implementation.

    These tests exercise the inner wrapper coroutines created in
    `TaskTools._register_resources` to ensure they call the underlying
    implementation functions with proper dependency injection. This
    specifically covers the previously uncovered lines in tasks.py.
    """

    @pytest.mark.asyncio
    async def test_registered_resource_wrappers_delegate(self, mocker: MockerFixture) -> None:
        """Resources wrappers call underlying functions with injected client."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Capture functions registered via FastMCP decorators
        registered_resources: dict[str, object] = {}

        def capture_resource(uri: str) -> Callable[[object], object]:
            def decorator(fn: object) -> object:
                registered_resources[uri] = fn
                return fn

            return decorator

        mocker.patch.object(mcp, "resource", side_effect=capture_resource)

        # Patch underlying implementation functions to verify delegation
        mock_get_tasks_resource = mocker.AsyncMock(return_value={"ok": True, "type": "list"})
        mock_get_task_resource = mocker.AsyncMock(return_value={"ok": True, "type": "single"})
        mocker.patch(
            "lunatask_mcp.tools.tasks.get_tasks_resource_fn",
            new=mock_get_tasks_resource,
        )
        mocker.patch(
            "lunatask_mcp.tools.tasks.get_task_resource_fn",
            new=mock_get_task_resource,
        )

        # Initialize TaskTools to register wrappers
        TaskTools(mcp, client)

        # Sanity: both resources should be registered
        assert "lunatask://tasks" in registered_resources
        assert "lunatask://tasks/{task_id}" in registered_resources

        # Invoke wrappers and verify they delegate to implementation with injected client
        mock_ctx = mocker.AsyncMock()

        list_wrapper = registered_resources["lunatask://tasks"]
        single_wrapper = registered_resources["lunatask://tasks/{task_id}"]

        list_result = await list_wrapper(mock_ctx)  # type: ignore[misc]
        single_result = await single_wrapper("abc123", mock_ctx)  # type: ignore[misc]

        assert list_result == {"ok": True, "type": "list"}
        assert single_result == {"ok": True, "type": "single"}

        mock_get_tasks_resource.assert_awaited_once_with(client, mock_ctx)
        mock_get_task_resource.assert_awaited_once_with(client, mock_ctx, "abc123")

    @pytest.mark.asyncio
    async def test_registered_tool_wrappers_delegate(self, mocker: MockerFixture) -> None:
        """Tool wrappers call underlying functions with injected client and params."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Capture tool functions registered via decorator
        registered_tools: dict[str, object] = {}

        def capture_tool(name: str) -> Callable[[object], object]:
            def decorator(fn: object) -> object:
                registered_tools[name] = fn
                return fn

            return decorator

        mocker.patch.object(mcp, "tool", side_effect=capture_tool)

        # Patch underlying tool implementations
        mock_create = mocker.AsyncMock(return_value={"ok": True, "op": "create"})
        mock_update = mocker.AsyncMock(return_value={"ok": True, "op": "update"})
        mock_delete = mocker.AsyncMock(return_value={"ok": True, "op": "delete"})
        mocker.patch("lunatask_mcp.tools.tasks.create_task_tool_fn", new=mock_create)
        mocker.patch("lunatask_mcp.tools.tasks.update_task_tool_fn", new=mock_update)
        mocker.patch("lunatask_mcp.tools.tasks.delete_task_tool_fn", new=mock_delete)

        # Initialize TaskTools to register wrappers
        TaskTools(mcp, client)

        # Sanity: all tools should be registered
        assert {"create_task", "update_task", "delete_task"}.issubset(registered_tools.keys())

        mock_ctx = mocker.AsyncMock()

        # Invoke wrappers with sample params
        create_wrapper = registered_tools["create_task"]
        update_wrapper = registered_tools["update_task"]
        delete_wrapper = registered_tools["delete_task"]

        # Provide precise callable types for Pyright
        create_fn = cast(Callable[..., Awaitable[dict[str, Any]]], create_wrapper)
        update_fn = cast(Callable[..., Awaitable[dict[str, Any]]], update_wrapper)
        delete_fn = cast(Callable[..., Awaitable[dict[str, Any]]], delete_wrapper)

        create_res = cast(
            dict[str, Any],
            await create_fn(
                mock_ctx, name="N", note=None, area_id=None, status="later", priority=0
            ),
        )  # type: ignore[misc]
        update_res = cast(
            dict[str, Any],
            await update_fn(mock_ctx, id="tid", status="started", due_date=None),
        )  # type: ignore[misc]
        delete_res = cast(dict[str, Any], await delete_fn(mock_ctx, id="tid"))  # type: ignore[misc]

        assert create_res == {"ok": True, "op": "create"}
        assert update_res == {"ok": True, "op": "update"}
        assert delete_res == {"ok": True, "op": "delete"}

        mock_create.assert_awaited()
        mock_update.assert_awaited()
        mock_delete.assert_awaited_once_with(client, mock_ctx, "tid")
