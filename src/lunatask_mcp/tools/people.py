"""People/contact management tools for LunaTask MCP integration."""

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
from lunatask_mcp.api.models_people import (
    PersonCreate,
    PersonRelationshipStrength,
    PersonTimelineNoteCreate,
)

logger = logging.getLogger(__name__)


class PeopleTools:
    """People/contact management tools providing MCP integrations for LunaTask people."""

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize PeopleTools with FastMCP instance and LunaTask client.

        Args:
            mcp_instance: FastMCP instance for registering tools
            lunatask_client: LunaTask API client for making requests
        """

        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_tools()

    async def _handle_lunatask_api_errors(  # noqa: C901, PLR0911, PLR0912, PLR0915
        self, ctx: ServerContext, error: Exception, operation: str
    ) -> dict[str, Any]:
        """Handle common LunaTask API errors and return structured error response.

        Args:
            ctx: Server context for logging
            error: The caught exception
            operation: Description of the operation for error messages (e.g., "person creation")

        Returns:
            Dictionary with error response structure
        """
        if isinstance(error, LunaTaskValidationError):
            if "person creation" in operation:
                message = f"Person validation failed: {error}"
            elif "timeline note" in operation:
                message = f"Timeline note validation failed: {error}"
            else:
                message = f"Validation failed: {error}"
            await ctx.error(message)
            logger.warning("Validation error during %s: %s", operation, error)
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        if isinstance(error, LunaTaskNotFoundError):
            if "person deletion" in operation:
                message = f"Person not found: {error}"
            elif "timeline note" in operation:
                message = f"Timeline note not found: {error}"
            elif "person creation" in operation:
                message = f"Person not found: {error}"
            else:
                message = f"Resource not found: {error}"
            await ctx.error(message)
            logger.warning("Not found error during %s: %s", operation, error)
            return {
                "success": False,
                "error": "not_found_error",
                "message": message,
            }

        if isinstance(error, LunaTaskSubscriptionRequiredError):
            message = f"Subscription required: {error}"
            await ctx.error(message)
            logger.warning("Subscription required during %s: %s", operation, error)
            return {
                "success": False,
                "error": "subscription_required",
                "message": message,
            }

        if isinstance(error, LunaTaskAuthenticationError):
            message = f"Authentication failed: {error}"
            await ctx.error(message)
            logger.warning("Authentication error during %s: %s", operation, error)
            return {
                "success": False,
                "error": "authentication_error",
                "message": message,
            }

        if isinstance(error, LunaTaskRateLimitError):
            message = f"Rate limit exceeded: {error}"
            await ctx.error(message)
            logger.warning("Rate limit exceeded during %s: %s", operation, error)
            return {
                "success": False,
                "error": "rate_limit_error",
                "message": message,
            }

        if isinstance(error, (LunaTaskServerError, LunaTaskServiceUnavailableError)):
            message = f"Server error: {error}"
            await ctx.error(message)
            logger.warning("Server error during %s: %s", operation, error)
            return {
                "success": False,
                "error": "server_error",
                "message": message,
            }

        if isinstance(error, LunaTaskTimeoutError):
            message = f"Request timeout: {error}"
            await ctx.error(message)
            logger.warning("Timeout during %s: %s", operation, error)
            return {
                "success": False,
                "error": "timeout_error",
                "message": message,
            }

        if isinstance(error, LunaTaskNetworkError):
            message = f"Network error: {error}"
            await ctx.error(message)
            logger.warning("Network error during %s: %s", operation, error)
            return {
                "success": False,
                "error": "network_error",
                "message": message,
            }

        if isinstance(error, LunaTaskAPIError):
            message = f"API error: {error}"
            await ctx.error(message)
            logger.warning("API error during %s: %s", operation, error)
            return {
                "success": False,
                "error": "api_error",
                "message": message,
            }

        # Handle unexpected errors
        if "person creation" in operation:
            message = f"Unexpected error creating person: {error}"
        elif "person deletion" in operation:
            message = f"Unexpected error during person deletion: {error}"
        elif "timeline note" in operation:
            message = f"Unexpected error creating timeline note: {error}"
        else:
            message = f"Unexpected error during {operation}: {error}"
        await ctx.error(message)
        logger.exception("Unexpected error during %s", operation)
        return {
            "success": False,
            "error": "unexpected_error",
            "message": message,
        }

    async def create_person_tool(  # noqa: PLR0913
        self,
        ctx: ServerContext,
        first_name: str,
        last_name: str,
        relationship_strength: str | None = None,
        source: str | None = None,
        source_id: str | None = None,
        email: str | None = None,
        birthday: str | None = None,
        phone: str | None = None,
    ) -> dict[str, Any]:
        """Create a person in LunaTask with optional duplicate detection.

        Args:
            ctx: Server context for logging and communication
            first_name: Person's first name
            last_name: Person's last name
            relationship_strength: Optional relationship strength enum value
            source: Optional source identifier for duplicate detection
            source_id: Optional source-specific ID for duplicate detection
            email: Optional email address
            birthday: Optional birthday in YYYY-MM-DD format
            phone: Optional phone number

        Returns:
            Dictionary with success status, person_id (if created), and message.
            May include 'duplicate' flag if person already exists.
        """

        await ctx.info("Creating new person")

        # Validate and convert relationship_strength
        parsed_relationship_strength = PersonRelationshipStrength.CASUAL_FRIENDS
        if relationship_strength is not None:
            try:
                parsed_relationship_strength = PersonRelationshipStrength(relationship_strength)
            except ValueError:
                valid_values = ", ".join([e.value for e in PersonRelationshipStrength])
                message = (
                    f"Invalid relationship_strength '{relationship_strength}'. "
                    f"Must be one of: {valid_values}"
                )
                await ctx.error(message)
                logger.warning("Invalid relationship_strength provided: %s", relationship_strength)
                return {
                    "success": False,
                    "error": "validation_error",
                    "message": message,
                }

        # Parse birthday if provided
        parsed_birthday: date_class | None = None
        if birthday is not None:
            try:
                parsed_birthday = date_class.fromisoformat(birthday)
            except ValueError as error:
                message = f"Invalid birthday format. Expected YYYY-MM-DD format: {error!s}"
                await ctx.error(message)
                logger.warning("Invalid birthday provided for create_person: %s", birthday)
                return {
                    "success": False,
                    "error": "validation_error",
                    "message": message,
                }

        person_payload = PersonCreate(
            first_name=first_name,
            last_name=last_name,
            relationship_strength=parsed_relationship_strength,
            source=source,
            source_id=source_id,
            email=email,
            birthday=parsed_birthday,
            phone=phone,
        )

        try:
            async with self.lunatask_client as client:
                person_response = await client.create_person(person_payload)

        except Exception as error:
            return await self._handle_lunatask_api_errors(ctx, error, "person creation")

        if person_response is None:
            duplicate_message = "Person already exists for this source/source_id"
            await ctx.info("Person already exists; duplicate create skipped")
            logger.info("Duplicate person detected for source=%s, source_id=%s", source, source_id)
            return {
                "success": True,
                "duplicate": True,
                "message": duplicate_message,
            }

        await ctx.info(f"Successfully created person {person_response.id}")
        logger.info("Successfully created person %s", person_response.id)
        return {
            "success": True,
            "person_id": person_response.id,
            "message": "Person created successfully",
        }

    async def create_person_timeline_note_tool(
        self,
        ctx: ServerContext,
        person_id: str,
        content: str,
        date_on: str | None = None,
    ) -> dict[str, Any]:
        """Create a timeline note for a person in LunaTask.

        Args:
            ctx: Server context for logging and communication
            person_id: ID of the person to add the timeline note to
            content: Content of the timeline note
            date_on: Optional date in YYYY-MM-DD format to associate with the note

        Returns:
            Dictionary with success status, person_timeline_note_id, and message.
        """

        await ctx.info("Creating person timeline note")

        if not person_id.strip():
            message = "person_id is required to create a timeline note"
            await ctx.error(message)
            logger.warning("Missing person_id for person timeline note creation")
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        if content.strip() == "":
            message = "content cannot be empty when creating a timeline note"
            await ctx.error(message)
            logger.warning("Empty content provided for person timeline note creation")
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        parsed_date: date_class | None = None
        if date_on is not None:
            try:
                parsed_date = date_class.fromisoformat(date_on)
            except ValueError as error:
                message = f"Invalid date_on format. Expected YYYY-MM-DD format: {error!s}"
                await ctx.error(message)
                logger.warning("Invalid date_on provided for person timeline note: %s", date_on)
                return {
                    "success": False,
                    "error": "validation_error",
                    "message": message,
                }

        note_payload = PersonTimelineNoteCreate(
            person_id=person_id,
            content=content.strip(),
            date_on=parsed_date,
        )

        try:
            async with self.lunatask_client as client:
                note_response = await client.create_person_timeline_note(note_payload)

        except Exception as error:
            return await self._handle_lunatask_api_errors(ctx, error, "timeline note creation")

        await ctx.info(f"Person timeline note created: {note_response.id}")
        logger.info("Created person timeline note %s", note_response.id)
        return {
            "success": True,
            "person_timeline_note_id": note_response.id,
            "message": "Person timeline note created successfully",
        }

    async def delete_person_tool(
        self,
        ctx: ServerContext,
        person_id: str,
    ) -> dict[str, Any]:
        """Delete a person in LunaTask.

        Args:
            ctx: Server context for logging and communication
            person_id: ID of the person to delete

        Returns:
            Dictionary with success status, person_id, deleted_at timestamp, and message.
        """

        # Strip whitespace once at the beginning
        person_id = person_id.strip()

        await ctx.info(f"Deleting person {person_id}")

        # Validate person ID before making API call
        if not person_id:
            message = "Person ID cannot be empty"
            await ctx.error(message)
            logger.warning("Empty person ID provided for person deletion")
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        try:
            async with self.lunatask_client as client:
                person_response = await client.delete_person(person_id)

        except Exception as error:
            return await self._handle_lunatask_api_errors(ctx, error, "person deletion")

        await ctx.info(f"Successfully deleted person {person_response.id}")
        logger.info("Successfully deleted person %s", person_response.id)
        return {
            "success": True,
            "person_id": person_response.id,
            "deleted_at": person_response.deleted_at.isoformat()
            if person_response.deleted_at
            else None,
            "message": "Person deleted successfully",
        }

    def _register_tools(self) -> None:
        """Register people-related MCP tools with the FastMCP instance.

        Registers create_person, create_person_timeline_note, and delete_person tools
        with their respective descriptions and parameter validation.
        """

        async def _create_person(  # noqa: PLR0913
            ctx: ServerContext,
            first_name: str,
            last_name: str,
            relationship_strength: str | None = None,
            source: str | None = None,
            source_id: str | None = None,
            email: str | None = None,
            birthday: str | None = None,
            phone: str | None = None,
        ) -> dict[str, Any]:
            return await self.create_person_tool(
                ctx,
                first_name,
                last_name,
                relationship_strength,
                source,
                source_id,
                email,
                birthday,
                phone,
            )

        valid_strengths = ", ".join([e.value for e in PersonRelationshipStrength])
        self.mcp.tool(
            name="create_person",
            description=(
                f"Create a person/contact in LunaTask. Requires first_name and last_name. "
                f"Optional relationship_strength ({valid_strengths}), "
                f"source/source_id for duplicate detection, email, birthday (YYYY-MM-DD), "
                f"and phone. Returns person_id or duplicate status."
            ),
        )(_create_person)

        async def _create_person_timeline_note(
            ctx: ServerContext,
            person_id: str,
            content: str,
            date_on: str | None = None,
        ) -> dict[str, Any]:
            return await self.create_person_timeline_note_tool(ctx, person_id, content, date_on)

        self.mcp.tool(
            name="create_person_timeline_note",
            description=(
                "Create a timeline note for a person in LunaTask. Requires person_id and content. "
                "Optional date_on (YYYY-MM-DD) to associate the note with a specific day."
            ),
        )(_create_person_timeline_note)

        async def _delete_person(
            ctx: ServerContext,
            person_id: str,
        ) -> dict[str, Any]:
            return await self.delete_person_tool(ctx, person_id)

        self.mcp.tool(
            name="delete_person",
            description=(
                "Delete a person/contact in LunaTask by person_id. Requires person_id. "
                "Returns success status with person_id and deleted_at timestamp. "
                "Note: deletion is not idempotent - second delete will return not found error."
            ),
        )(_delete_person)
