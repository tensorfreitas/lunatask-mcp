"""LunaTask API client for secure authentication and request handling.

This module provides the LunaTaskClient class for making authenticated
requests to the LunaTask API with proper error handling and security.
"""

import logging
import types
from typing import Any, NoReturn

import httpx

from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import TaskCreate, TaskResponse, TaskUpdate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.rate_limiter import TokenBucketLimiter

# HTTP status code constants
_HTTP_BAD_REQUEST = 400
_HTTP_UNAUTHORIZED = 401
_HTTP_PAYMENT_REQUIRED = 402
_HTTP_NOT_FOUND = 404
_HTTP_UNPROCESSABLE_ENTITY = 422
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_INTERNAL_SERVER_ERROR = 500
_HTTP_SERVICE_UNAVAILABLE = 503
_HTTP_TIMEOUT = 524
_HTTP_BAD_GATEWAY = 600

# Configure logger to write to stderr
logger = logging.getLogger(__name__)


class LunaTaskClient:
    """Client for making authenticated requests to the LunaTask API.

    This client handles secure bearer token authentication, HTTP connection
    management, and comprehensive error handling while ensuring that
    bearer tokens are never exposed in logs or error messages.
    """

    def __init__(self, config: ServerConfig) -> None:
        """Initialize the LunaTask API client.

        Args:
            config: Server configuration containing bearer token and base URL
        """

        self._config = config
        self._base_url = str(config.lunatask_base_url).rstrip("/")
        self._bearer_token = config.lunatask_bearer_token
        self._http_client: httpx.AsyncClient | None = None

        # Initialize rate limiter with configuration
        self._rate_limiter = TokenBucketLimiter(
            rpm=config.rate_limit_rpm, burst=config.rate_limit_burst
        )

    def __str__(self) -> str:
        """Return string representation without exposing bearer token."""
        return f"LunaTaskClient(base_url={self._base_url}, token=***redacted***)"

    def __repr__(self) -> str:
        """Return repr without exposing bearer token."""
        return f"LunaTaskClient(base_url='{self._base_url}', token='***redacted***')"

    async def __aenter__(self) -> "LunaTaskClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit with cleanup."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper configuration.

        Returns:
            httpx.AsyncClient: Configured async HTTP client
        """
        if self._http_client is None:
            timeout = httpx.Timeout(
                connect=5.0,  # 5 seconds to establish connection
                read=10.0,  # 10 seconds to read response
                write=10.0,  # 10 seconds to send request
                pool=10.0,  # 10 seconds for connection pooling
            )

            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            )

            self._http_client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
            )

        return self._http_client

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers with bearer token.

        Returns:
            Dict[str, str]: Headers including Authorization and Content-Type
        """
        return {
            "Authorization": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json",
        }

    def _get_redacted_headers(self) -> dict[str, str]:
        """Get headers with redacted bearer token for logging.

        Returns:
            Dict[str, str]: Headers with redacted authorization token
        """
        return {
            "Authorization": "Bearer ***redacted***",
            "Content-Type": "application/json",
        }

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> NoReturn:
        """Handle HTTP status errors and raise appropriate exceptions.

        Args:
            error: HTTP status error from httpx

        Raises:
            LunaTaskBadRequestError: For 400 Bad Request
            LunaTaskAuthenticationError: For 401 Unauthorized
            LunaTaskSubscriptionRequiredError: For 402 Payment Required
            LunaTaskNotFoundError: For 404 Not Found
            LunaTaskValidationError: For 422 Unprocessable Entity
            LunaTaskRateLimitError: For 429 Too Many Requests
            LunaTaskServerError: For 5xx server errors
            LunaTaskServiceUnavailableError: For 503 Service Unavailable
            LunaTaskTimeoutError: For 524 Request Timed Out
            LunaTaskAPIError: For other HTTP errors
        """
        status_code = error.response.status_code

        if status_code == _HTTP_BAD_REQUEST:
            logger.error("Bad request to LunaTask API - invalid parameters")
            raise LunaTaskBadRequestError from error
        if status_code == _HTTP_UNAUTHORIZED:
            logger.error("Authentication failed with LunaTask API")
            raise LunaTaskAuthenticationError from error
        if status_code == _HTTP_PAYMENT_REQUIRED:
            logger.error("LunaTask subscription required - free plan limit reached")
            raise LunaTaskSubscriptionRequiredError from error
        if status_code == _HTTP_NOT_FOUND:
            logger.error("Resource not found: %s", error.request.url)
            raise LunaTaskNotFoundError from error
        if status_code == _HTTP_UNPROCESSABLE_ENTITY:
            logger.error("LunaTask API validation error - entity not valid")
            raise LunaTaskValidationError from error
        if status_code == _HTTP_TOO_MANY_REQUESTS:
            logger.error("Rate limit exceeded for LunaTask API")
            raise LunaTaskRateLimitError from error
        if status_code == _HTTP_SERVICE_UNAVAILABLE:
            logger.error("LunaTask API temporarily unavailable for maintenance")
            raise LunaTaskServiceUnavailableError from error
        if status_code == _HTTP_TIMEOUT:
            logger.error("LunaTask API request timed out")
            raise LunaTaskTimeoutError(status_code=status_code) from error
        if _HTTP_INTERNAL_SERVER_ERROR <= status_code < _HTTP_BAD_GATEWAY:
            logger.error("LunaTask API server error: %s", status_code)
            raise LunaTaskServerError("", status_code) from error
        logger.error("LunaTask API error: %s", status_code)
        raise LunaTaskAPIError("", status_code) from error

    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the LunaTask API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: JSON data for request body
            params: Query parameters

        Returns:
            Dict[str, Any]: Parsed JSON response

        Raises:
            LunaTaskBadRequestError: Invalid request parameters
            LunaTaskAuthenticationError: Authentication failed
            LunaTaskSubscriptionRequiredError: Subscription required
            LunaTaskNotFoundError: Resource not found
            LunaTaskValidationError: Entity validation failed
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error
            LunaTaskServiceUnavailableError: Service unavailable
            LunaTaskNetworkError: Network connectivity error
            LunaTaskTimeoutError: Request timeout
            LunaTaskAPIError: Other API errors
        """
        # Acquire rate limiting token before making request
        await self._rate_limiter.acquire()

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        headers = self._get_auth_headers()

        try:
            http_client = self._get_http_client()

            # Log request with redacted headers
            redacted_headers = self._get_redacted_headers()
            logger.debug(
                "Making %s request to %s with headers: %s",
                method,
                url,
                redacted_headers,
            )

            response = await http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
            )

            # Raise for HTTP status errors
            response.raise_for_status()

            # Parse and return JSON response
            result = response.json()
            logger.debug("Successful API response: %s", response.status_code)

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.TimeoutException as e:
            logger.exception("Request timeout")
            raise LunaTaskTimeoutError from e
        except httpx.NetworkError as e:
            logger.exception("Network error")
            raise LunaTaskNetworkError from e
        except Exception as e:
            logger.exception("Unexpected error during API request")
            raise LunaTaskAPIError.create_unexpected_error(method, endpoint) from e
        else:
            return result

    async def get_tasks(self, **params: str | int | None) -> list[TaskResponse]:
        """Retrieve all tasks from the LunaTask API.

        Args:
            **params: Optional query parameters for pagination/filtering
                     (e.g., limit, offset, status)

        Returns:
            List[TaskResponse]: List of task objects from the API

        Raises:
            LunaTaskAuthenticationError: Invalid bearer token
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error occurred
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """
        # Prepare params dict, filtering out None values
        query_params = {k: v for k, v in params.items() if v is not None} if params else None

        # Make authenticated request to /v1/tasks endpoint
        if query_params:
            response_data = await self.make_request("GET", "tasks", params=query_params)
        else:
            response_data = await self.make_request("GET", "tasks")

        # Parse response JSON into TaskResponse model list
        # The tasks API returns a list of task dictionaries, but make_request() is typed
        # to return dict[str, Any] for general use. We know from the API spec that GET /v1/tasks
        # specifically returns a JSON array of task objects, so this assignment is safe.
        task_list: list[dict[str, Any]] = response_data  # type: ignore[assignment]
        try:
            tasks = [TaskResponse(**task_data) for task_data in task_list]
        except Exception as e:
            logger.exception("Failed to parse task response data")
            task_count = len(task_list) if task_list else "unknown"
            raise LunaTaskAPIError.create_parse_error("tasks", task_count=task_count) from e
        else:
            logger.debug("Successfully retrieved %d tasks", len(tasks))
            return tasks

    async def get_task(self, task_id: str) -> TaskResponse:
        """Retrieve a single task from the LunaTask API by ID.

        Args:
            task_id: The unique identifier for the task to retrieve

        Returns:
            TaskResponse: Task object from the API

        Raises:
            LunaTaskNotFoundError: Task not found
            LunaTaskAuthenticationError: Invalid bearer token
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error occurred
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """
        # Make authenticated request to /v1/tasks/{task_id} endpoint
        response_data = await self.make_request("GET", f"tasks/{task_id}")

        # Parse response JSON into TaskResponse model instance
        try:
            task = TaskResponse(**response_data)
        except Exception as e:
            logger.exception("Failed to parse single task response data")
            raise LunaTaskAPIError.create_parse_error(f"tasks/{task_id}", task_id=task_id) from e
        else:
            logger.debug("Successfully retrieved task: %s", task.id)
            return task

    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """Create a new task in the LunaTask API.

        Args:
            task_data: TaskCreate object containing task data to create

        Returns:
            TaskResponse: Created task object from the API with assigned ID

        Raises:
            LunaTaskValidationError: Validation error (422)
            LunaTaskSubscriptionRequiredError: Subscription required (402)
            LunaTaskAuthenticationError: Invalid bearer token (401)
            LunaTaskRateLimitError: Rate limit exceeded (429)
            LunaTaskServerError: Server error occurred (5xx)
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """
        # Convert TaskCreate model to JSON data
        json_data = task_data.model_dump(exclude_none=True)

        # Make authenticated request to POST /v1/tasks endpoint
        response_data = await self.make_request("POST", "tasks", data=json_data)

        # Parse response JSON into TaskResponse model instance
        try:
            task = TaskResponse(**response_data)
        except Exception as e:
            logger.exception("Failed to parse created task response data")
            task_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error("tasks", task_name=task_name) from e
        else:
            logger.debug("Successfully created task: %s", task.id)
            return task

    async def update_task(self, task_id: str, update: TaskUpdate) -> TaskResponse:
        """Update an existing task in the LunaTask API.

        Args:
            task_id: The unique identifier for the task to update
            update: TaskUpdate object containing fields to update

        Returns:
            TaskResponse: Updated task object from the API

        Raises:
            LunaTaskNotFoundError: Task not found (404)
            LunaTaskBadRequestError: Invalid update data (400)
            LunaTaskAuthenticationError: Invalid bearer token (401)
            LunaTaskRateLimitError: Rate limit exceeded (429)
            LunaTaskServerError: Server error occurred (5xx)
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """
        # Convert TaskUpdate model to JSON data, excluding None values for partial update
        json_data = update.model_dump(exclude_none=True)

        # Make authenticated request to PATCH /v1/tasks/{task_id} endpoint
        response_data = await self.make_request("PATCH", f"tasks/{task_id}", data=json_data)

        # Parse response JSON into TaskResponse model instance
        try:
            task = TaskResponse(**response_data)
        except Exception as e:
            logger.exception("Failed to parse updated task response data")
            raise LunaTaskAPIError.create_parse_error(f"tasks/{task_id}", task_id=task_id) from e
        else:
            logger.debug("Successfully updated task: %s", task.id)
            return task

    async def test_connectivity(self) -> bool:
        """Test connectivity to the LunaTask API.

        Makes a simple authenticated request to verify that the bearer token
        is valid and the API is accessible.

        Returns:
            bool: True if connectivity test succeeds, False otherwise
        """
        try:
            result = await self.make_request("GET", "ping")
            if result.get("message") == "pong":
                logger.info("LunaTask API connectivity test successful")
                return True
            # Early return pattern is clearer here than else block
            logger.warning("LunaTask API connectivity test failed: unexpected response")
            return False  # noqa: TRY300
        except LunaTaskAPIError as e:
            logger.warning("LunaTask API connectivity test failed: %s", e)
            return False
        except Exception:
            logger.exception("LunaTask API connectivity test failed with unexpected error")
            return False
