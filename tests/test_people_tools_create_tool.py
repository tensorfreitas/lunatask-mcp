"""Tests for PeopleTools.create_person_tool()."""

from datetime import date
from unittest import mock

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
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
from lunatask_mcp.api.models_people import PersonCreate, PersonRelationshipStrength
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.people import PeopleTools
from tests.factories import create_person_response


class TestCreatePersonTool:
    """Test suite for the create_person MCP tool."""

    @pytest.mark.asyncio
    async def test_create_person_tool_success_all_parameters(self, mocker: MockerFixture) -> None:
        """Tool should return success payload and person_id on creation with all parameters."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        created_person = create_person_response(
            person_id="person-123",
            relationship_strength="business-contacts",
            source="salesforce",
            source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
            email="john.doe@example.com",
            birthday=date(1985, 3, 20),
            phone="+1-555-123-4567",
        )

        mocker.patch.object(client, "create_person", return_value=created_person)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
            relationship_strength="business-contacts",
            source="salesforce",
            source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
            email="john.doe@example.com",
            birthday="1985-03-20",
            phone="+1-555-123-4567",
        )

        assert result == {
            "success": True,
            "person_id": "person-123",
            "message": "Person created successfully",
        }

        client.create_person.assert_called_once()  # type: ignore[attr-defined]
        call_arg = client.create_person.call_args[0][0]  # type: ignore[attr-defined]
        assert isinstance(call_arg, PersonCreate)
        assert call_arg.first_name == "John"
        assert call_arg.last_name == "Doe"
        assert call_arg.relationship_strength == PersonRelationshipStrength.BUSINESS_CONTACTS
        assert call_arg.source == "salesforce"
        assert call_arg.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"
        assert call_arg.email == "john.doe@example.com"
        assert call_arg.birthday == date(1985, 3, 20)
        assert call_arg.phone == "+1-555-123-4567"

    @pytest.mark.asyncio
    async def test_create_person_tool_success_minimal_parameters(
        self, mocker: MockerFixture
    ) -> None:
        """Tool should work with only first_name and last_name parameters."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        created_person = create_person_response(
            person_id="person-minimal-456",
            relationship_strength="casual-friends",
        )

        mocker.patch.object(client, "create_person", return_value=created_person)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="Jane",
            last_name="Smith",
        )

        assert result == {
            "success": True,
            "person_id": "person-minimal-456",
            "message": "Person created successfully",
        }

        client.create_person.assert_called_once()  # type: ignore[attr-defined]
        call_arg = client.create_person.call_args[0][0]  # type: ignore[attr-defined]
        assert isinstance(call_arg, PersonCreate)
        assert call_arg.first_name == "Jane"
        assert call_arg.last_name == "Smith"
        assert call_arg.relationship_strength == PersonRelationshipStrength.CASUAL_FRIENDS

    @pytest.mark.asyncio
    async def test_create_person_tool_duplicate_detection(self, mocker: MockerFixture) -> None:
        """Duplicate detection should return success with duplicate flag."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(client, "create_person", return_value=None)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
            source="salesforce",
            source_id="existing-id-123",
        )

        assert result == {
            "success": True,
            "duplicate": True,
            "message": "Person already exists for this source/source_id",
        }

    @pytest.mark.asyncio
    async def test_create_person_tool_relationship_strength_validation(
        self, mocker: MockerFixture
    ) -> None:
        """Tool should validate relationship_strength parameter values."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Test valid relationship strength values
        for valid_strength in [
            "family",
            "intimate-friends",
            "close-friends",
            "casual-friends",
            "acquaintances",
            "business-contacts",
            "almost-strangers",
        ]:
            created_person = create_person_response(
                person_id=f"person-{valid_strength}",
                relationship_strength=valid_strength,
            )

            mocker.patch.object(client, "create_person", return_value=created_person)
            mocker.patch.object(client, "__aenter__", return_value=client)
            mocker.patch.object(client, "__aexit__", return_value=None)

            result = await people_tools.create_person_tool(
                mock_ctx,
                first_name="Test",
                last_name="Person",
                relationship_strength=valid_strength,
            )

            assert result["success"] is True
            assert result["person_id"] == f"person-{valid_strength}"

        # Test invalid relationship strength value
        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="Test",
            last_name="Person",
            relationship_strength="invalid-strength",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid relationship_strength" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_birthday_date_parsing(self, mocker: MockerFixture) -> None:
        """Tool should parse birthday date strings and handle validation errors."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Test valid date parsing
        created_person = create_person_response(
            person_id="person-birthday",
            birthday=date(1990, 12, 25),
        )

        mocker.patch.object(client, "create_person", return_value=created_person)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="Test",
            last_name="Person",
            birthday="1990-12-25",
        )

        assert result["success"] is True
        call_arg = client.create_person.call_args[0][0]  # type: ignore[attr-defined]
        assert call_arg.birthday == date(1990, 12, 25)  # type: ignore[attr-defined]

        # Test invalid date format
        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="Test",
            last_name="Person",
            birthday="invalid-date",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid birthday format" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_validation_error_422(self, mocker: MockerFixture) -> None:
        """Tool should handle validation errors from API correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskValidationError("Custom fields for email not defined in app"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Custom fields for email not defined in app" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_subscription_required_error_402(
        self, mocker: MockerFixture
    ) -> None:
        """Tool should handle subscription required errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskSubscriptionRequiredError("Upgrade required for people management"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "subscription_required"
        assert "Upgrade required for people management" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Tool should handle authentication errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskAuthenticationError("Invalid bearer token"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "authentication_error"
        assert "Invalid bearer token" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Tool should handle rate limit errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "rate_limit_error"
        assert "Rate limit exceeded" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_server_error_5xx(self, mocker: MockerFixture) -> None:
        """Tool should handle server errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskServerError("Internal server error", status_code=500),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "server_error"
        assert "Internal server error" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_service_unavailable_error_503(
        self, mocker: MockerFixture
    ) -> None:
        """Tool should handle service unavailable errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskServiceUnavailableError("Service temporarily unavailable"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "server_error"
        assert "Service temporarily unavailable" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_timeout_error(self, mocker: MockerFixture) -> None:
        """Tool should handle timeout errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "timeout_error"
        assert "Request timeout" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_network_error(self, mocker: MockerFixture) -> None:
        """Tool should handle network errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskNetworkError("Network connection failed"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "network_error"
        assert "Network connection failed" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_api_error(self, mocker: MockerFixture) -> None:
        """Tool should handle general API errors correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskAPIError("API error occurred"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "API error occurred" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_unexpected_error(self, mocker: MockerFixture) -> None:
        """Tool should handle unexpected exceptions correctly."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=RuntimeError("Unexpected error"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        assert result["success"] is False
        assert result["error"] == "unexpected_error"
        assert "Unexpected error creating person" in result["message"]

    @pytest.mark.asyncio
    async def test_create_person_tool_context_logging_success(self, mocker: MockerFixture) -> None:
        """Tool should log success cases through FastMCP context."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()
        created_person = create_person_response(person_id="person-log-test")

        mocker.patch.object(client, "create_person", return_value=created_person)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        # Verify context logging calls
        mock_ctx.info.assert_any_call("Creating new person")
        mock_ctx.info.assert_any_call("Successfully created person person-log-test")

    @pytest.mark.asyncio
    async def test_create_person_tool_context_logging_error(self, mocker: MockerFixture) -> None:
        """Tool should log error cases through FastMCP context."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskValidationError("Validation failed"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        await people_tools.create_person_tool(
            mock_ctx,
            first_name="John",
            last_name="Doe",
        )

        # Verify context error logging
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert "Person validation failed" in error_message


class TestPeopleToolsInitialization:
    """Test PeopleTools initialization and MCP integration."""

    def test_people_tools_initialization(self) -> None:
        """Test that PeopleTools initializes correctly with MCP and client."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        people_tools = PeopleTools(mcp, client)

        assert people_tools.mcp is mcp
        assert people_tools.lunatask_client is client

    def test_people_tools_registers_mcp_tools(self, mocker: MockerFixture) -> None:
        """Test that PeopleTools registers create_person tool with MCP."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        mock_tool = mocker.patch.object(mcp, "tool")

        PeopleTools(mcp, client)

        mock_tool.assert_called_once_with(
            name="create_person",
            description=mock.ANY,
        )
