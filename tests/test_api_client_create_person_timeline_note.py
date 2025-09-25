"""Tests for LunaTaskClient.create_person_timeline_note()."""

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
from lunatask_mcp.api.models_people import (
    PersonTimelineNoteCreate,
    PersonTimelineNoteResponse,
)
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, VALID_TOKEN


class TestLunaTaskClientCreatePersonTimelineNote:
    """Test suite for LunaTaskClient.create_person_timeline_note()."""

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_success(self, mocker: MockerFixture) -> None:
        """Client should unwrap and parse the person timeline note response."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        payload = PersonTimelineNoteCreate(
            person_id="person-123",
            content="Called mom to check in",
            date_on=date(2025, 9, 20),
        )

        mock_response: dict[str, Any] = {
            "person_timeline_note": {
                "id": "timeline-note-123",
                "date_on": "2025-09-20",
                "created_at": "2025-09-20T12:15:00Z",
                "updated_at": "2025-09-20T12:15:00Z",
            }
        }

        mock_make_request = mocker.patch.object(client, "make_request", return_value=mock_response)

        result = await client.create_person_timeline_note(payload)

        assert isinstance(result, PersonTimelineNoteResponse)
        assert result.id == "timeline-note-123"
        assert result.date_on == date(2025, 9, 20)
        assert result.created_at == datetime(2025, 9, 20, 12, 15, tzinfo=UTC)
        assert result.updated_at == datetime(2025, 9, 20, 12, 15, tzinfo=UTC)

        mock_make_request.assert_called_once_with(
            "POST",
            "person_timeline_notes",
            data={
                "person_id": "person-123",
                "content": "Called mom to check in",
                "date_on": "2025-09-20",
            },
        )

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_parse_error_missing_wrapper(
        self, mocker: MockerFixture
    ) -> None:
        """Missing wrapper key should raise a LunaTaskAPIError parse error."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(client, "make_request", return_value={"unexpected": {}})

        with pytest.raises(LunaTaskAPIError, match="Failed to parse response"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_validation_error(
        self, mocker: MockerFixture
    ) -> None:
        """Propagate validation errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskValidationError("Invalid payload"),
        )

        with pytest.raises(LunaTaskValidationError, match="Invalid payload"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_subscription_required_error(
        self, mocker: MockerFixture
    ) -> None:
        """Propagate subscription required errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskSubscriptionRequiredError("Upgrade required"),
        )

        with pytest.raises(LunaTaskSubscriptionRequiredError, match="Upgrade required"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_authentication_error(
        self, mocker: MockerFixture
    ) -> None:
        """Propagate authentication errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_rate_limit_error(
        self, mocker: MockerFixture
    ) -> None:
        """Propagate rate limit errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_timeout_error(self, mocker: MockerFixture) -> None:
        """Propagate timeout errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timed out"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timed out"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_network_error(self, mocker: MockerFixture) -> None:
        """Propagate network errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network issue"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network issue"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_server_error(self, mocker: MockerFixture) -> None:
        """Propagate server errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal error", status_code=500),
        )

        with pytest.raises(LunaTaskServerError, match="Internal error"):
            await client.create_person_timeline_note(payload)

    @pytest.mark.asyncio
    async def test_create_person_timeline_note_service_unavailable_error(
        self, mocker: MockerFixture
    ) -> None:
        """Propagate service unavailable errors from make_request."""

        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        payload = PersonTimelineNoteCreate(person_id="person-123", content="Note")

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServiceUnavailableError("Service unavailable"),
        )

        with pytest.raises(LunaTaskServiceUnavailableError, match="Service unavailable"):
            await client.create_person_timeline_note(payload)
