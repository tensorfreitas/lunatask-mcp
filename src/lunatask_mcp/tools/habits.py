"""Habit management tools for LunaTask MCP integration.

This module provides the HabitTools class which implements MCP tools for habit
tracking operations with the LunaTask API.
"""

import logging
from datetime import date as date_class
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.context import Context as ServerContext

from lunatask_mcp.api.client import LunaTaskClient

# Configure logger to write to stderr
logger = logging.getLogger(__name__)


class HabitTools:
    """Habit management tools providing MCP tools for LunaTask integration.

    This class encapsulates habit-related MCP tools, enabling AI models
    to track habit activities in LunaTask through standardized MCP tool calls.
    """

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize HabitTools with MCP instance and LunaTask client.

        Args:
            mcp_instance: FastMCP server instance for registering tools
            lunatask_client: LunaTask API client for data operations
        """
        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_tools()

    async def track_habit_tool(
        self,
        ctx: ServerContext,  # noqa: ARG002  # Required for MCP tool signature
        id: str,  # noqa: A002  # Required by MCP tool API - habit ID parameter
        date: str,  # Required by MCP tool API - date parameter
    ) -> dict[str, Any]:
        """Track an activity for a specific habit on a given date.

        Args:
            ctx: Server context for logging
            id: The ID of the habit to track
            date: The date when the habit was performed in ISO-8601 format (YYYY-MM-DD)

        Returns:
            Dict[str, Any]: Success response with confirmation message

        Raises:
            ValueError: If date format is invalid
            LunaTaskAuthenticationError: Authentication failed
            LunaTaskNotFoundError: Habit not found
            LunaTaskValidationError: Invalid parameters
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error
            LunaTaskTimeoutError: Request timeout
            LunaTaskNetworkError: Network connectivity error
        """
        # Parse the date string to validate format and convert to date object
        try:
            parsed_date = date_class.fromisoformat(date)
        except ValueError as e:
            logger.exception("Invalid date format provided: %s", date)
            msg = f"Invalid date format: {date}. Expected YYYY-MM-DD format"
            raise ValueError(msg) from e

        # Assign to local variable to avoid builtin shadowing in the rest of the method
        habit_id = id

        # Call the client method to track the habit
        await self.lunatask_client.track_habit(habit_id, parsed_date)

        # Log successful tracking
        logger.info("Successfully tracked habit %s on %s", habit_id, date)

        # Return success response
        return {"ok": True, "message": f"Successfully tracked habit {habit_id} on {date}"}

    def _register_tools(self) -> None:
        """Register all habit-related MCP tools with the FastMCP instance."""

        # Wrapper function to inject dependencies and satisfy FastMCP signature
        async def _track_habit(ctx: ServerContext, id: str, date: str) -> dict[str, Any]:  # noqa: A002
            """MCP tool wrapper for track_habit_tool."""
            return await self.track_habit_tool(ctx, id, date)

        # Register the track_habit tool with FastMCP
        self.mcp.tool(
            name="track_habit", description="Track an activity for a specific habit on a given date"
        )(_track_habit)
