"""LunaTask API client for secure authentication and request handling.

This module provides the LunaTaskClient class for making authenticated
requests to the LunaTask API with proper error handling and security.
"""

import asyncio
import json
import logging
import types
from dataclasses import dataclass
from datetime import date
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
from lunatask_mcp.api.models import NoteCreate, NoteResponse, TaskCreate, TaskResponse, TaskUpdate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.rate_limiter import TokenBucketLimiter

# HTTP status code constants
_HTTP_NO_CONTENT = 204
_HTTP_BAD_REQUEST = 400
_HTTP_UNAUTHORIZED = 401
_HTTP_PAYMENT_REQUIRED = 402
_HTTP_NOT_FOUND = 404
_HTTP_UNPROCESSABLE_ENTITY = 422
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_INTERNAL_SERVER_ERROR = 500
_HTTP_SERVICE_UNAVAILABLE = 503
_HTTP_TIMEOUT = 524
_HTTP_BAD_GATEWAY = 502
_HTTP_MAX_SERVER_ERROR = 600

_RETRYABLE_STATUS_CODES = {
    _HTTP_INTERNAL_SERVER_ERROR,
    _HTTP_BAD_GATEWAY,
    _HTTP_SERVICE_UNAVAILABLE,
    _HTTP_TIMEOUT,
}


@dataclass(slots=True)
class _RetryContext:
    """Internal container storing retry metadata for a single attempt."""

    attempt: int
    max_attempts: int
    backoff: float
    method: str
    url: str


# Configure logger to write to stderr
logger = logging.getLogger(__name__)

