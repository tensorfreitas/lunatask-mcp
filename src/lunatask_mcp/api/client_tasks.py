"""Tasks mixin for LunaTask API client.

This module provides the TasksClientMixin class containing all task-related
CRUD operations that can be composed with the BaseClient during client
modularization.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, cast

from lunatask_mcp.api.exceptions import LunaTaskAPIError, LunaTaskBadRequestError
from lunatask_mcp.api.models import TaskCreate, TaskResponse, TaskUpdate

if TYPE_CHECKING:
    from lunatask_mcp.api.protocols import BaseClientProtocol

# Configure logger to write to stderr
logger = logging.getLogger(__name__)

# Guardrail constants (imported from base)
_MAX_LIST_LIMIT = 50


class TasksClientMixin:
    """Mixin providing task-related operations for LunaTask API client.

    This mixin contains all task CRUD methods and helpers, designed to be
    composed with BaseClient via multiple inheritance.
    """

    def _get_base_client(self) -> "BaseClientProtocol":
        """Get type-safe access to base client methods."""
        return cast("BaseClientProtocol", self)

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
        base_client = self._get_base_client()
        response_data = (
            await base_client.make_request("GET", "tasks", params=query_params)
            if query_params
            else await base_client.make_request("GET", "tasks")
        )

        tasks = self._extract_task_list(response_data)

        # Apply composite open filter client-side if requested
        if apply_open_filter:
            tasks = [t for t in tasks if t.status != "completed"]
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
        response_data = await self._get_base_client().make_request("GET", f"tasks/{task_id}")

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
        response_data = await self._get_base_client().make_request("POST", "tasks", data=json_data)

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
        response_data = await self._get_base_client().make_request(
            "PATCH", f"tasks/{task_id}", data=json_data
        )

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
        await self._get_base_client().make_request("DELETE", f"tasks/{task_id}")

        logger.debug("Successfully deleted task: %s", task_id)
        return True
