"""Note management tools for LunaTask MCP integration."""

from __future__ import annotations

import logging
from datetime import date as date_class
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.context import Context as ServerContext

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import NoteCreate, NoteUpdate

logger = logging.getLogger(__name__)


class NotesTools:
    """Note management tools providing MCP integrations for LunaTask notes."""

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize NotesTools with FastMCP instance and LunaTask client."""

        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_tools()

    async def _handle_lunatask_api_errors(  # noqa: PLR0911
        self,
        ctx: ServerContext,
        error: Exception,
        operation: str,
    ) -> dict[str, Any]:
        """Handle common LunaTask API errors and return structured error response.

        Args:
            ctx: Server context for logging
            error: The caught exception
            operation: Description of operation (e.g., "note creation", "note update")

        Returns:
            Dictionary with error response structure
        """
        if isinstance(error, LunaTaskValidationError):
            message = f"Note validation failed: {error}"
            await ctx.error(message)
            logger.warning("Validation error during %s: %s", operation, error)
            return {"success": False, "error": "validation_error", "message": message}

        if isinstance(error, LunaTaskNotFoundError):
            message = f"Note not found: {error}"
            await ctx.error(message)
            logger.warning("Not found error during %s: %s", operation, error)
            return {"success": False, "error": "not_found_error", "message": message}

        if isinstance(error, LunaTaskSubscriptionRequiredError):
            message = f"Subscription required: {error}"
            await ctx.error(message)
            logger.warning("Subscription required during %s: %s", operation, error)
            return {"success": False, "error": "subscription_required", "message": message}

        if isinstance(error, LunaTaskAuthenticationError):
            message = f"Authentication failed: {error}"
            await ctx.error(message)
            logger.warning("Authentication error during %s: %s", operation, error)
            return {"success": False, "error": "authentication_error", "message": message}

        if isinstance(error, LunaTaskRateLimitError):
            message = f"Rate limit exceeded: {error}"
            await ctx.error(message)
            logger.warning("Rate limit exceeded during %s: %s", operation, error)
            return {"success": False, "error": "rate_limit_error", "message": message}

        if isinstance(error, (LunaTaskServerError, LunaTaskServiceUnavailableError)):
            message = f"Server error: {error}"
            await ctx.error(message)
            logger.warning("Server error during %s: %s", operation, error)
            return {"success": False, "error": "server_error", "message": message}

        if isinstance(error, LunaTaskTimeoutError):
            message = f"Request timeout: {error}"
            await ctx.error(message)
            logger.warning("Timeout during %s: %s", operation, error)
            return {"success": False, "error": "timeout_error", "message": message}

        if isinstance(error, LunaTaskNetworkError):
            message = f"Network error: {error}"
            await ctx.error(message)
            logger.warning("Network error during %s: %s", operation, error)
            return {"success": False, "error": "network_error", "message": message}

        if isinstance(error, LunaTaskAPIError):
            message = f"API error: {error}"
            await ctx.error(message)
            logger.warning("API error during %s: %s", operation, error)
            return {"success": False, "error": "api_error", "message": message}

        # Handle unexpected errors
        message = f"Unexpected error during {operation}: {error}"
        await ctx.error(message)
        logger.exception("Unexpected error during %s", operation)
        return {"success": False, "error": "unexpected_error", "message": message}

    async def create_note_tool(  # noqa: PLR0913
        self,
        ctx: ServerContext,
        notebook_id: str | None = None,
        name: str | None = None,
        content: str | None = None,
        date_on: str | None = None,
        source: str | None = None,
        source_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a note in LunaTask with optional duplicate detection."""

        await ctx.info("Creating new note")

        parsed_date: date_class | None = None
        if date_on is not None:
            try:
                parsed_date = date_class.fromisoformat(date_on)
            except ValueError as error:
                message = f"Invalid date_on format. Expected YYYY-MM-DD format: {error!s}"
                await ctx.error(message)
                logger.warning("Invalid date_on provided for create_note: %s", date_on)
                return {
                    "success": False,
                    "error": "validation_error",
                    "message": message,
                }

        note_payload = NoteCreate(
            notebook_id=notebook_id,
            name=name,
            content=content,
            date_on=parsed_date,
            source=source,
            source_id=source_id,
        )

        try:
            async with self.lunatask_client as client:
                note_response = await client.create_note(note_payload)
        except Exception as error:
            return await self._handle_lunatask_api_errors(ctx, error, "note creation")

        if note_response is None:
            duplicate_message = (
                "Note already exists for this source/source_id in the provided notebook"
            )
            await ctx.info("Note already exists; duplicate create skipped")
            logger.info("Duplicate note detected for notebook=%s", notebook_id)
            return {
                "success": True,
                "duplicate": True,
                "message": duplicate_message,
            }

        await ctx.info(f"Successfully created note {note_response.id}")
        logger.info("Successfully created note %s", note_response.id)
        return {
            "success": True,
            "note_id": note_response.id,
            "message": "Note created successfully",
        }

    async def update_note_tool(  # noqa: PLR0913
        self,
        ctx: ServerContext,
        note_id: str,
        name: str | None = None,
        content: str | None = None,
        notebook_id: str | None = None,
        date_on: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing note in LunaTask.

        Args:
            ctx: MCP context for logging and communication
            note_id: Note ID to update (required, UUID format)
            name: Updated note name/title (optional)
            content: Updated note content - replaces entire content (optional)
            notebook_id: Updated notebook ID to move note (optional)
            date_on: Updated note date in YYYY-MM-DD format (optional)

        Returns:
            dict[str, Any]: Response with note update result
        """
        # Validate required note ID
        if not note_id or not note_id.strip():
            error_msg = "Note ID cannot be empty"
            await ctx.error(error_msg)
            logger.warning("Empty note_id provided for update")
            return {"success": False, "error": "validation_error", "message": error_msg}

        # Validate at least one field provided
        update_fields = [name, content, notebook_id, date_on]
        if all(field is None for field in update_fields):
            error_msg = "At least one field must be provided for update"
            await ctx.error(error_msg)
            logger.warning("No fields provided for note update: %s", note_id)
            return {"success": False, "error": "validation_error", "message": error_msg}

        # Parse and validate date_on if provided
        parsed_date: date_class | None = None
        if date_on is not None:
            try:
                parsed_date = date_class.fromisoformat(date_on)
            except ValueError as error:
                error_msg = f"Invalid date_on format. Expected YYYY-MM-DD: {error!s}"
                await ctx.error(error_msg)
                logger.warning("Invalid date_on for note %s: %s", note_id, date_on)
                return {"success": False, "error": "validation_error", "message": error_msg}

        await ctx.info(f"Updating note {note_id}")

        try:
            # Build kwargs for PATCH semantics
            update_kwargs: dict[str, Any] = {"id": note_id}
            if name is not None:
                update_kwargs["name"] = name
            if content is not None:
                update_kwargs["content"] = content
            if notebook_id is not None:
                update_kwargs["notebook_id"] = notebook_id
            if parsed_date is not None:
                update_kwargs["date_on"] = parsed_date

            note_update = NoteUpdate(**update_kwargs)

            async with self.lunatask_client as client:
                updated_note = await client.update_note(note_id, note_update)

            await ctx.info(f"Successfully updated note {note_id}")
            logger.info("Successfully updated note %s", note_id)
            return {
                "success": True,
                "note_id": note_id,
                "message": "Note updated successfully",
                "note": {
                    "id": updated_note.id,
                    "notebook_id": updated_note.notebook_id,
                    "date_on": updated_note.date_on.isoformat() if updated_note.date_on else None,
                    "created_at": updated_note.created_at.isoformat(),
                    "updated_at": updated_note.updated_at.isoformat(),
                },
            }
        except Exception as error:
            return await self._handle_lunatask_api_errors(ctx, error, "note update")

    async def delete_note_tool(
        self,
        ctx: ServerContext,
        note_id: str,
    ) -> dict[str, Any]:
        """Delete a note in LunaTask.

        Args:
            ctx: Server context for logging and communication
            note_id: ID of the note to delete (UUID format)

        Returns:
            Dictionary with success status, note_id, deleted_at timestamp, and message.
        """
        # Strip whitespace once at the beginning
        note_id = note_id.strip()

        await ctx.info(f"Deleting note {note_id}")

        # Validate note ID before making API call
        if not note_id:
            message = "Note ID cannot be empty"
            await ctx.error(message)
            logger.warning("Empty note ID provided for note deletion")
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        try:
            async with self.lunatask_client as client:
                note_response = await client.delete_note(note_id)

        except Exception as error:
            return await self._handle_lunatask_api_errors(ctx, error, "note deletion")

        await ctx.info(f"Successfully deleted note {note_response.id}")
        logger.info("Successfully deleted note %s", note_response.id)
        return {
            "success": True,
            "note_id": note_response.id,
            "deleted_at": note_response.deleted_at.isoformat()
            if note_response.deleted_at
            else None,
            "message": "Note deleted successfully",
        }

    def _register_tools(self) -> None:
        """Register note-related MCP tools with the FastMCP instance."""

        async def _create_note(  # noqa: PLR0913
            ctx: ServerContext,
            notebook_id: str | None = None,
            name: str | None = None,
            content: str | None = None,
            date_on: str | None = None,
            source: str | None = None,
            source_id: str | None = None,
        ) -> dict[str, Any]:
            return await self.create_note_tool(
                ctx,
                notebook_id,
                name,
                content,
                date_on,
                source,
                source_id,
            )

        self.mcp.tool(
            name="create_note",
            description=(
                "Create a note in LunaTask. Accepts notebook_id, optional name/content, "
                "an ISO date_on, and optional source/source_id metadata for duplicate "
                "detection. Returns note_id or duplicate status."
            ),
        )(_create_note)

        async def _update_note(  # noqa: PLR0913
            ctx: ServerContext,
            note_id: str,
            name: str | None = None,
            content: str | None = None,
            notebook_id: str | None = None,
            date_on: str | None = None,
        ) -> dict[str, Any]:
            return await self.update_note_tool(ctx, note_id, name, content, notebook_id, date_on)

        self.mcp.tool(
            name="update_note",
            description=(
                "Update an existing note in LunaTask. Requires note_id (UUID). "
                "Optional fields: name, content (replaces entire content due to E2E encryption), "
                "notebook_id (to move note), date_on (YYYY-MM-DD). "
                "At least one field must be provided. Returns updated note data."
            ),
        )(_update_note)

        async def _delete_note(
            ctx: ServerContext,
            note_id: str,
        ) -> dict[str, Any]:
            return await self.delete_note_tool(ctx, note_id)

        self.mcp.tool(
            name="delete_note",
            description=(
                "Delete a note in LunaTask by note_id. Requires note_id (UUID). "
                "Returns success status with note_id and deleted_at timestamp. "
                "Note: deletion is not idempotent - second delete will return not found error."
            ),
        )(_delete_note)
