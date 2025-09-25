"""Person timeline notes functionality mixin for the LunaTask API client.

This module exposes a mixin providing the capability to create timeline notes
associated with people in LunaTask.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from lunatask_mcp.api.exceptions import LunaTaskAPIError
from lunatask_mcp.api.models_people import (
    PersonTimelineNoteCreate,
    PersonTimelineNoteResponse,
)

if TYPE_CHECKING:
    from lunatask_mcp.api.protocols import BaseClientProtocol

logger = logging.getLogger(__name__)


class PersonTimelineNotesClientMixin:
    """Mixin providing person timeline note creation functionality."""

    async def create_person_timeline_note(
        self: BaseClientProtocol, payload: PersonTimelineNoteCreate
    ) -> PersonTimelineNoteResponse:
        """Create a person timeline note through the LunaTask API.

        Args:
            payload: PersonTimelineNoteCreate object describing the note.

        Returns:
            PersonTimelineNoteResponse: Parsed response for the created note.

        Raises:
            LunaTaskValidationError: Validation error (422)
            LunaTaskSubscriptionRequiredError: Subscription required (402)
            LunaTaskAuthenticationError: Invalid bearer token (401)
            LunaTaskRateLimitError: Rate limit exceeded (429)
            LunaTaskServerError: Server error occurred (5xx)
            LunaTaskServiceUnavailableError: Service unavailable (503)
            LunaTaskTimeoutError: Request timeout
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors or parse failures
        """

        json_payload = json.loads(payload.model_dump_json(exclude_none=True))
        response_data = await self.make_request("POST", "person_timeline_notes", data=json_payload)

        try:
            note_data = response_data["person_timeline_note"]
            note = PersonTimelineNoteResponse(**note_data)
        except KeyError as error:
            logger.exception("Missing person_timeline_note wrapper in response payload")
            raise LunaTaskAPIError.create_parse_error(
                "person_timeline_notes", person_id=json_payload.get("person_id", "unknown")
            ) from error
        except Exception as error:
            logger.exception("Failed to parse person timeline note response payload")
            raise LunaTaskAPIError.create_parse_error(
                "person_timeline_notes", person_id=json_payload.get("person_id", "unknown")
            ) from error

        logger.debug("Created person timeline note %s", note.id)
        return note
