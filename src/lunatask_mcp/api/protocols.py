"""Protocol definitions for LunaTask API client mixins.

This module provides typing protocols that enable mixins to reference
base client methods without circular imports, supporting strict pyright
type checking during client modularization.
"""

from typing import Any, Protocol


class BaseClientProtocol(Protocol):
    """Protocol defining the interface that mixins can depend on.

    This protocol declares the essential methods that mixins need to access
    from the base client, enabling proper type checking without tight coupling.
    """

    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the LunaTask API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            data: JSON data for request body
            params: Query parameters

        Returns:
            Dict[str, Any]: Parsed JSON response
        """
        ...

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers with bearer token.

        Returns:
            Dict[str, str]: Headers including Authorization and Content-Type
        """
        ...

    def _get_redacted_headers(self) -> dict[str, str]:
        """Get headers with redacted bearer token for logging.

        Returns:
            Dict[str, str]: Headers with redacted authorization token
        """
        ...
