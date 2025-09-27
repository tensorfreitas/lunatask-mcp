"""Configuration module for LunaTask MCP server.

This module provides the ServerConfig Pydantic model for managing server
configuration from files, command-line arguments, and defaults.
"""

from importlib.metadata import version
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

    rate_limit_rpm: int = Field(
        default=60,
        ge=1,
        le=10000,
        description="Rate limit: requests per minute",
    )

    rate_limit_burst: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Rate limit: burst capacity",
    )

    http_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="HTTP client retry count for failed requests",
    )

    http_backoff_start_seconds: float = Field(
        default=0.25,
        ge=0.1,
        le=10.0,
        description="HTTP client backoff start time in seconds",
    )

    http_min_mutation_interval_seconds: float = Field(
        default=0.0,
        ge=0.0,
        le=5.0,
        description=(
            "Minimum delay between mutating HTTP requests (POST/PATCH/DELETE) in seconds. "
            "Leave at 0.0 to rely solely on the token bucket rate limiter; increase when "
            "coordinating with external throttling constraints."
        ),
    )

    http_user_agent: str = Field(
        default_factory=lambda: f"lunatask-mcp/{version('lunatask-mcp')}",
        description="HTTP client User-Agent header",
    )

    timeout_connect: float = Field(
        default=5.0,
        ge=1.0,
        le=30.0,
        description="HTTP connection timeout in seconds",
    )

    timeout_read: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="HTTP read timeout in seconds",
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
