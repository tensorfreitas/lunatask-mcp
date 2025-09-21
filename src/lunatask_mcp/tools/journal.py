"""Journal tools providing MCP integrations for LunaTask journal entries."""

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
from lunatask_mcp.api.models import JournalEntryCreate

logger = logging.getLogger(__name__)


class JournalTools:
    """MCP tools that create journal entries via the LunaTask API."""

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize JournalTools with MCP instance and LunaTask client."""

        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_tools()

    # TODO: Refactor to have less return statements
    async def create_journal_entry_tool(  # noqa: PLR0911, PLR0915, C901
        self,
        ctx: ServerContext,
        *,
        date_on: str,
        name: str | None = None,
        content: str | None = None,
    ) -> dict[str, Any]:
        """Create a LunaTask journal entry for the provided date.

        Args:
            ctx: FastMCP execution context used for structured logging.
            date_on: ISO-8601 (YYYY-MM-DD) date that the journal entry belongs to.
            name: Optional title for the journal entry.
            content: Optional Markdown body for the journal entry.

        Returns:
            dict[str, Any]: Structured result containing a success flag, optional
            `journal_entry_id`, and a human-readable message or error details.
        """

        await ctx.info("Creating journal entry")

        try:
            parsed_date = date_class.fromisoformat(date_on)
        except ValueError as error:
            message = f"Invalid date_on format. Expected YYYY-MM-DD format: {error!s}"
            await ctx.error(message)
            logger.warning("Invalid date_on provided for create_journal_entry: %s", date_on)
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        entry_payload = JournalEntryCreate(
            date_on=parsed_date,
            name=name,
            content=content,
        )

        try:
            async with self.lunatask_client as client:
                journal_entry = await client.create_journal_entry(entry_payload)
        except LunaTaskValidationError as error:
            message = f"Journal entry validation failed: {error}"
            await ctx.error(message)
            logger.warning("Journal entry validation error: %s", error)
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }
        except LunaTaskSubscriptionRequiredError as error:
            message = f"Subscription required: {error}"
            await ctx.error(message)
            logger.warning("Subscription required during journal entry creation: %s", error)
            return {
                "success": False,
                "error": "subscription_required",
                "message": message,
            }
        except LunaTaskAuthenticationError as error:
            message = f"Authentication failed: {error}"
            await ctx.error(message)
            logger.warning("Authentication error during journal entry creation: %s", error)
            return {
                "success": False,
                "error": "authentication_error",
                "message": message,
            }
        except LunaTaskRateLimitError as error:
            message = f"Rate limit exceeded: {error}"
            await ctx.error(message)
            logger.warning("Rate limit exceeded during journal entry creation: %s", error)
            return {
                "success": False,
                "error": "rate_limit_error",
                "message": message,
            }
        except (LunaTaskServerError, LunaTaskServiceUnavailableError) as error:
            message = f"Server error: {error}"
            await ctx.error(message)
            logger.warning("Server error during journal entry creation: %s", error)
            return {
                "success": False,
                "error": "server_error",
                "message": message,
            }
        except LunaTaskTimeoutError as error:
            message = f"Request timeout: {error}"
            await ctx.error(message)
            logger.warning("Timeout during journal entry creation: %s", error)
            return {
                "success": False,
                "error": "timeout_error",
                "message": message,
            }
        except LunaTaskNetworkError as error:
            message = f"Network error: {error}"
            await ctx.error(message)
            logger.warning("Network error during journal entry creation: %s", error)
            return {
                "success": False,
                "error": "network_error",
                "message": message,
            }
        except LunaTaskAPIError as error:
            message = f"API error: {error}"
            await ctx.error(message)
            logger.warning("API error during journal entry creation: %s", error)
            return {
                "success": False,
                "error": "api_error",
                "message": message,
            }
        except Exception as error:
            message = f"Unexpected error creating journal entry: {error}"
            await ctx.error(message)
            logger.exception("Unexpected error during journal entry creation")
            return {
                "success": False,
                "error": "unexpected_error",
                "message": message,
            }

        await ctx.info(f"Successfully created journal entry {journal_entry.id}")
        logger.info("Successfully created journal entry %s", journal_entry.id)
        return {
            "success": True,
            "journal_entry_id": journal_entry.id,
            "message": "Journal entry created successfully",
        }

    def _register_tools(self) -> None:
        """Register journal MCP tools with the FastMCP instance.

        Returns:
            None: This method registers callbacks on the MCP instance in-place.
        """

        async def _create_journal_entry(
            ctx: ServerContext,
            *,
            date_on: str,
            name: str | None = None,
            content: str | None = None,
        ) -> dict[str, Any]:
            return await self.create_journal_entry_tool(
                ctx,
                date_on=date_on,
                name=name,
                content=content,
            )

        self.mcp.tool(
            name="create_journal_entry",
            description=(
                "Create a journal entry for a specific date. Provide the date in YYYY-MM-DD format"
                " along with optional name and content fields."
            ),
        )(_create_journal_entry)
