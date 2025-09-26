"""Tests for LunaTaskClient.delete_person()."""

from __future__ import annotations

import urllib.parse
from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models_people import PersonRelationshipStrength, PersonResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, INVALID_TOKEN, VALID_TOKEN


class TestLunaTaskClientDeletePerson:
    """Test suite for LunaTaskClient.delete_person() method."""

    @pytest.mark.asyncio
    async def test_delete_person_success_200_with_wrapped_response(
        self, mocker: MockerFixture
    ) -> None:
        """Test successful person deletion with 200 response and wrapped person data."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "92a960ba-54f5-42db-bd0c-596dced80644"

        # Mock 200 response with wrapped person data including deleted_at
        mock_response: dict[str, Any] = {
            "person": {
                "id": "92a960ba-54f5-42db-bd0c-596dced80644",
                "agreed_reconnect_on": None,
                "created_at": "2025-09-25T17:15:12.941Z",
                "deleted_at": "2025-09-25T17:15:47.398Z",
                "last_reconnect_on": None,
                "next_reconnect_on": None,
                "relationship_direction": None,
                "relationship_strength": "acquaintances",
                "sources": [],
                "updated_at": "2025-09-25T17:15:47.398Z",
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_person(person_id)

        assert isinstance(result, PersonResponse)
        assert result.id == "92a960ba-54f5-42db-bd0c-596dced80644"
        assert result.relationship_strength == PersonRelationshipStrength.ACQUAINTANCES
        assert result.deleted_at == datetime(2025, 9, 25, 17, 15, 47, 398000, tzinfo=UTC)
        assert result.created_at == datetime(2025, 9, 25, 17, 15, 12, 941000, tzinfo=UTC)
        assert result.updated_at == datetime(2025, 9, 25, 17, 15, 47, 398000, tzinfo=UTC)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test delete_person raises LunaTaskNotFoundError on 404 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "nonexistent-person"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError("Person not found"),
        )

        with pytest.raises(LunaTaskNotFoundError, match="Person not found"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test delete_person raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        person_id = "person-123"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test delete_person raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "person-rate-limited"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_server_error_500(self, mocker: MockerFixture) -> None:
        """Test delete_person raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "person-server-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_timeout_error(self, mocker: MockerFixture) -> None:
        """Test delete_person raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "person-timeout"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_network_error(self, mocker: MockerFixture) -> None:
        """Test delete_person raises LunaTaskNetworkError on network error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "person-network-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network error"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network error"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_empty_string_id_validation(self, mocker: MockerFixture) -> None:
        """Test delete_person with empty person_id raises validation error before API call."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = ""

        # Mock should NOT be called due to early validation
        mock_request = mocker.patch.object(client, "make_request")

        with pytest.raises(LunaTaskValidationError, match="Person ID cannot be empty"):
            await client.delete_person(person_id)

        # Ensure API was NOT called due to validation failure
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_person_whitespace_id_validation(self, mocker: MockerFixture) -> None:
        """Test delete_person with whitespace person_id raises validation error before API call."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "   \t\n  "

        # Mock should NOT be called due to early validation
        mock_request = mocker.patch.object(client, "make_request")

        with pytest.raises(LunaTaskValidationError, match="Person ID cannot be empty"):
            await client.delete_person(person_id)

        # Ensure API was NOT called due to validation failure
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_person_url_encoding_special_characters(
        self, mocker: MockerFixture
    ) -> None:
        """Test delete_person properly URL-encodes special characters in person_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        # Person ID with special characters that need URL encoding
        person_id = "person-with/special@chars&params=value"
        expected_encoded = urllib.parse.quote(person_id, safe="")

        mock_response: dict[str, Any] = {
            "person": {
                "id": person_id,
                "relationship_strength": "casual-friends",
                "sources": [],
                "created_at": "2025-09-25T17:15:12.941Z",
                "deleted_at": "2025-09-25T17:15:47.398Z",
                "updated_at": "2025-09-25T17:15:47.398Z",
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_person(person_id)

        assert isinstance(result, PersonResponse)
        assert result.id == person_id

        # Verify the URL was properly encoded
        mock_request.assert_called_once_with("DELETE", f"people/{expected_encoded}")

    @pytest.mark.asyncio
    async def test_delete_person_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test delete_person applies rate limiting through make_request delegation."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "rate-limited-delete-person"

        mock_response: dict[str, Any] = {
            "person": {
                "id": person_id,
                "relationship_strength": "casual-friends",
                "sources": [],
                "created_at": "2025-09-25T17:15:12.941Z",
                "deleted_at": "2025-09-25T17:15:47.398Z",
                "updated_at": "2025-09-25T17:15:47.398Z",
            }
        }

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_person(person_id)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")
        assert isinstance(result, PersonResponse)

    @pytest.mark.asyncio
    async def test_delete_person_non_idempotent_behavior(self, mocker: MockerFixture) -> None:
        """Test delete_person non-idempotent behavior - second delete returns 404."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "person-already-deleted"

        # First call succeeds (person exists and gets deleted)
        mock_response: dict[str, Any] = {
            "person": {
                "id": person_id,
                "relationship_strength": "casual-friends",
                "sources": [],
                "created_at": "2025-09-25T17:15:12.941Z",
                "deleted_at": "2025-09-25T17:15:47.398Z",
                "updated_at": "2025-09-25T17:15:47.398Z",
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.delete_person(person_id)
        assert isinstance(result, PersonResponse)
        assert result.deleted_at is not None

        # Second call fails (person no longer exists)
        mock_request.side_effect = LunaTaskNotFoundError("Person not found")

        with pytest.raises(LunaTaskNotFoundError):
            await client.delete_person(person_id)

    @pytest.mark.asyncio
    async def test_delete_person_parse_error_missing_person_key(
        self, mocker: MockerFixture
    ) -> None:
        """Test delete_person raises LunaTaskAPIError when response is missing 'person' key."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "person-parse-error"

        # Mock response without the expected 'person' wrapper
        mock_response = {"unexpected": {"id": person_id}}

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")

    @pytest.mark.asyncio
    async def test_delete_person_parse_error_malformed_person_data(
        self, mocker: MockerFixture
    ) -> None:
        """Test delete_person raises LunaTaskAPIError when person data is malformed."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        person_id = "person-malformed-data"

        # Mock response with invalid person data (missing required fields)
        mock_response: dict[str, Any] = {
            "person": {
                "id": person_id,
                # Missing required fields like relationship_strength, created_at, etc.
            }
        }

        mock_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.delete_person(person_id)

        mock_request.assert_called_once_with("DELETE", f"people/{person_id}")
