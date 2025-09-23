"""Tests for LunaTaskClient.create_person()."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture

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
from lunatask_mcp.api.models_people import PersonCreate, PersonRelationshipStrength, PersonResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, VALID_TOKEN


class TestLunaTaskClientCreatePerson:
    """Test suite for LunaTaskClient.create_person()."""

    @pytest.mark.asyncio
    async def test_create_person_success_all_fields(self, mocker: MockerFixture) -> None:
        """Client should deserialize wrapped person response on success."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_payload = PersonCreate(
            first_name="John",
            last_name="Doe",
            relationship_strength=PersonRelationshipStrength.BUSINESS_CONTACTS,
            source="salesforce",
            source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
            email="john.doe@example.com",
            birthday=date(1985, 3, 20),
            phone="+1-555-123-4567",
        )

        mock_response: dict[str, Any] = {
            "person": {
                "id": "5999b945-b2b1-48c6-aa72-b251b75b3c2e",
                "relationship_strength": "business-contacts",
                "sources": [
                    {"source": "salesforce", "source_id": "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"},
                ],
                "created_at": "2021-01-10T10:39:25Z",
                "updated_at": "2021-01-10T10:39:25Z",
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.create_person(person_payload)

        assert isinstance(result, PersonResponse)
        assert result.id == "5999b945-b2b1-48c6-aa72-b251b75b3c2e"
        assert result.relationship_strength == PersonRelationshipStrength.BUSINESS_CONTACTS
        assert result.source == "salesforce"
        assert result.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"
        assert result.created_at == datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC)
        assert result.updated_at == datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC)

        mock_make_request.assert_called_once_with(
            "POST",
            "people",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "relationship_strength": "business-contacts",
                "source": "salesforce",
                "source_id": "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
                "email": "john.doe@example.com",
                "birthday": "1985-03-20",
                "phone": "+1-555-123-4567",
            },
        )

    @pytest.mark.asyncio
    async def test_create_person_success_minimal_fields(self, mocker: MockerFixture) -> None:
        """Client should handle minimal person creation with only required fields."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_payload = PersonCreate(first_name="Jane", last_name="Smith")

        mock_response: dict[str, Any] = {
            "person": {
                "id": "8888c945-b2b1-48c6-aa72-b251b75b3c2e",
                "relationship_strength": "casual-friends",
                "sources": [],
                "created_at": "2021-01-10T10:39:25Z",
                "updated_at": "2021-01-10T10:39:25Z",
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.create_person(person_payload)

        assert isinstance(result, PersonResponse)
        assert result.id == "8888c945-b2b1-48c6-aa72-b251b75b3c2e"
        assert result.relationship_strength == PersonRelationshipStrength.CASUAL_FRIENDS

        mock_make_request.assert_called_once_with(
            "POST",
            "people",
            data={
                "first_name": "Jane",
                "last_name": "Smith",
                "relationship_strength": "casual-friends",
            },
        )

    @pytest.mark.asyncio
    async def test_create_person_duplicate_returns_none(self, mocker: MockerFixture) -> None:
        """204 No Content response should return None to signal duplicate detected."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mock_make_request = mocker.patch.object(client, "make_request", return_value={})

        result = await client.create_person(person_payload)

        assert result is None
        mock_make_request.assert_called_once_with(
            "POST",
            "people",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "relationship_strength": "casual-friends",
            },
        )

    @pytest.mark.asyncio
    async def test_create_person_authentication_error(self, mocker: MockerFixture) -> None:
        """Propagate authentication errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid bearer token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid bearer token"):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_subscription_required_error(self, mocker: MockerFixture) -> None:
        """Propagate subscription required errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskSubscriptionRequiredError("Subscription upgrade required"),
        )

        with pytest.raises(
            LunaTaskSubscriptionRequiredError, match="Subscription upgrade required"
        ):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_validation_error(self, mocker: MockerFixture) -> None:
        """Propagate validation errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskValidationError("Custom fields for email not defined in app"),
        )

        with pytest.raises(
            LunaTaskValidationError, match="Custom fields for email not defined in app"
        ):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Propagate rate limit errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_server_error(self, mocker: MockerFixture) -> None:
        """Propagate server errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error", status_code=500),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_service_unavailable_error(self, mocker: MockerFixture) -> None:
        """Propagate service unavailable errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServiceUnavailableError("Service temporarily unavailable"),
        )

        with pytest.raises(
            LunaTaskServiceUnavailableError, match="Service temporarily unavailable"
        ):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_timeout_error(self, mocker: MockerFixture) -> None:
        """Propagate timeout errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_network_error(self, mocker: MockerFixture) -> None:
        """Propagate network errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network connection failed"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network connection failed"):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_parse_error_missing_person_key(
        self, mocker: MockerFixture
    ) -> None:
        """Missing wrapped person should raise a LunaTaskAPIError parse error."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        mocker.patch.object(client, "make_request", return_value={"unexpected": {}})

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_parse_error_malformed_data(self, mocker: MockerFixture) -> None:
        """Malformed person data should raise a LunaTaskAPIError parse error."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        person_payload = PersonCreate(first_name="John", last_name="Doe")

        # Missing required fields in response
        mock_response: dict[str, Any] = {
            "person": {
                "id": "5999b945-b2b1-48c6-aa72-b251b75b3c2e",
                # Missing relationship_strength, created_at, updated_at
            }
        }

        mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.create_person(person_payload)

    @pytest.mark.asyncio
    async def test_create_person_serializes_with_exclude_none(self, mocker: MockerFixture) -> None:
        """PersonCreate should be serialized with exclude_none=True behavior."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_payload = PersonCreate(
            first_name="John",
            last_name="Doe",
            source="github",
            # source_id, email, birthday, phone are None and should be excluded
        )

        mock_response: dict[str, Any] = {
            "person": {
                "id": "5999b945-b2b1-48c6-aa72-b251b75b3c2e",
                "relationship_strength": "casual-friends",
                "sources": [{"source": "github", "source_id": None}],
                "created_at": "2021-01-10T10:39:25Z",
                "updated_at": "2021-01-10T10:39:25Z",
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        await client.create_person(person_payload)

        # Verify that None values were excluded from the serialized data
        call_args = mock_make_request.call_args
        sent_data = call_args[1]["data"]

        assert "first_name" in sent_data
        assert "last_name" in sent_data
        assert "relationship_strength" in sent_data
        assert "source" in sent_data
        # These None fields should not be present
        assert "source_id" not in sent_data
        assert "email" not in sent_data
        assert "birthday" not in sent_data
        assert "phone" not in sent_data
