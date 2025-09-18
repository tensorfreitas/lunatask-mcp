"""Tests for LunaTaskClient.create_task() aligned with refactored models."""
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
from lunatask_mcp.api.models import TaskCreate, TaskMotivation, TaskResponse, TaskStatus
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

        # Minimal TaskCreate now requires area_id and name
        task_data = TaskCreate(
            name="Test Task",
            area_id="area-001",
        )

        # Response must conform to TaskResponse
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-min-123",
                "area_id": "area-001",
                "status": "later",
                "motivation": "unknown",
                "priority": 0,
                "eisenhower": 0,
                "created_at": "2023-01-01T10:00:00Z",
                "updated_at": "2023-01-01T10:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert result.area_id == "area-001"
        assert result.status == TaskStatus.LATER
        assert result.motivation == TaskMotivation.UNKNOWN
        assert result.priority == 0
        mock_request.assert_called_once_with(
            "POST",
            "tasks",
            data={
                "name": "Test Task",
                "area_id": "area-001",
            },
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
            goal_id="goal-789",
            status="later",
            priority=1,
            motivation="must",
        )

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-456",
                "area_id": "area-456",
                "goal_id": "goal-789",
                "status": "started",
                "motivation": "must",
                "priority": 1,
                "eisenhower": 0,
                "created_at": "2023-01-01T10:00:00Z",
                "updated_at": "2023-01-01T10:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert result.area_id == "area-456"
        assert result.goal_id == "goal-789"
        assert result.status == TaskStatus.STARTED
        assert result.motivation == TaskMotivation.MUST
        assert result.priority == 1
        mock_request.assert_called_once_with(
            "POST",
            "tasks",
            data={
                "name": "Full Test Task",
                "note": "These are test note",
                "area_id": "area-456",
                "goal_id": "goal-789",
                "status": "later",
                "priority": 1,
                "motivation": "must",
            },
        )

    @pytest.mark.asyncio
    async def test_create_task_validation_error_422(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskValidationError on 422 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(
            name="Invalid Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

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

        task_data = TaskCreate(
            name="Test Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

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

        task_data = TaskCreate(
            name="Test Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

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

        task_data = TaskCreate(
            name="Test Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

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

        task_data = TaskCreate(
            name="Test Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

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

        task_data = TaskCreate(
            name="Test Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

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
        """Test create_task correctly parses task response with valid fields."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(
            name="Parse Test Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "newly-assigned-id-123",
                "area_id": "test-area",
                "goal_id": "goal-001",
                "status": "started",
                "motivation": "unknown",
                "priority": TEST_PRIORITY_HIGH,
                "eisenhower": 0,
                "created_at": "2023-01-01T10:00:00Z",
                "updated_at": "2023-01-01T10:00:00Z",
                "sources": [
                    {
                        "source": "api",
                        "source_id": "mcp-client",
                    }
                ],
            }
        }

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert isinstance(result, TaskResponse)
        assert result.area_id == "test-area"
        assert result.goal_id == "goal-001"
        assert result.status == TaskStatus.STARTED
        assert result.priority == TEST_PRIORITY_HIGH
        assert result.source == "api"
        assert result.source_id == "mcp-client"

    @pytest.mark.asyncio
    async def test_create_task_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test create_task applies rate limiting before request."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(
            name="Rate Limited Task",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "rate-limited-task",
                "area_id": "area-001",
                "goal_id": "goal-001",
                "status": "later",
                "motivation": "unknown",
                "priority": 0,
                "eisenhower": 0,
                "created_at": "2023-01-01T10:00:00Z",
                "updated_at": "2023-01-01T10:00:00Z",
                "sources": [],
            }
        }

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        _ = await client.create_task(task_data)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with(
            "POST",
            "tasks",
            data={
                "name": "Rate Limited Task",
                "area_id": "area-001",
                "goal_id": "goal-001",
                "motivation": "unknown",
            },
        )

    @pytest.mark.asyncio
    async def test_create_task_missing_task_key_raises_parse_error(
        self, mocker: MockerFixture
    ) -> None:
        """No 'task' key -> parse error (KeyError branch)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(
            name="Sample",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

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

        task_data = TaskCreate(
            name="Another",
            area_id="area-001",
            goal_id="goal-001",
            motivation="unknown",
        )

        # Invalid status 'open' should cause parse error in TaskResponse
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "invalid-task",
                "status": "open",
                "area_id": "area-001",
                "goal_id": "goal-001",
                "motivation": "unknown",
                "priority": 0,
                "eisenhower": 0,
                "created_at": "2023-01-01T10:00:00Z",
                "updated_at": "2023-01-01T10:00:00Z",
            }
        }
        mocker.patch.object(client, "make_request", return_value=mock_response_data)

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.create_task(task_data)

        assert "endpoint=tasks" in str(exc_info.value)
