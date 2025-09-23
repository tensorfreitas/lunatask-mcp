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
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models_people import PersonCreate, PersonRelationshipStrength

logger = logging.getLogger(__name__)


class PeopleTools:
    """People/contact management tools providing MCP integrations for LunaTask people."""

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize PeopleTools with FastMCP instance and LunaTask client."""

        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_tools()

    async def create_person_tool(  # noqa: PLR0913, PLR0911, PLR0912, PLR0915, C901
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
        """Create a person in LunaTask with optional duplicate detection."""

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

        except LunaTaskValidationError as error:
            message = f"Person validation failed: {error}"
            await ctx.error(message)
            logger.warning("Person validation error: %s", error)
            return {
                "success": False,
                "error": "validation_error",
                "message": message,
            }

        except LunaTaskSubscriptionRequiredError as error:
            message = f"Subscription required: {error}"
            await ctx.error(message)
            logger.warning("Subscription required during person creation: %s", error)
            return {
                "success": False,
                "error": "subscription_required",
                "message": message,
            }

        except LunaTaskAuthenticationError as error:
            message = f"Authentication failed: {error}"
            await ctx.error(message)
            logger.warning("Authentication error during person creation: %s", error)
            return {
                "success": False,
                "error": "authentication_error",
                "message": message,
            }

        except LunaTaskRateLimitError as error:
            message = f"Rate limit exceeded: {error}"
            await ctx.error(message)
            logger.warning("Rate limit exceeded during person creation: %s", error)
            return {
                "success": False,
                "error": "rate_limit_error",
                "message": message,
            }

        except (LunaTaskServerError, LunaTaskServiceUnavailableError) as error:
            message = f"Server error: {error}"
            await ctx.error(message)
            logger.warning("Server error during person creation: %s", error)
            return {
                "success": False,
                "error": "server_error",
                "message": message,
            }

        except LunaTaskTimeoutError as error:
            message = f"Request timeout: {error}"
            await ctx.error(message)
            logger.warning("Timeout during person creation: %s", error)
            return {
                "success": False,
                "error": "timeout_error",
                "message": message,
            }

        except LunaTaskNetworkError as error:
            message = f"Network error: {error}"
            await ctx.error(message)
            logger.warning("Network error during person creation: %s", error)
            return {
                "success": False,
                "error": "network_error",
                "message": message,
            }

        except LunaTaskAPIError as error:
            message = f"API error: {error}"
            await ctx.error(message)
            logger.warning("API error during person creation: %s", error)
            return {
                "success": False,
                "error": "api_error",
                "message": message,
            }

        except Exception as error:
            message = f"Unexpected error creating person: {error}"
            await ctx.error(message)
            logger.exception("Unexpected error during person creation")
            return {
                "success": False,
                "error": "unexpected_error",
                "message": message,
            }

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

    def _register_tools(self) -> None:
        """Register people-related MCP tools with the FastMCP instance."""

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
