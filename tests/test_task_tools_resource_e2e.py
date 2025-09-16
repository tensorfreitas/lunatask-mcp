"""Tests for TaskTools end-to-end resource validation.

This module contains end-to-end validation tests for the TaskTools class
that validate complete MCP resource functionality from client perspective.
"""

from datetime import UTC, date, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAuthenticationError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_source, create_task_response


class TestEndToEndResourceValidation:
    """End-to-End task tools resoursce e2e validation testing.

    These tests validate complete MCP resource functionality from client perspective:
    - Resource discoverability
    - Complete resource access flow
    - MCP error response validation
    - Resource registration and URI template matching
    """

    def test_resource_discoverability_via_mcp_introspection(self, mocker: MockerFixture) -> None:
        """Test that lunatask://tasks/{task_id} resource is discoverable by MCP clients.

        Verify resource is discoverable by MCP clients using resource listing
        """
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource registration to verify it was called correctly
        mock_resource = mocker.patch.object(mcp, "resource")

        # Initialize TaskTools to register resources
        TaskTools(mcp, client)

        # Verify resource templates are registered and discoverable (including discovery)
        mock_resource.assert_any_call("lunatask://tasks")
        mock_resource.assert_any_call("lunatask://tasks/{task_id}")
        mock_resource.assert_any_call("lunatask://tasks/discovery")

        # Verify we have all resources registered
        expected_resource_count = 3
        assert mock_resource.call_count >= expected_resource_count

        # Verify the resource functions were registered with correct signatures
        calls = mock_resource.call_args_list

        # Find the single task resource call
        single_task_call = None
        for call in calls:
            if call[0][0] == "lunatask://tasks/{task_id}":  # URI template
                single_task_call = call
                break

        assert single_task_call is not None, "Single task resource template not found"

        # Verify the decorator was called with correct URI template
        assert single_task_call[0][0] == "lunatask://tasks/{task_id}"

    @pytest.mark.asyncio
    async def test_complete_resource_access_flow_success(self, mocker: MockerFixture) -> None:
        """Test complete resource access flow from MCP client perspective with valid task_id.

        Test complete resource access flow from MCP client with valid task ID
        """
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context for the resource call
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "e2e-test-session"

        # Create realistic task data that would come from LunaTask API
        test_task = create_task_response(
            task_id="e2e-test-task-456",
            status="started",
            created_at=datetime(2025, 8, 21, 9, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 11, 30, 0, tzinfo=UTC),
            priority=2,
            scheduled_on=date(2025, 8, 28),
            area_id="work-area-789",
            source=create_source("integration", "github_issue"),
        )

        # Mock the complete client flow
        mock_get_task = mocker.patch.object(client, "get_task", return_value=test_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the complete resource access flow
        result = await task_tools.get_task_resource(mock_ctx, task_id="e2e-test-task-456")

        # Validate complete MCP resource response structure
        assert isinstance(result, dict)
        assert result["resource_type"] == "lunatask_task"
        assert result["task_id"] == "e2e-test-task-456"

        # Validate task data structure and content
        task_data = result["task"]
        assert task_data["id"] == "e2e-test-task-456"
        assert task_data["status"] == "started"
        expected_priority = 2
        assert task_data["priority"] == expected_priority
        assert task_data["scheduled_on"] == "2025-08-28"
        assert task_data["area_id"] == "work-area-789"
        assert task_data["source"]["type"] == "integration"
        assert task_data["source"]["value"] == "github_issue"

        # Validate metadata structure
        metadata = result["metadata"]
        assert metadata["retrieved_at"] == "e2e-test-session"
        assert "E2E encryption" in metadata["encrypted_fields_note"]

        # Validate the complete call chain worked correctly
        mock_get_task.assert_called_once_with("e2e-test-task-456")
        mock_ctx.info.assert_any_call("Retrieving task e2e-test-task-456 from LunaTask API")
        mock_ctx.info.assert_any_call("Successfully retrieved task e2e-test-task-456 from LunaTask")

    @pytest.mark.asyncio
    async def test_mcp_error_response_validation_task_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """Test MCP error responses for TaskNotFoundError and other error scenarios.

        Validate MCP error responses for TaskNotFoundError and other error scenarios
        """
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock TaskNotFoundError from client
        not_found_error = LunaTaskNotFoundError("Task not found")
        mocker.patch.object(client, "get_task", side_effect=not_found_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Verify that the error is properly propagated for MCP error handling
        with pytest.raises(LunaTaskNotFoundError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="nonexistent-task-123")

        # Validate the error is the exact same instance
        assert exc_info.value is not_found_error

        # Validate proper error logging occurred
        mock_ctx.error.assert_called_once()
        error_msg = mock_ctx.error.call_args[0][0]
        assert "Task nonexistent-task-123 not found" in error_msg

    @pytest.mark.asyncio
    async def test_mcp_error_response_validation_authentication_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test MCP error response validation for authentication errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="invalid_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock authentication error
        auth_error = LunaTaskAuthenticationError("Authentication failed")
        mocker.patch.object(client, "get_task", side_effect=auth_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Verify proper error propagation
        with pytest.raises(LunaTaskAuthenticationError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="test-task-999")

        assert exc_info.value is auth_error
        mock_ctx.error.assert_called_once()
        error_msg = mock_ctx.error.call_args[0][0]
        assert "Invalid or expired LunaTask API credentials" in error_msg

    @pytest.mark.asyncio
    async def test_mcp_error_response_validation_rate_limit_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test MCP error response validation for rate limit errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock rate limit error
        rate_limit_error = LunaTaskRateLimitError("Rate limit exceeded")
        mocker.patch.object(client, "get_task", side_effect=rate_limit_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Verify proper error propagation
        with pytest.raises(LunaTaskRateLimitError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="test-task-888")

        assert exc_info.value is rate_limit_error
        mock_ctx.error.assert_called_once()
        error_msg = mock_ctx.error.call_args[0][0]
        assert "LunaTask API rate limit exceeded" in error_msg

    def test_resource_registration_and_uri_template_matching(self, mocker: MockerFixture) -> None:
        """Test resource registration and proper URI template matching in running server.

        Confirm resource registration and proper URI template matching in server
        """
        # Create the FastMCP instance and configuration as would happen in real server
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="production_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource decorator to capture registration details
        mock_resource_decorator = mocker.patch.object(mcp, "resource")

        # Initialize TaskTools as would happen in the actual server
        task_tools = TaskTools(mcp, client)

        # Verify that resource templates were registered with correct URI patterns
        mock_resource_decorator.assert_any_call("lunatask://tasks")
        mock_resource_decorator.assert_any_call("lunatask://tasks/{task_id}")
        mock_resource_decorator.assert_any_call("lunatask://tasks/discovery")

        # Verify the correct number of resource registrations
        expected_resource_count = 3
        assert mock_resource_decorator.call_count >= expected_resource_count

        # Verify that TaskTools instance maintains references correctly
        assert task_tools.mcp is mcp
        assert task_tools.lunatask_client is client

        # Verify the URI template pattern for single task resource
        single_task_calls = [
            call
            for call in mock_resource_decorator.call_args_list
            if call[0][0] == "lunatask://tasks/{task_id}"
        ]
        assert len(single_task_calls) == 1, (
            "Single task resource template should be registered exactly once"
        )

        # Validate URI template format matches MCP specification
        uri_template = single_task_calls[0][0][0]
        assert uri_template == "lunatask://tasks/{task_id}"
        assert "{task_id}" in uri_template
        assert uri_template.startswith("lunatask://")

    @pytest.mark.asyncio
    async def test_end_to_end_parameter_extraction_validation(self, mocker: MockerFixture) -> None:
        """Test that URI template parameter extraction works correctly end-to-end."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Create test task with a complex ID that tests parameter extraction
        test_task_id = "complex-task-id-with-dashes-123"
        test_task = create_task_response(
            task_id=test_task_id,
            status="later",
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
        )

        mock_get_task = mocker.patch.object(client, "get_task", return_value=test_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource with the complex task ID
        result = await task_tools.get_task_resource(mock_ctx, task_id=test_task_id)

        # Verify parameter was extracted and passed correctly
        mock_get_task.assert_called_once_with(test_task_id)

        # Verify the response contains the correct task ID
        assert result["task_id"] == test_task_id
        assert result["task"]["id"] == test_task_id

    @pytest.mark.asyncio
    async def test_end_to_end_encrypted_fields_handling_validation(
        self, mocker: MockerFixture
    ) -> None:
        """Test end-to-end validation that encrypted fields are handled correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Create task that simulates E2E encryption (missing name/note fields)
        encrypted_task = create_task_response(
            task_id="encrypted-task-e2e",
            status="waiting",
            created_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 21, 10, 0, 0, tzinfo=UTC),
            priority=1,
            scheduled_on=date(2025, 8, 30),
            area_id="secure-area",
            source=create_source("secure", "encrypted_source"),
        )

        mocker.patch.object(client, "get_task", return_value=encrypted_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Execute the complete flow
        result = await task_tools.get_task_resource(mock_ctx, task_id="encrypted-task-e2e")

        # Validate that encrypted fields are properly absent
        task_data = result["task"]
        assert "name" not in task_data
        assert "note" not in task_data

        # Validate that other fields are present
        assert task_data["id"] == "encrypted-task-e2e"
        assert task_data["status"] == "waiting"
        assert task_data["priority"] == 1
        assert task_data["area_id"] == "secure-area"

        # Validate metadata indicates encryption
        assert "E2E encryption" in result["metadata"]["encrypted_fields_note"]
