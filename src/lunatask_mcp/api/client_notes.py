"""Notes functionality mixin for LunaTask API client.

This module provides the NotesClientMixin class that handles note creation
operations, designed to be composed with the base client.
"""

import json
import logging
from typing import TYPE_CHECKING

from lunatask_mcp.api.exceptions import LunaTaskAPIError
from lunatask_mcp.api.models import NoteCreate, NoteResponse

if TYPE_CHECKING:
    from lunatask_mcp.api.protocols import BaseClientProtocol

logger = logging.getLogger(__name__)


class NotesClientMixin:
    """Mixin providing note creation functionality for the LunaTask API client."""

    async def create_note(self: "BaseClientProtocol", note_data: NoteCreate) -> NoteResponse | None:
        """Create a new note in the LunaTask API.

        Args:
            note_data: NoteCreate object containing note data to create.

        Returns:
            NoteResponse | None: Created note object from the API, or None when
            the API returns 204 No Content due to an idempotent duplicate.

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
        json_data = json.loads(note_data.model_dump_json(exclude_none=True))

        response_data = await self.make_request("POST", "notes", data=json_data)

        if not response_data:
            logger.debug(
                "Note creation returned no content; assuming duplicate for source/source_id"
            )
            return None

        try:
            note_payload = response_data["note"]
            note = NoteResponse(**note_payload)
        except KeyError as error:
            logger.exception("Failed to extract note from wrapped response format")
            note_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error(
                "notes", note_name=f"{note_name} - missing 'note' key"
            ) from error
        except Exception as error:
            logger.exception("Failed to parse created note response data")
            note_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error("notes", note_name=note_name) from error
        else:
            logger.debug("Successfully created note: %s", note.id)
            return note
