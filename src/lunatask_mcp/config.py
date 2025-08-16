"""Configuration module for LunaTask MCP server.

This module provides the ServerConfig Pydantic model for managing server
configuration from files, command-line arguments, and defaults.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ServerConfig(BaseModel):
    """Server configuration model with validation and default values.

    This Pydantic model handles all server configuration including API tokens,
    URLs, ports, and logging levels with comprehensive validation.
    """

    lunatask_bearer_token: str = Field(
        ...,
        description="Bearer token for LunaTask API authentication",
    )

    lunatask_base_url: HttpUrl = Field(
        default=HttpUrl("https://api.lunatask.app/v1/"),
        description="Base URL for LunaTask API endpoints",
    )

    port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Port number for future HTTP transport support",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level for the application",
    )

    config_file: str | None = Field(
        default=None,
        description="Path to configuration file",
    )

    test_connectivity_on_startup: bool = Field(
        default=False,
        description="Test LunaTask API connectivity during server startup",
    )

    @field_validator("lunatask_base_url")
    @classmethod
    def validate_https_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that the base URL uses HTTPS protocol.

        Args:
            v: The URL value to validate.

        Returns:
            HttpUrl: The validated HTTPS URL.

        Raises:
            ValueError: If the URL does not use HTTPS protocol.
        """
        if v.scheme != "https":
            msg = "URL must use HTTPS"
            raise ValueError(msg)
        return v

    def to_redacted_dict(self) -> dict[str, Any]:
        """Return a dictionary representation with sensitive data redacted.

        This method creates a safe representation of the configuration
        for logging purposes, ensuring that bearer tokens are not exposed.

        Returns:
            dict[str, Any]: Configuration dictionary with secrets redacted.
        """
        config_dict = self.model_dump()
        config_dict["lunatask_bearer_token"] = "***redacted***"  # noqa: S105 - redaction placeholder, not actual secret
        # Convert HttpUrl to string for serialization
        config_dict["lunatask_base_url"] = str(config_dict["lunatask_base_url"])
        return config_dict
