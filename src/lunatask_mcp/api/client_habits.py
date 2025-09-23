"""Habits functionality mixin for LunaTask API client.

This module provides the HabitsClientMixin class that handles habit tracking
operations, designed to be composed with the base client.
"""

import logging
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lunatask_mcp.api.protocols import BaseClientProtocol

logger = logging.getLogger(__name__)


class HabitsClientMixin:
    """Mixin providing habit tracking functionality for the LunaTask API client."""

    async def track_habit(self: "BaseClientProtocol", habit_id: str, track_date: date) -> None:
        """Track an activity for a specific habit on a given date.

        Args:
            habit_id: The ID of the habit to track
            track_date: The date when the habit was performed

        Raises:
            LunaTaskAuthenticationError: Authentication failed
            LunaTaskNotFoundError: Habit not found
            LunaTaskValidationError: Invalid date format
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error
            LunaTaskTimeoutError: Request timeout
            LunaTaskNetworkError: Network connectivity error
        """
        await self.make_request(
            "POST", f"habits/{habit_id}/track", data={"performed_on": track_date.isoformat()}
        )
        logger.debug("Successfully tracked habit: %s on %s", habit_id, track_date.isoformat())
