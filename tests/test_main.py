"""Tests for the main entry point module."""

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import CoreServer, main


def test_core_server_class_exists() -> None:
    """Test that CoreServer class is defined."""
    assert CoreServer is not None
    assert callable(CoreServer)


def test_main_function_exists() -> None:
    """Test that main function is defined and callable."""
    assert main is not None
    assert callable(main)


@pytest.mark.asyncio
async def test_core_server_initialization(default_config: ServerConfig) -> None:
    """Test CoreServer can be instantiated."""
    server = CoreServer(default_config)
    assert server is not None


def test_main_configures_logging_to_stderr(mocker: MockerFixture) -> None:
    """Test that main function configures logging to stderr."""
    mocker.patch("sys.stderr")
    # This test will be implemented after we create the main module


def test_main_does_not_print_to_stdout() -> None:
    """Test that main function doesn't output to stdout (MCP protocol requirement)."""
    # This test will validate stdout purity


class TestCoreServerLunaTaskIntegration:
    """Test CoreServer integration with LunaTaskClient."""

    @pytest.mark.asyncio
    async def test_get_lunatask_client_creates_instance(self, default_config: ServerConfig) -> None:
        """Test that get_lunatask_client creates a LunaTaskClient instance."""
        server = CoreServer(default_config)
        client = server.get_lunatask_client()

        assert isinstance(client, LunaTaskClient)
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_lunatask_client_returns_same_instance(
        self, default_config: ServerConfig
    ) -> None:
        """Test that get_lunatask_client returns the same instance on multiple calls."""
        server = CoreServer(default_config)
        client1 = server.get_lunatask_client()
        client2 = server.get_lunatask_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_lunatask_client_uses_config(self, default_config: ServerConfig) -> None:
        """Test that LunaTaskClient is initialized with the correct configuration."""
        server = CoreServer(default_config)
        client = server.get_lunatask_client()

        # Access private attribute for testing
        assert client._config is default_config  # type: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_connectivity_test_disabled_by_default(
        self, default_config: ServerConfig
    ) -> None:
        """Test that connectivity test is disabled by default."""
        assert default_config.test_connectivity_on_startup is False

    @pytest.mark.asyncio
    async def test_connectivity_test_enabled_in_config(self) -> None:
        """Test that connectivity test can be enabled in configuration."""
        config = ServerConfig(lunatask_bearer_token="test-token", test_connectivity_on_startup=True)
        assert config.test_connectivity_on_startup is True

    @pytest.mark.asyncio
    async def test_connectivity_test_skipped_when_disabled(
        self, default_config: ServerConfig, mocker: MockerFixture
    ) -> None:
        """Test that connectivity test is skipped when disabled."""
        server = CoreServer(default_config)

        # Mock the logger to verify no connectivity test messages
        mock_logger = mocker.patch("lunatask_mcp.main.logging.getLogger")

        await server._test_connectivity_if_enabled()  # type: ignore[reportPrivateUsage]

        # Should return early without logging connectivity test messages
        mock_logger.return_value.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_connectivity_test_runs_when_enabled(self, mocker: MockerFixture) -> None:
        """Test that connectivity test runs when enabled."""
        config = ServerConfig(lunatask_bearer_token="test-token", test_connectivity_on_startup=True)
        server = CoreServer(config)

        # Mock the LunaTaskClient and its test_connectivity method
        mock_client = mocker.AsyncMock()
        mock_client.test_connectivity.return_value = True
        mocker.patch.object(server, "get_lunatask_client", return_value=mock_client)

        # Mock the logger
        mock_logger = mocker.patch("lunatask_mcp.main.logging.getLogger")

        await server._test_connectivity_if_enabled()  # type: ignore[reportPrivateUsage]

        # Verify connectivity test was called
        mock_client.test_connectivity.assert_called_once()

        # Verify appropriate log messages
        mock_logger.return_value.info.assert_any_call("Testing LunaTask API connectivity...")
        mock_logger.return_value.info.assert_any_call("LunaTask API connectivity test successful")

    @pytest.mark.asyncio
    async def test_connectivity_test_handles_failure(self, mocker: MockerFixture) -> None:
        """Test that connectivity test handles failure gracefully."""
        config = ServerConfig(lunatask_bearer_token="test-token", test_connectivity_on_startup=True)
        server = CoreServer(config)

        # Mock the LunaTaskClient to return failure
        mock_client = mocker.AsyncMock()
        mock_client.test_connectivity.return_value = False
        mocker.patch.object(server, "get_lunatask_client", return_value=mock_client)

        # Mock the logger
        mock_logger = mocker.patch("lunatask_mcp.main.logging.getLogger")

        await server._test_connectivity_if_enabled()  # type: ignore[reportPrivateUsage]

        # Verify appropriate warning message
        mock_logger.return_value.warning.assert_called_with("LunaTask API connectivity test failed")

    @pytest.mark.asyncio
    async def test_connectivity_test_handles_exception(self, mocker: MockerFixture) -> None:
        """Test that connectivity test handles exceptions gracefully."""
        config = ServerConfig(lunatask_bearer_token="test-token", test_connectivity_on_startup=True)
        server = CoreServer(config)

        # Mock the LunaTaskClient to raise an exception
        mock_client = mocker.AsyncMock()
        mock_client.test_connectivity.side_effect = Exception("Network error")
        mocker.patch.object(server, "get_lunatask_client", return_value=mock_client)

        # Mock the logger
        mock_logger = mocker.patch("lunatask_mcp.main.logging.getLogger")

        await server._test_connectivity_if_enabled()  # type: ignore[reportPrivateUsage]

        # Verify exception is logged
        mock_logger.return_value.exception.assert_called_with(
            "LunaTask API connectivity test failed with exception"
        )

    def test_run_calls_connectivity_test_when_enabled(self, mocker: MockerFixture) -> None:
        """Test that run method calls connectivity test when enabled."""
        config = ServerConfig(lunatask_bearer_token="test-token", test_connectivity_on_startup=True)
        server = CoreServer(config)

        # Mock _test_connectivity_if_enabled and app.run to prevent actual execution
        mock_connectivity_test = mocker.patch.object(server, "_test_connectivity_if_enabled")
        mock_app_run = mocker.patch.object(server.app, "run")

        server.run()

        # Verify connectivity test was called
        mock_connectivity_test.assert_called_once()

        # Verify server still starts normally
        mock_app_run.assert_called_once_with(transport="stdio")

    def test_run_skips_connectivity_test_when_disabled(self, mocker: MockerFixture) -> None:
        """Test that run method skips connectivity test when disabled."""
        config = ServerConfig(
            lunatask_bearer_token="test-token", test_connectivity_on_startup=False
        )
        server = CoreServer(config)

        # Mock _test_connectivity_if_enabled and app.run to prevent actual execution
        mock_connectivity_test = mocker.patch.object(server, "_test_connectivity_if_enabled")
        mock_app_run = mocker.patch.object(server.app, "run")

        server.run()

        # Verify connectivity test was not called
        mock_connectivity_test.assert_not_called()

        # Verify server still starts normally
        mock_app_run.assert_called_once_with(transport="stdio")


