"""Tests for PeopleTools create person tool end-to-end validation.

This module contains end-to-end validation tests for the PeopleTools create_person tool
that validate complete MCP tool functionality from client perspective.
"""

import inspect
from datetime import date

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskValidationError
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.people import PeopleTools
from tests.factories import create_person_response


class TestCreatePersonToolEndToEnd:
    """End-to-end validation tests for create_person tool discoverability and execution."""

    def test_create_person_tool_registered_with_mcp(self) -> None:
        """Test that create_person tool is properly registered and discoverable via MCP."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Initialize PeopleTools to register create_person tool
        PeopleTools(mcp, client)

        # Verify tool is registered in the MCP server
        tool_manager = mcp._tool_manager  # type: ignore[attr-defined] # Testing internal API
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined] # Testing internal API
        tool_names = [tool.name for tool in registered_tools]

        assert "create_person" in tool_names

        # Verify tool has proper schema
        create_person_tool = next(tool for tool in registered_tools if tool.name == "create_person")
        assert create_person_tool.description is not None
        assert "Create a person/contact in LunaTask" in create_person_tool.description

        # Verify tool has expected parameters - using try/except for optional schema inspection
        try:
            if hasattr(create_person_tool, "input_schema"):
                schema = getattr(create_person_tool, "input_schema", None)  # type: ignore[attr-defined] # Optional attribute inspection
                if isinstance(schema, dict) and "properties" in schema:
                    properties = schema["properties"]  # type: ignore[index] # Dict access for schema validation

                    # Required parameters
                    assert "first_name" in properties
                    assert "last_name" in properties

                    # Optional parameters
                    expected_optional_params = {
                        "relationship_strength",
                        "source",
                        "source_id",
                        "email",
                        "birthday",
                        "phone",
                    }
                    for param in expected_optional_params:
                        assert param in properties, f"Missing expected parameter: {param}"
        except (AttributeError, KeyError, TypeError):
            # Schema inspection is optional - tool registration is the main validation
            pass

    @pytest.mark.asyncio
    async def test_create_person_tool_complete_execution_flow(self, mocker: MockerFixture) -> None:
        """Test complete tool execution flow from MCP client perspective."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        # Mock context and successful API response
        mock_ctx = mocker.AsyncMock()
        created_person = create_person_response(
            person_id="e2e-person-123",
            relationship_strength="business-contacts",
            source="salesforce",
            source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
            email="john.doe@company.com",
            birthday=date(1985, 5, 15),
            phone="+1-555-987-6543",
        )

        mocker.patch.object(client, "create_person", return_value=created_person)
        mock_context_manager = mocker.AsyncMock()
        mock_context_manager.__aenter__.return_value = client
        mock_context_manager.__aexit__.return_value = None
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test tool execution with full parameter set
        result = await people_tools.create_person_tool(
            ctx=mock_ctx,
            first_name="John",
            last_name="Doe",
            relationship_strength="business-contacts",
            source="salesforce",
            source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
            email="john.doe@company.com",
            birthday="1985-05-15",
            phone="+1-555-987-6543",
        )

        # Verify successful response structure
        assert result["success"] is True
        assert result["person_id"] == "e2e-person-123"
        assert result["message"] == "Person created successfully"

        # Verify client was called correctly
        client.create_person.assert_called_once()  # type: ignore[attr-defined]
        call_arg = client.create_person.call_args[0][0]  # type: ignore[attr-defined]

        # Verify all parameters were correctly passed through
        assert call_arg.first_name == "John"  # type: ignore[attr-defined]
        assert call_arg.last_name == "Doe"  # type: ignore[attr-defined]
        assert call_arg.relationship_strength == "business-contacts"  # type: ignore[attr-defined]
        assert call_arg.source == "salesforce"  # type: ignore[attr-defined]
        assert call_arg.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"  # type: ignore[attr-defined]
        assert call_arg.email == "john.doe@company.com"  # type: ignore[attr-defined]
        assert call_arg.birthday == date(1985, 5, 15)  # type: ignore[attr-defined]
        assert call_arg.phone == "+1-555-987-6543"  # type: ignore[attr-defined]

        # Verify context logging was called
        mock_ctx.info.assert_any_call("Creating new person")
        mock_ctx.info.assert_any_call("Successfully created person e2e-person-123")

    @pytest.mark.asyncio
    async def test_create_person_tool_duplicate_workflow(self, mocker: MockerFixture) -> None:
        """Test complete duplicate detection workflow."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock duplicate response (client returns None)
        mocker.patch.object(client, "create_person", return_value=None)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            ctx=mock_ctx,
            first_name="Jane",
            last_name="Doe",
            source="github",
            source_id="existing-user-456",
        )

        # Verify duplicate response structure
        assert result["success"] is True
        assert result["duplicate"] is True
        assert result["message"] == "Person already exists for this source/source_id"

        # Verify context logging for duplicate
        mock_ctx.info.assert_any_call("Creating new person")
        mock_ctx.info.assert_any_call("Person already exists; duplicate create skipped")

    @pytest.mark.asyncio
    async def test_create_person_tool_error_handling_workflow(self, mocker: MockerFixture) -> None:
        """Test complete error handling workflow through the stack."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock validation error from client
        mocker.patch.object(
            client,
            "create_person",
            side_effect=LunaTaskValidationError("Custom fields for email not defined in app"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await people_tools.create_person_tool(
            ctx=mock_ctx,
            first_name="Test",
            last_name="User",
            email="test@example.com",
        )

        # Verify error response structure
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Custom fields for email not defined in app" in result["message"]

        # Verify error was logged to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert "Person validation failed" in error_message

    @pytest.mark.asyncio
    async def test_create_person_tool_parameter_validation_workflow(
        self, mocker: MockerFixture
    ) -> None:
        """Test parameter validation workflow before API call."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock client to ensure it's not called due to validation failure
        mock_create_person = mocker.patch.object(client, "create_person")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Test invalid date format
        result = await people_tools.create_person_tool(
            ctx=mock_ctx,
            first_name="Test",
            last_name="User",
            birthday="invalid-date-format",
        )

        # Verify validation error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid birthday format" in result["message"]

        # Verify client was not called due to pre-validation failure
        mock_create_person.assert_not_called()

        # Verify error was logged to context
        mock_ctx.error.assert_called_once()

    def test_create_person_tool_integration_with_fastmcp_context(self) -> None:
        """Test that tool properly integrates with FastMCP context system."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Initialize PeopleTools
        people_tools = PeopleTools(mcp, client)

        # Verify the tool method has proper signature for FastMCP
        create_person_method = people_tools.create_person_tool
        signature = inspect.signature(create_person_method)

        # Verify first parameter is context
        parameters = list(signature.parameters.values())
        min_params = 3  # ctx, first_name, last_name minimum
        assert len(parameters) >= min_params
        assert parameters[0].name == "ctx"

        # Verify required parameters
        param_names = [param.name for param in parameters]
        assert "first_name" in param_names
        assert "last_name" in param_names

        # Verify optional parameters
        expected_optional = {
            "relationship_strength",
            "source",
            "source_id",
            "email",
            "birthday",
            "phone",
        }
        actual_optional = {param.name for param in parameters if param.default is not param.empty}
        assert expected_optional.issubset(actual_optional)

    @pytest.mark.asyncio
    async def test_create_person_tool_logging_output_verification(
        self, mocker: MockerFixture
    ) -> None:
        """Test logging output verification through complete execution."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        people_tools = PeopleTools(mcp, client)

        mock_ctx = mocker.AsyncMock()

        # Mock logger to capture stderr logging
        mock_logger = mocker.patch("lunatask_mcp.tools.people.logger")

        created_person = create_person_response(person_id="log-test-789")

        mocker.patch.object(client, "create_person", return_value=created_person)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        await people_tools.create_person_tool(
            mock_ctx,
            first_name="Log",
            last_name="Test",
        )

        # Verify stderr logging calls
        mock_logger.info.assert_called_with("Successfully created person %s", "log-test-789")

        # Verify FastMCP context logging calls
        mock_ctx.info.assert_any_call("Creating new person")
        mock_ctx.info.assert_any_call("Successfully created person log-test-789")

        # Verify no error logging occurred
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()
        mock_logger.exception.assert_not_called()
        mock_ctx.error.assert_not_called()
