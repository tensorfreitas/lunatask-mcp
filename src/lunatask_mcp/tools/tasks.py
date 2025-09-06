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
from lunatask_mcp.tools.tasks_resources import (
    list_tasks_area_alias as list_tasks_area_alias_fn,
)
from lunatask_mcp.tools.tasks_resources import (
    list_tasks_global_alias as list_tasks_global_alias_fn,
)
from lunatask_mcp.tools.tasks_resources import (
    tasks_discovery_resource as tasks_discovery_resource_fn,
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
        priority: int | str = 0,
        motivation: str = "unknown",
        eisenhower: int | str | None = None,
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
        priority: int | str | None = None,
        due_date: str | None = None,
        motivation: str | None = None,
        eisenhower: int | str | None = None,
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

    def _register_resources(self) -> None:  # noqa: C901
        """Register all task-related MCP resources and tools with the FastMCP instance."""
        # Wrap resource functions to satisfy FastMCP signature expectations
        # for static resources (no URI params) and parameterized resources.

        # Wrap functions to inject lunatask_client dependency

        async def _task_single_resource(task_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await get_task_resource_fn(self.lunatask_client, ctx, task_id)

        async def _tasks_discovery(ctx: ServerContext) -> dict[str, Any]:
            return await tasks_discovery_resource_fn(self.lunatask_client, ctx)

        # Area-scoped alias resources
        async def _area_now(area_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_area_alias_fn(
                self.lunatask_client, ctx, area_id=area_id, alias="now"
            )

        async def _area_today(area_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_area_alias_fn(
                self.lunatask_client, ctx, area_id=area_id, alias="today"
            )

        async def _area_overdue(area_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_area_alias_fn(
                self.lunatask_client, ctx, area_id=area_id, alias="overdue"
            )

        async def _area_next7(area_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_area_alias_fn(
                self.lunatask_client, ctx, area_id=area_id, alias="next_7_days"
            )

        async def _area_high(area_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_area_alias_fn(
                self.lunatask_client, ctx, area_id=area_id, alias="high_priority"
            )

        async def _area_recent(area_id: str, ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_area_alias_fn(
                self.lunatask_client, ctx, area_id=area_id, alias="recent_completions"
            )

        async def _create_task_tool(  # noqa: PLR0913
            ctx: ServerContext,
            name: str,
            note: str | None = None,
            area_id: str | None = None,
            status: str = "later",
            priority: int | str = 0,
            motivation: str = "unknown",
            eisenhower: int | str | None = None,
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

        async def _update_task_tool(  # noqa: PLR0913
            ctx: ServerContext,
            id: str,  # noqa: A002
            name: str | None = None,
            note: str | None = None,
            area_id: str | None = None,
            status: str | None = None,
            priority: int | str | None = None,
            due_date: str | None = None,
            motivation: str | None = None,
            eisenhower: int | str | None = None,
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

        async def _delete_task_tool(ctx: ServerContext, id: str) -> dict[str, Any]:  # noqa: A002
            """Delete an existing task in LunaTask."""
            return await delete_task_tool_fn(self.lunatask_client, ctx, id)

        # Keep a non-breaking explicit discovery URI that maps to the same handler.
        self.mcp.resource("lunatask://tasks")(_tasks_discovery)
        self.mcp.resource("lunatask://tasks/discovery")(_tasks_discovery)
        self.mcp.resource("lunatask://tasks/{task_id}")(_task_single_resource)
        # Register area alias templates
        self.mcp.resource("lunatask://area/{area_id}/now")(_area_now)
        self.mcp.resource("lunatask://area/{area_id}/today")(_area_today)
        self.mcp.resource("lunatask://area/{area_id}/overdue")(_area_overdue)
        self.mcp.resource("lunatask://area/{area_id}/next-7-days")(_area_next7)
        self.mcp.resource("lunatask://area/{area_id}/high-priority")(_area_high)
        self.mcp.resource("lunatask://area/{area_id}/recent-completions")(_area_recent)

        # Register global alias resources
        async def _global_now(ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_global_alias_fn(self.lunatask_client, ctx, alias="now")

        async def _global_today(ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_global_alias_fn(self.lunatask_client, ctx, alias="today")

        async def _global_overdue(ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_global_alias_fn(self.lunatask_client, ctx, alias="overdue")

        async def _global_next7(ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_global_alias_fn(self.lunatask_client, ctx, alias="next_7_days")

        async def _global_high(ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_global_alias_fn(
                self.lunatask_client, ctx, alias="high_priority"
            )

        async def _global_recent(ctx: ServerContext) -> dict[str, Any]:
            return await list_tasks_global_alias_fn(
                self.lunatask_client, ctx, alias="recent_completions"
            )

        self.mcp.resource("lunatask://global/now")(_global_now)
        self.mcp.resource("lunatask://global/today")(_global_today)
        self.mcp.resource("lunatask://global/overdue")(_global_overdue)
        self.mcp.resource("lunatask://global/next-7-days")(_global_next7)
        self.mcp.resource("lunatask://global/high-priority")(_global_high)
        self.mcp.resource("lunatask://global/recent-completions")(_global_recent)
        self.mcp.tool("create_task")(_create_task_tool)
        self.mcp.tool("update_task")(_update_task_tool)
        self.mcp.tool("delete_task")(_delete_task_tool)
