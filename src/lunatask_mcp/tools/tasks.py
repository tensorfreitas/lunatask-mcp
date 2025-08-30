"""Task management tools for LunaTask MCP integration.

This module now exposes the TaskTools class and delegates implementation of
individual handlers to smaller modules to keep file size under 500 lines.
"""

import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.context import Context as ServerContext

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.tools.tasks_create import create_task_tool as create_task_tool_fn
from lunatask_mcp.tools.tasks_delete import delete_task_tool as delete_task_tool_fn
from lunatask_mcp.tools.tasks_resources import (
    get_task_resource as get_task_resource_fn,
)
from lunatask_mcp.tools.tasks_resources import (
    get_tasks_resource as get_tasks_resource_fn,
)
from lunatask_mcp.tools.tasks_update import update_task_tool as update_task_tool_fn

# Configure logger to write to stderr
logger = logging.getLogger(__name__)


class TaskTools:
    """Task management tools providing MCP resources for LunaTask integration.

    This class encapsulates task-related MCP resources, enabling AI models
    to retrieve and work with task data from LunaTask through standardized
    MCP resource URIs. Implementation details are delegated to helper modules.
    """

    # Note: Functions now use dependency injection rather than self binding

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize TaskTools with MCP instance and LunaTask client.

        Args:
            mcp_instance: FastMCP server instance for registering resources
            lunatask_client: LunaTask API client for data retrieval
        """
        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_resources()

    # Public API methods for backwards compatibility with tests
    async def get_tasks_resource(self, ctx: ServerContext) -> dict[str, Any]:
        """MCP resource providing access to all LunaTask tasks."""
        return await get_tasks_resource_fn(self.lunatask_client, ctx)

    async def get_task_resource(self, ctx: ServerContext, task_id: str) -> dict[str, Any]:
        """MCP resource providing access to a single LunaTask task by ID."""
        return await get_task_resource_fn(self.lunatask_client, ctx, task_id)

    async def create_task_tool(  # noqa: PLR0913
        self,
        ctx: ServerContext,
        name: str,
        note: str | None = None,
        area_id: str | None = None,
        status: str = "later",
        priority: int = 0,
        motivation: str = "unknown",
        eisenhower: int | None = None,
    ) -> dict[str, Any]:
        """Create a new task in LunaTask."""
        return await create_task_tool_fn(
            self.lunatask_client,
            ctx,
            name,
            note,
            area_id,
            status,
            priority,
            motivation,
            eisenhower,
        )

    async def update_task_tool(  # noqa: PLR0913
        self,
        ctx: ServerContext,
        id: str,  # noqa: A002
        name: str | None = None,
        note: str | None = None,
        area_id: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        due_date: str | None = None,
        motivation: str | None = None,
        eisenhower: int | None = None,
    ) -> dict[str, Any]:
        """Update an existing task in LunaTask."""
        return await update_task_tool_fn(
            self.lunatask_client,
            ctx,
            id,
            name,
            note,
            area_id,
            status,
            priority,
            due_date,
            motivation,
            eisenhower,
        )

    async def delete_task_tool(self, ctx: ServerContext, id: str) -> dict[str, Any]:  # noqa: A002
        """Delete an existing task in LunaTask."""
        return await delete_task_tool_fn(self.lunatask_client, ctx, id)

    def _register_resources(self) -> None:
        """Register all task-related MCP resources and tools with the FastMCP instance."""
        # Wrap resource functions to satisfy FastMCP signature expectations
        # for static resources (no URI params) and parameterized resources.

        # Wrap functions to inject lunatask_client dependency
        async def _tasks_list_resource(ctx: ServerContext) -> dict[str, Any]:
            return await get_tasks_resource_fn(self.lunatask_client, ctx)

        async def _task_single_resource(task_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await get_task_resource_fn(self.lunatask_client, ctx, task_id)

        async def _create_task_tool(  # noqa: PLR0913
            ctx: ServerContext,
            name: str,
            note: str | None = None,
            area_id: str | None = None,
            status: str = "later",
            priority: int = 0,
            motivation: str = "unknown",
            eisenhower: int | None = None,
        ) -> dict[str, Any]:
            return await create_task_tool_fn(
                self.lunatask_client,
                ctx,
                name,
                note,
                area_id,
                status,
                priority,
                motivation,
                eisenhower,
            )

        async def _update_task_tool(  # noqa: PLR0913
            ctx: ServerContext,
            task_id: str,  # renamed from id to avoid builtin shadow
            name: str | None = None,
            note: str | None = None,
            area_id: str | None = None,
            status: str | None = None,
            priority: int | None = None,
            due_date: str | None = None,
            motivation: str | None = None,
            eisenhower: int | None = None,
        ) -> dict[str, Any]:
            return await update_task_tool_fn(
                self.lunatask_client,
                ctx,
                task_id,
                name,
                note,
                area_id,
                status,
                priority,
                due_date,
                motivation,
                eisenhower,
            )

        async def _delete_task_tool(ctx: ServerContext, task_id: str) -> dict[str, Any]:
            return await delete_task_tool_fn(self.lunatask_client, ctx, task_id)

        self.mcp.resource("lunatask://tasks")(_tasks_list_resource)
        self.mcp.resource("lunatask://tasks/{task_id}")(_task_single_resource)
        self.mcp.tool("create_task")(_create_task_tool)
        self.mcp.tool("update_task")(_update_task_tool)
        self.mcp.tool("delete_task")(_delete_task_tool)
