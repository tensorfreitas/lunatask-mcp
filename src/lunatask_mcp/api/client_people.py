"""People functionality mixin for LunaTask API client.

This module provides the PeopleClientMixin class that handles person creation
operations, designed to be composed with the base client.
"""

import json
import logging
from typing import TYPE_CHECKING

from lunatask_mcp.api.exceptions import LunaTaskAPIError
from lunatask_mcp.api.models_people import PersonCreate, PersonResponse

if TYPE_CHECKING:
    from lunatask_mcp.api.protocols import BaseClientProtocol

logger = logging.getLogger(__name__)


class PeopleClientMixin:
    """Mixin providing person creation functionality for the LunaTask API client."""

    async def create_person(
        self: "BaseClientProtocol", person_data: PersonCreate
    ) -> PersonResponse | None:
        """Create a new person in the LunaTask API.

        Args:
            person_data: PersonCreate object containing person data to create.

        Returns:
            PersonResponse | None: Created person object from the API, or None when
            the API returns 204 No Content due to duplicate source/source_id.

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
        json_data = json.loads(person_data.model_dump_json(exclude_none=True))

        response_data = await self.make_request("POST", "people", data=json_data)

        if not response_data:
            logger.debug(
                "Person creation returned no content; assuming duplicate for source/source_id"
            )
            return None

        try:
            person_payload = response_data["person"]
            person = PersonResponse(**person_payload)
        except KeyError as error:
            logger.exception("Failed to extract person from wrapped response format")
            person_name = f"{json_data.get('first_name', '')} {json_data.get('last_name', '')}"
            raise LunaTaskAPIError.create_parse_error(
                "people", person_name=f"{person_name.strip()} - missing 'person' key"
            ) from error
        except Exception as error:
            logger.exception("Failed to parse created person response data")
            person_name = f"{json_data.get('first_name', '')} {json_data.get('last_name', '')}"
            raise LunaTaskAPIError.create_parse_error(
                "people", person_name=person_name.strip()
            ) from error
        else:
            logger.debug("Successfully created person: %s", person.id)
            return person
