"""Journal functionality mixin for LunaTask API client.

This module provides the JournalClientMixin class that handles journal entry
creation operations, designed to be composed with the base client.
"""

import json
import logging
from typing import TYPE_CHECKING

from lunatask_mcp.api.exceptions import LunaTaskAPIError
from lunatask_mcp.api.models import JournalEntryCreate, JournalEntryResponse

if TYPE_CHECKING:
    from lunatask_mcp.api.protocols import BaseClientProtocol

logger = logging.getLogger(__name__)


class JournalClientMixin:
    """Mixin providing journal entry functionality for the LunaTask API client."""

    async def create_journal_entry(
        self: "BaseClientProtocol", entry_data: JournalEntryCreate
    ) -> JournalEntryResponse:
        """Create a new journal entry in the LunaTask API.

        Args:
            entry_data: JournalEntryCreate object containing journal entry data.

        Returns:
            JournalEntryResponse: Created journal entry returned by the API.

        Raises:
            LunaTaskValidationError: Validation error (422)
            LunaTaskSubscriptionRequiredError: Subscription required (402)
            LunaTaskAuthenticationError: Invalid bearer token (401)
            LunaTaskRateLimitError: Rate limit exceeded (429)
            LunaTaskServerError: Server error occurred (5xx)
            LunaTaskServiceUnavailableError: Service unavailable (503)
            LunaTaskTimeoutError: Request timeout
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """
        json_data = json.loads(entry_data.model_dump_json(exclude_none=True))

        response_data = await self.make_request("POST", "journal_entries", data=json_data)

        try:
            entry_payload = response_data["journal_entry"]
            entry = JournalEntryResponse(**entry_payload)
        except KeyError as error:
            logger.exception("Failed to extract journal entry from wrapped response format")
            entry_date = json_data.get("date_on", "unknown")
            raise LunaTaskAPIError.create_parse_error(
                "journal_entries",
                date_on=entry_date,
                detail="missing 'journal_entry' key",
            ) from error
        except Exception as error:
            logger.exception("Failed to parse created journal entry response data")
            entry_date = json_data.get("date_on", "unknown")
            raise LunaTaskAPIError.create_parse_error(
                "journal_entries", date_on=entry_date
            ) from error
        else:
            logger.debug("Successfully created journal entry: %s", entry.id)
            return entry
