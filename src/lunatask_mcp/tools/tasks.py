"""Task management tools for LunaTask MCP integration.

This module provides MCP resources for accessing and managing LunaTask tasks
through the Model Context Protocol, enabling AI models to interact with task data.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskAPIError

# Configure logger to write to stderr
logger = logging.getLogger(__name__)


class TaskTools:
    """Task management tools providing MCP resources for LunaTask integration.

    This class encapsulates task-related MCP resources, enabling AI models
    to retrieve and work with task data from LunaTask through standardized
    MCP resource URIs.
    """

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize TaskTools with MCP instance and LunaTask client.

        Args:
            mcp_instance: FastMCP server instance for registering resources
            lunatask_client: LunaTask API client for data retrieval
        """
        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_resources()

    def _register_resources(self) -> None:
        """Register all task-related MCP resources with the FastMCP instance."""
        self.mcp.resource("lunatask://tasks")(self.get_tasks_resource)

    async def get_tasks_resource(self, ctx: Context) -> dict[str, Any]:
        """MCP resource providing access to all LunaTask tasks.

        This resource retrieves all tasks from the LunaTask API and presents them
        as a structured JSON resource accessible via the URI 'lunatask://tasks'.

        Args:
            ctx: MCP context providing logging and execution context

        Returns:
            dict[str, Any]: JSON structure containing task data with metadata

        Raises:
            LunaTaskAPIError: If the LunaTask API request fails
        """
        try:
            await ctx.info("Retrieving tasks from LunaTask API")

            # Use the LunaTaskClient to fetch all tasks
            async with self.lunatask_client:
                tasks = await self.lunatask_client.get_tasks()

            # Convert TaskResponse objects to dictionaries for JSON serialization
            task_data = [
                {
                    "id": task.id,
                    "area_id": task.area_id,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "source": {
                        "type": task.source.type,
                        "value": task.source.value,
                    }
                    if task.source
                    else None,
                    "tags": task.tags,
                }
                for task in tasks
            ]

            resource_data = {
                "resource_type": "lunatask_tasks",
                "total_count": len(tasks),
                "tasks": task_data,
                "metadata": {
                    "retrieved_at": ctx.session_id if hasattr(ctx, "session_id") else "unknown",
                    "encrypted_fields_note": (
                        "Task names and notes are not included due to E2E encryption"
                    ),
                },
            }

        except LunaTaskAPIError as e:
            error_msg = f"Failed to retrieve tasks from LunaTask API: {e}"
            logger.exception(error_msg)
            await ctx.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"Unexpected error retrieving tasks: {e}"
            logger.exception(error_msg)
            await ctx.error(error_msg)
            raise LunaTaskAPIError(error_msg) from e
        else:
            await ctx.info(f"Successfully retrieved {len(tasks)} tasks from LunaTask")
            return resource_data
