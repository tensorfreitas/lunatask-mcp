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
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import NoteCreate

logger = logging.getLogger(__name__)


class NotesTools:
    """Note management tools providing MCP integrations for LunaTask notes."""

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize NotesTools with FastMCP instance and LunaTask client."""

        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_tools()

    async def create_note_tool(  # noqa: PLR0913, PLR0911, PLR0915, C901
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

        except LunaTaskValidationError as error:
            message = f"Note validation failed: {error}"
            await ctx.error(message)
            logger.warning("Note validation error: %s", error)
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        except LunaTaskSubscriptionRequiredError as error:
            message = f"Subscription required: {error}"
            await ctx.error(message)
            logger.warning("Subscription required during note creation: %s", error)
            return {
                "success": False,
                "error": "subscription_required",
                "message": message,
            }

        except LunaTaskAuthenticationError as error:
            message = f"Authentication failed: {error}"
            await ctx.error(message)
            logger.warning("Authentication error during note creation: %s", error)
            return {
                "success": False,
                "error": "authentication_error",
                "message": message,
            }

        except LunaTaskRateLimitError as error:
            message = f"Rate limit exceeded: {error}"
            await ctx.error(message)
            logger.warning("Rate limit exceeded during note creation: %s", error)
            return {
                "success": False,
                "error": "rate_limit_error",
                "message": message,
            }

        except (LunaTaskServerError, LunaTaskServiceUnavailableError) as error:
            message = f"Server error: {error}"
            await ctx.error(message)
            logger.warning("Server error during note creation: %s", error)
            return {
                "success": False,
                "error": "server_error",
                "message": message,
            }

        except LunaTaskTimeoutError as error:
            message = f"Request timeout: {error}"
            await ctx.error(message)
            logger.warning("Timeout during note creation: %s", error)
            return {
                "success": False,
                "error": "timeout_error",
                "message": message,
            }

        except LunaTaskNetworkError as error:
            message = f"Network error: {error}"
            await ctx.error(message)
            logger.warning("Network error during note creation: %s", error)
            return {
                "success": False,
                "error": "network_error",
                "message": message,
            }

        except LunaTaskAPIError as error:
            message = f"API error: {error}"
            await ctx.error(message)
            logger.warning("API error during note creation: %s", error)
            return {
                "success": False,
                "error": "api_error",
                "message": message,
            }

        except Exception as error:
            message = f"Unexpected error creating note: {error}"
            await ctx.error(message)
            logger.exception("Unexpected error during note creation")
            return {
                "success": False,
                "error": "unexpected_error",
                "message": message,
            }

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