# Guardrail constants
_MAX_LIST_LIMIT = 50


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
                connect=self._config.timeout_connect,
                read=self._config.timeout_read,
                write=10.0,
                pool=10.0,
            )

            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            )

            headers = {"User-Agent": self._config.http_user_agent}

            self._http_client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
                headers=headers,
            )

        return self._http_client

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        """Check whether an HTTP status code should trigger a retry."""
        return status_code in _RETRYABLE_STATUS_CODES

    @staticmethod
    def _has_remaining_attempts(context: _RetryContext) -> bool:
        """Determine whether another retry attempt is allowed."""
        return context.attempt < context.max_attempts - 1

    def _handle_http_status_retry(
        self,
        error: httpx.HTTPStatusError,
        context: _RetryContext,
    ) -> bool:
        """Handle retryable HTTP status errors.

        Returns:
            bool: True when caller should retry after applying backoff.
        """
        status_code = error.response.status_code
        if not self._has_remaining_attempts(context):
            self._handle_http_error(error)
        if not self._is_retryable_status(status_code):
            self._handle_http_error(error)

        logger.warning(
            "Retryable HTTP status %s for %s %s; retrying in %.2fs (attempt %d of %d)",
            status_code,
            context.method,
            context.url,
            context.backoff,
            context.attempt + 1,
            context.max_attempts,
        )
        return True

    def _handle_transient_exception(
        self,
        error: httpx.TimeoutException | httpx.NetworkError,
        context: _RetryContext,
    ) -> bool:
        """Handle timeout or network errors with exponential backoff.

        Returns:
            bool: True when caller should retry after applying backoff.
        """
        if not self._has_remaining_attempts(context):
            if isinstance(error, httpx.TimeoutException):
                logger.exception("Request timeout")
                raise LunaTaskTimeoutError from error
            logger.exception("Network error")
            raise LunaTaskNetworkError from error

        message = (
            "Timeout during %s %s; retrying in %.2fs (attempt %d of %d)"
            if isinstance(error, httpx.TimeoutException)
            else "Network error during %s %s; retrying in %.2fs (attempt %d of %d)"
        )
        logger.warning(
            message,
            context.method,
            context.url,
            context.backoff,
            context.attempt + 1,
            context.max_attempts,
        )
        return True

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
        if _HTTP_INTERNAL_SERVER_ERROR <= status_code < _HTTP_MAX_SERVER_ERROR:
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
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
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
        method_upper = method.upper()
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        max_attempts = self._config.http_retries + 1
        backoff = self._config.http_backoff_start_seconds

        for attempt in range(max_attempts):
            await self._rate_limiter.acquire()

            if method_upper in {"POST", "PATCH", "DELETE"}:
                await asyncio.sleep(0.12)

            headers = self._get_auth_headers()

            try:
                http_client = self._get_http_client()

                redacted_headers = self._get_redacted_headers()
                logger.debug(
                    "Making %s request to %s with headers: %s",
                    method_upper,
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

                response.raise_for_status()

            except httpx.HTTPStatusError as error:
                context = _RetryContext(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    backoff=backoff,
                    method=method_upper,
                    url=url,
                )
                should_retry = self._handle_http_status_retry(error, context)
                if should_retry:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                context = _RetryContext(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    backoff=backoff,
                    method=method_upper,
                    url=url,
                )
                should_retry = self._handle_transient_exception(error, context)
                if should_retry:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
            except Exception as error:
                logger.exception("Unexpected error during API request")
                raise LunaTaskAPIError.create_unexpected_error(method, endpoint) from error
            else:
                if response.status_code == _HTTP_NO_CONTENT:
                    logger.debug(
                        "Successful API response: %s (No Content)",
                        response.status_code,
                    )
                    return {}

                result = response.json()
                logger.debug("Successful API response: %s", response.status_code)
                return result

        msg = f"Exhausted retry attempts for {method_upper} {url}"
        logger.error(msg)
        raise LunaTaskAPIError(msg)

    async def get_tasks(self, **params: str | int | None) -> list[TaskResponse]:
        """Retrieve all tasks from the LunaTask API.

        The API returns tasks in wrapped format: {"tasks": [TaskResponse, ...]}.
        This method extracts and returns the task list with guardrails, while
        translating composite filters (e.g., status="open") client-side.

        Args:
            **params: Optional query parameters for pagination/filtering
                     (e.g., limit, offset, status)

        Returns:
            List[TaskResponse]: List of task objects from the API
        """
        query_params, apply_open_filter = self._prepare_list_query_params(params)

        # Make authenticated request to /v1/tasks endpoint
        response_data = (
            await self.make_request("GET", "tasks", params=query_params)
            if query_params
            else await self.make_request("GET", "tasks")
        )

        tasks = self._extract_task_list(response_data)

        # Apply composite open filter client-side if requested
        if apply_open_filter:
            tasks = [t for t in tasks if t.status != "completed"]
        logger.debug("Successfully retrieved %d tasks", len(tasks))
        return tasks

    def _prepare_list_query_params(
        self, params: dict[str, str | int | None] | None
    ) -> tuple[dict[str, str | int] | None, bool]:
        """Sanitize and canonicalize list query params.

        Returns a tuple of (query_params, apply_open_filter) where
        apply_open_filter indicates whether a composite open filter should be
        applied after fetching results.
        """
        if not params:
            return None, False

        # Drop None values
        query_params: dict[str, str | int] = {
            k: v
            for k, v in params.items()
            if v is not None  # type: ignore[misc]
        }

        apply_open_filter = False
        if query_params.get("status") == "open":
            apply_open_filter = True
            del query_params["status"]

        # Guardrails
        if "expand" in query_params:
            raise LunaTaskBadRequestError.expand_not_supported()

        if "limit" in query_params:
            try:
                limit_val = int(query_params["limit"])  # type: ignore[arg-type]
            except Exception:
                limit_val = _MAX_LIST_LIMIT
            if limit_val > _MAX_LIST_LIMIT:
                query_params["limit"] = _MAX_LIST_LIMIT

        # Canonicalize insertion order by lexicographic key
        query_params = {k: query_params[k] for k in sorted(query_params.keys())}
        return query_params, apply_open_filter

    def _extract_task_list(self, response_data: dict[str, Any]) -> list[TaskResponse]:
        """Parse the wrapped tasks list from API response with error handling."""
        task_list: list[dict[str, Any]] = response_data.get("tasks", [])
        try:
            return [TaskResponse(**task_data) for task_data in task_list]
        except KeyError as e:
            logger.exception("Failed to extract tasks from wrapped response format")
            raise LunaTaskAPIError.create_parse_error(
                "tasks", task_count="unknown - missing 'tasks' key"
            ) from e
        except Exception as e:
            logger.exception("Failed to parse task response data")
            task_count = len(task_list) if task_list else "unknown"
            raise LunaTaskAPIError.create_parse_error("tasks", task_count=task_count) from e

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
        # The get task API returns a wrapped response in format {"task": {...}}
        try:
            task = TaskResponse(**response_data["task"])
        except KeyError as e:
            logger.exception("Failed to extract task from wrapped response format")
            raise LunaTaskAPIError.create_parse_error(
                f"tasks/{task_id}", task_id=f"{task_id} - missing 'task' key"
            ) from e
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
        # Use model_dump_json to properly serialize date objects, then parse back to dict
        json_data = json.loads(task_data.model_dump_json(exclude_none=True))

        # Make authenticated request to POST /v1/tasks endpoint
        response_data = await self.make_request("POST", "tasks", data=json_data)

        # Parse response JSON into TaskResponse model instance
        # The create task API returns a wrapped response in format {"task": {...}}
        try:
            task = TaskResponse(**response_data["task"])
        except KeyError as e:
            logger.exception("Failed to extract task from wrapped response format")
            task_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error(
                "tasks", task_name=f"{task_name} - missing 'task' key"
            ) from e
        except Exception as e:
            logger.exception("Failed to parse created task response data")
            task_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error("tasks", task_name=task_name) from e
        else:
            logger.debug("Successfully created task: %s", task.id)
            return task

    async def create_note(self, note_data: NoteCreate) -> NoteResponse | None:
        """Create a new note in the LunaTask API.

        Args:
            note_data: NoteCreate object containing note data to create.

        Returns:
            NoteResponse | None: Created note object from the API, or None when
            the API returns 204 No Content due to an idempotent duplicate.

        Raises:
            LunaTaskValidationError: Validation error (422)
            LunaTaskSubscriptionRequiredError: Subscription required (402)
            LunaTaskAuthenticationError: Invalid bearer token (401)
            LunaTaskRateLimitError: Rate limit exceeded (429)
            LunaTaskServerError: Server error occurred (5xx)
            LunaTaskServiceUnavailableError: Service unavailable (503)
            LunaTaskTimeoutError: Request timeout
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """

        json_data = json.loads(note_data.model_dump_json(exclude_none=True))

        response_data = await self.make_request("POST", "notes", data=json_data)

        if not response_data:
            logger.debug(
                "Note creation returned no content; assuming duplicate for source/source_id"
            )
            return None

        try:
            note_payload = response_data["note"]
            note = NoteResponse(**note_payload)
        except KeyError as error:
            logger.exception("Failed to extract note from wrapped response format")
            note_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error(
                "notes", note_name=f"{note_name} - missing 'note' key"
            ) from error
        except Exception as error:
            logger.exception("Failed to parse created note response data")
            note_name = json_data.get("name", "unknown")
            raise LunaTaskAPIError.create_parse_error("notes", note_name=note_name) from error
        else:
            logger.debug("Successfully created note: %s", note.id)
            return note

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
        # Use model_dump_json to properly serialize date objects, then parse back to dict
        json_data = json.loads(update.model_dump_json(exclude_none=True))

        # Make authenticated request to PATCH /v1/tasks/{task_id} endpoint
        response_data = await self.make_request("PATCH", f"tasks/{task_id}", data=json_data)

        # Parse response JSON into TaskResponse model instance
        # The update task API returns a wrapped response in format {"task": {...}}
        try:
            task = TaskResponse(**response_data["task"])
        except KeyError as e:
            logger.exception("Failed to extract task from wrapped response format")
            raise LunaTaskAPIError.create_parse_error(
                f"tasks/{task_id}", task_id=f"{task_id} - missing 'task' key"
            ) from e
        except Exception as e:
            logger.exception("Failed to parse updated task response data")
            raise LunaTaskAPIError.create_parse_error(f"tasks/{task_id}", task_id=task_id) from e
        else:
            logger.debug("Successfully updated task: %s", task.id)
            return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete an existing task in the LunaTask API.

        Args:
            task_id: The unique identifier for the task to delete

        Returns:
            bool: True if deletion successful

        Raises:
            LunaTaskNotFoundError: Task not found (404)
            LunaTaskAuthenticationError: Invalid bearer token (401)
            LunaTaskRateLimitError: Rate limit exceeded (429)
            LunaTaskServerError: Server error occurred (5xx)
            LunaTaskNetworkError: Network connectivity error
            LunaTaskAPIError: Other API errors
        """
        # Make authenticated request to DELETE /v1/tasks/{task_id} endpoint.
        # Any 2xx response is considered a successful deletion. The underlying
        # make_request() will raise for non-2xx, so reaching here implies success
        # regardless of whether the server returns 204 No Content or a 200 with
        # a JSON body.
        await self.make_request("DELETE", f"tasks/{task_id}")

        logger.debug("Successfully deleted task: %s", task_id)
        return True

    async def test_connectivity(self) -> bool:
        """Test connectivity to the LunaTask API.

        Makes a simple authenticated request to verify that the bearer token
        is valid and the API is accessible.

        Returns:
            bool: True if connectivity test succeeds, False otherwise
        """
        try:
            result = await self.make_request("GET", "ping")
        except LunaTaskAPIError as e:
            logger.warning("LunaTask API connectivity test failed: %s", e)
            return False
        except Exception:
            logger.exception("LunaTask API connectivity test failed with unexpected error")
            return False
        else:
            if result.get("message") == "pong":
                logger.info("LunaTask API connectivity test successful")
                return True
            logger.warning("LunaTask API connectivity test failed: unexpected response")
            return False

    async def track_habit(self, habit_id: str, track_date: date) -> None:
        """Track an activity for a specific habit on a given date.

        Args:
            habit_id: The ID of the habit to track
            track_date: The date when the habit was performed

        Raises:
            LunaTaskAuthenticationError: Authentication failed
            LunaTaskNotFoundError: Habit not found
            LunaTaskValidationError: Invalid date format
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error
            LunaTaskTimeoutError: Request timeout
            LunaTaskNetworkError: Network connectivity error
        """
        await self.make_request(
            "POST", f"habits/{habit_id}/track", data={"performed_on": track_date.isoformat()}
        )
