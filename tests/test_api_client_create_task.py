"""Tests for LunaTaskClient.create_task()."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import TaskCreate, TaskResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import (
    DEFAULT_API_URL,
    INVALID_TOKEN,
    TEST_PRIORITY_HIGH,
    VALID_TOKEN,
)


class TestLunaTaskClientCreateTask:
    """Test suite for LunaTaskClient.create_task() method."""

    @pytest.mark.asyncio
    async def test_create_task_success_minimal_data(self, mocker: MockerFixture) -> None:
        """Test successful task creation with minimal required data."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-123",
                "status": "open",
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T10:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert result.id == "task-123"
        assert result.status == "open"
        mock_request.assert_called_once_with(
            "POST",
            "tasks",
            data={"name": "Test Task", "status": "later", "priority": 0, "motivation": "unknown"},
        )

    @pytest.mark.asyncio
    async def test_create_task_success_full_data(self, mocker: MockerFixture) -> None:
        """Test successful task creation with all optional fields."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(
            name="Full Test Task",
            note="These are test note",
            area_id="area-456",
            status="later",
            priority=1,
        )

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-456",
                "area_id": "area-456",
                "status": "open",
                "priority": 1,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T10:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert result.id == "task-456"
        assert result.area_id == "area-456"
        assert result.status == "open"
        assert result.priority == 1
        mock_request.assert_called_once_with(
            "POST",
            "tasks",
            data={
                "name": "Full Test Task",
                "note": "These are test note",
                "area_id": "area-456",
                "status": "later",
                "priority": 1,
                "motivation": "unknown",
            },
        )

    @pytest.mark.asyncio
    async def test_create_task_validation_error_422(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskValidationError on 422 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Invalid Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskValidationError("Validation failed"),
        )

        with pytest.raises(LunaTaskValidationError, match="Validation failed"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_subscription_required_error_402(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskSubscriptionRequiredError on 402 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskSubscriptionRequiredError("Subscription required"),
        )

        with pytest.raises(LunaTaskSubscriptionRequiredError, match="Subscription required"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_auth_error_401(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_server_error_500(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_response_parsing_success(self, mocker: MockerFixture) -> None:
        """Test create_task correctly parses task response with assigned ID."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Parse Test Task")

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "newly-assigned-id-123",
                "area_id": "test-area",
                "status": "open",
                "priority": TEST_PRIORITY_HIGH,
                "created_at": "2025-08-21T11:30:00Z",
                "updated_at": "2025-08-21T11:30:00Z",
                "source": {"type": "api", "value": "mcp-client"},
            }
        }

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert isinstance(result, TaskResponse)
        assert result.id == "newly-assigned-id-123"
        assert result.area_id == "test-area"
        assert result.status == "open"
        assert result.priority == TEST_PRIORITY_HIGH
        assert result.source is not None
        assert result.source.type == "api"
        assert result.source.value == "mcp-client"

    @pytest.mark.asyncio
    async def test_create_task_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test create_task applies rate limiting before request."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Rate Limited Task")

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "rate-limited-task",
                "status": "open",
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T10:00:00Z",
            }
        }

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with(
            "POST",
            "tasks",
            data={
                "name": "Rate Limited Task",
                "status": "later",
                "priority": 0,
                "motivation": "unknown",
            },
        )
        assert result.id == "rate-limited-task"

    @pytest.mark.asyncio
    async def test_create_task_missing_task_key_raises_parse_error(
        self, mocker: MockerFixture
    ) -> None:
        """No 'task' key -> parse error (KeyError branch)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Sample")

        mocker.patch.object(client, "make_request", return_value={"message": "ok"})

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.create_task(task_data)

        assert "endpoint=tasks" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_task_invalid_task_payload_raises_parse_error(
        self, mocker: MockerFixture
    ) -> None:
        """Invalid 'task' content -> validation failure -> general Exception branch."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Another")

        mock_response_data: dict[str, Any] = {"task": {"id": "x", "status": "open"}}
        mocker.patch.object(client, "make_request", return_value=mock_response_data)

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.create_task(task_data)

        assert "endpoint=tasks" in str(exc_info.value)
