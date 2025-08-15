"""Custom exceptions for LunaTask API operations.

This module defines the exception hierarchy for LunaTask API errors,
ensuring proper error handling and secure logging.
"""


class LunaTaskAPIError(Exception):
    """Base exception for all LunaTask API errors.

    This exception ensures that bearer tokens are never exposed
    in error messages or logs.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize LunaTask API error.

        Args:
            message: Error message (must not contain bearer token)
            status_code: HTTP status code if applicable
        """
        self.status_code = status_code
        super().__init__(message)


class LunaTaskAuthenticationError(LunaTaskAPIError):
    """Raised when authentication fails (401 Unauthorized)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize authentication error.

        Args:
            message: Error message (defaults to generic message)
        """
        super().__init__(message, status_code=401)


class LunaTaskNotFoundError(LunaTaskAPIError):
    """Raised when a resource is not found (404 Not Found)."""

    def __init__(self, message: str = "Resource not found") -> None:
        """Initialize not found error.

        Args:
            message: Error message describing what was not found
        """
        super().__init__(message, status_code=404)


class LunaTaskRateLimitError(LunaTaskAPIError):
    """Raised when rate limit is exceeded (429 Too Many Requests)."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        """Initialize rate limit error.

        Args:
            message: Error message about rate limiting
        """
        super().__init__(message, status_code=429)


class LunaTaskServerError(LunaTaskAPIError):
    """Raised when server returns 5xx errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        """Initialize server error.

        Args:
            message: Error message from server
            status_code: HTTP status code (5xx)
        """
        super().__init__(message, status_code=status_code)


class LunaTaskNetworkError(LunaTaskAPIError):
    """Raised when network operations fail."""

    def __init__(self, message: str = "Network error occurred") -> None:
        """Initialize network error.

        Args:
            message: Error message describing network issue
        """
        super().__init__(message, status_code=None)


class LunaTaskTimeoutError(LunaTaskAPIError):
    """Raised when requests timeout."""

    def __init__(self, message: str = "Request timeout") -> None:
        """Initialize timeout error.

        Args:
            message: Error message about timeout
        """
        super().__init__(message, status_code=None)
