"""Notes functionality mixin for LunaTask API client.

This module provides the NotesClientMixin class that handles note creation,
update, and deletion operations, designed to be composed with the base client.
"""

import json
import logging
import urllib.parse
from typing import TYPE_CHECKING

from pydantic import ValidationError

from lunatask_mcp.api.exceptions import LunaTaskAPIError, LunaTaskValidationError
from lunatask_mcp.api.models import NoteCreate, NoteResponse, NoteUpdate

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
            NoteResponse | None: Created note object from wrapped API response
            format {"note": {...}}, or None when the API returns 204 No Content
            due to an idempotent duplicate.

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
        except (TypeError, ValidationError) as error:
            logger.exception("Failed to parse created note response data")
            note_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error("notes", note_name=note_name) from error
        else:
            logger.debug("Successfully created note: %s", note.id)
            return note

    async def update_note(
        self: "BaseClientProtocol", note_id: str, update: NoteUpdate
    ) -> NoteResponse:
        """Update an existing note in the LunaTask API.

        Args:
            note_id: The unique identifier for the note to update (UUID)
            update: NoteUpdate object containing fields to update

        Returns:
            NoteResponse: Updated note object from wrapped API response
            format {"note": {...}}

        Raises:
            LunaTaskNotFoundError: Note not found (404)
            LunaTaskValidationError: Validation error (422)
            LunaTaskAuthenticationError: Invalid bearer token (401)
            LunaTaskRateLimitError: Rate limit exceeded (429)
            LunaTaskServerError: Server error occurred (5xx)
            LunaTaskServiceUnavailableError: Service unavailable (503)
            LunaTaskTimeoutError: Request timeout
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """
        json_data = json.loads(update.model_dump_json(exclude_none=True))

        response_data = await self.make_request("PUT", f"notes/{note_id}", data=json_data)

        try:
            note_payload = response_data["note"]
            note = NoteResponse(**note_payload)
        except KeyError as error:
            logger.exception("Failed to extract note from wrapped response format")
            raise LunaTaskAPIError.create_parse_error(
                f"notes/{note_id}", note_id=f"{note_id} - missing 'note' key"
            ) from error
        except (TypeError, ValidationError) as error:
            logger.exception("Failed to parse updated note response data")
            raise LunaTaskAPIError.create_parse_error(
                f"notes/{note_id}", note_id=note_id
            ) from error
        else:
            logger.debug("Successfully updated note: %s", note.id)
            return note

    async def delete_note(self: "BaseClientProtocol", note_id: str) -> NoteResponse:
        """Delete an existing note in the LunaTask API.

        Args:
            note_id: The unique identifier for the note to delete (UUID format).
                    Must not be empty or whitespace-only. Will be URL-encoded
                    before making the request.

        Returns:
            NoteResponse: Deleted note object from wrapped API response
            format {"note": {...}}, with deleted_at timestamp populated.

        Raises:
            LunaTaskValidationError: When note_id is empty or whitespace-only.
            LunaTaskNotFoundError: Note not found (404).
            LunaTaskAuthenticationError: Invalid bearer token (401).
            LunaTaskRateLimitError: Rate limit exceeded (429).
            LunaTaskServerError: Server error occurred (5xx).
            LunaTaskTimeoutError: Request timeout.
            LunaTaskNetworkError: Network connectivity error.
            LunaTaskAPIError: Other API errors including parse errors.
        """
        # Validate note_id before making request to prevent malformed URLs
        if not note_id or not note_id.strip():
            raise LunaTaskValidationError.empty_note_id()

        # URL-encode the note_id to handle special characters safely
        encoded_note_id = urllib.parse.quote(note_id, safe="")

        response_data = await self.make_request("DELETE", f"notes/{encoded_note_id}")

        try:
            note_payload = response_data["note"]
            note = NoteResponse(**note_payload)
        except KeyError as error:
            logger.exception("Failed to extract note from wrapped response format")
            raise LunaTaskAPIError.create_parse_error(
                "notes", note_id=f"{note_id} - missing 'note' key"
            ) from error
        except (TypeError, ValidationError) as error:
            logger.exception("Failed to parse deleted note response data")
            raise LunaTaskAPIError.create_parse_error("notes", note_id=note_id) from error
        else:
            logger.debug("Successfully deleted note: %s", note.id)
            return note