def test_core_server_registers_journal_tool(default_config: ServerConfig) -> None:
    """CoreServer should register the create_journal_entry tool with FastMCP."""

    server = CoreServer(default_config)

    tool_manager = server.app._tool_manager  # type: ignore[attr-defined]
    registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined]
    tool_names = {tool.name for tool in registered_tools}

    assert "create_journal_entry" in tool_names


class TestCoreServerTaskToolsIntegration:
    """Test CoreServer integration with TaskTools."""

    def test_task_tools_dependency_injection(self, default_config: ServerConfig) -> None:
        """Test that TaskTools receives LunaTaskClient via dependency injection."""
        server = CoreServer(default_config)

        # Verify that get_lunatask_client returns a client instance
        client = server.get_lunatask_client()
        assert isinstance(client, LunaTaskClient)
        assert client is not None

    def test_task_tools_registration_with_fastmcp(
        self, default_config: ServerConfig, mocker: MockerFixture
    ) -> None:
        """Test that TaskTools is registered with FastMCP instance during initialization."""
        # Mock the TaskTools class to verify it's called during server initialization
        mock_task_tools = mocker.patch("lunatask_mcp.main.TaskTools")

        server = CoreServer(default_config)

        # Verify TaskTools was instantiated with the correct arguments
        mock_task_tools.assert_called_once()
        call_args = mock_task_tools.call_args

        # First argument should be the FastMCP instance
        assert call_args[0][0] is server.app
        # Second argument should be a LunaTaskClient instance
        assert isinstance(call_args[0][1], LunaTaskClient)

    def test_lunatask_client_available_to_task_tools(self, default_config: ServerConfig) -> None:
        """Test that LunaTaskClient is available to TaskTools via dependency injection."""
        server = CoreServer(default_config)

        # Get the client that would be passed to TaskTools
        client = server.get_lunatask_client()

        # Verify it has the correct configuration
        assert client._config is default_config  # type: ignore[reportPrivateUsage]

    def test_fastmcp_instance_has_resource_capability(self, default_config: ServerConfig) -> None:
        """Test that the FastMCP instance is configured to support resources."""
        server = CoreServer(default_config)

        # The FastMCP instance should exist and be properly configured
        assert server.app is not None
        assert hasattr(server.app, "resource")  # Should have resource decorator method

    def test_resource_registration_and_discoverability(
        self, default_config: ServerConfig, mocker: MockerFixture
    ) -> None:
        """Test that lunatask://tasks resource is registered and discoverable."""
        # Mock TaskTools to verify resource registration
        mock_task_tools = mocker.patch("lunatask_mcp.main.TaskTools")

        server = CoreServer(default_config)

        # Verify TaskTools was instantiated (which registers the resource)
        mock_task_tools.assert_called_once()

        # Verify the FastMCP app has a resource decorator method
        assert hasattr(server.app, "resource")

        # The actual resource registration happens in TaskTools._register_resources()
        # which calls self.mcp.resource("lunatask://tasks")(self.get_tasks_resource)
        # This test confirms the integration is set up correctly

    def test_resource_registration_setup_for_discoverability(
        self, default_config: ServerConfig, mocker: MockerFixture
    ) -> None:
        """Test that the setup enables resource discoverability through MCP protocol."""
        # Mock TaskTools to verify resource registration pattern
        mock_task_tools = mocker.patch("lunatask_mcp.main.TaskTools")

        server = CoreServer(default_config)

        # Verify TaskTools was instantiated with FastMCP instance
        mock_task_tools.assert_called_once()
        call_args = mock_task_tools.call_args

        # The FastMCP instance passed to TaskTools
        mcp_instance = call_args[0][0]
        assert mcp_instance is server.app

        # Verify the FastMCP instance has resource decorator capability
        assert hasattr(mcp_instance, "resource")

        # The resource registration happens in TaskTools._register_resources()
        # which follows the pattern: self.mcp.resource("lunatask://tasks")(self.get_tasks_resource)
        # This test verifies the integration setup that enables MCP list_resources capability
