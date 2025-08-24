"""Task management tools for LunaTask MCP integration.

This module provides MCP resources for accessing and managing LunaTask tasks
through the Model Context Protocol, enabling AI models to interact with task data.
"""

import logging
from datetime import datetime
from typing import Any

from fastmcp import Context, FastMCP

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import TaskCreate, TaskResponse, TaskUpdate

# Configure logger to write to stderr
logger = logging.getLogger(__name__)


class TaskTools:
    """Task management tools providing MCP resources for LunaTask integration.

    This class encapsulates task-related MCP resources, enabling AI models
    to retrieve and work with task data from LunaTask through standardized
    MCP resource URIs.
    """

    def __init__(self, mcp_instance: FastMCP, lunatask_client: LunaTaskClient) -> None:
        """Initialize TaskTools with MCP instance and LunaTask client.

        Args:
            mcp_instance: FastMCP server instance for registering resources
            lunatask_client: LunaTask API client for data retrieval
        """
        self.mcp = mcp_instance
        self.lunatask_client = lunatask_client
        self._register_resources()

    def _register_resources(self) -> None:
        """Register all task-related MCP resources and tools with the FastMCP instance."""
        self.mcp.resource("lunatask://tasks")(self.get_tasks_resource)
        self.mcp.resource("lunatask://tasks/{task_id}")(self.get_task_resource)
        self.mcp.tool("create_task")(self.create_task_tool)
        self.mcp.tool("update_task")(self.update_task_tool)
        self.mcp.tool("delete_task")(self.delete_task_tool)

    def _serialize_task_response(self, task: TaskResponse) -> dict[str, Any]:
        """Convert a TaskResponse object to a dictionary for JSON serialization.

        This shared helper method provides consistent serialization of TaskResponse
        objects across all task-related resources, ensuring proper handling of
        optional fields and datetime formatting.

        Args:
            task: TaskResponse object to serialize

        Returns:
            dict[str, Any]: Serialized task data suitable for JSON responses
        """
        return {
            "id": task.id,
            "area_id": task.area_id,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "source": {
                "type": task.source.type,
                "value": task.source.value,
            }
            if task.source
            else None,
            "goal_id": task.goal_id,
            "estimate": task.estimate,
            "motivation": task.motivation,
            "eisenhower": task.eisenhower,
            "previous_status": task.previous_status,
            "progress": task.progress,
            "scheduled_on": task.scheduled_on.isoformat() if task.scheduled_on else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

    async def get_tasks_resource(self, ctx: Context) -> dict[str, Any]:
        """MCP resource providing access to all LunaTask tasks.

        This resource retrieves all tasks from the LunaTask API and presents them
        as a structured JSON resource accessible via the URI 'lunatask://tasks'.

        Args:
            ctx: MCP context providing logging and execution context

        Returns:
            dict[str, Any]: JSON structure containing task data with metadata

        Raises:
            LunaTaskAPIError: If the LunaTask API request fails
        """
        try:
            await ctx.info("Retrieving tasks from LunaTask API")

            # Use the LunaTaskClient to fetch all tasks
            async with self.lunatask_client:
                tasks = await self.lunatask_client.get_tasks()

            # Convert TaskResponse objects to dictionaries for JSON serialization
            task_data = [self._serialize_task_response(task) for task in tasks]

            resource_data = {
                "resource_type": "lunatask_tasks",
                "total_count": len(tasks),
                "tasks": task_data,
                "metadata": {
                    "retrieved_at": ctx.session_id if hasattr(ctx, "session_id") else "unknown",
                    "encrypted_fields_note": (
                        "Task names and note are not included due to E2E encryption"
                    ),
                },
            }

        except LunaTaskAPIError as e:
            # Handle specific LunaTask API errors with structured MCP responses
            if e.__class__.__name__ == "LunaTaskAuthenticationError":
                error_msg = "Failed to retrieve tasks: Invalid or expired LunaTask API credentials"
                await ctx.error(error_msg)
                logger.exception("Authentication error accessing LunaTask API")
            elif e.__class__.__name__ == "LunaTaskRateLimitError":
                error_msg = (
                    "Failed to retrieve tasks: LunaTask API rate limit exceeded - "
                    "please try again later"
                )
                await ctx.error(error_msg)
                logger.warning("Rate limit exceeded for LunaTask API")
            elif e.__class__.__name__ == "LunaTaskServerError":
                error_msg = (
                    f"Failed to retrieve tasks: LunaTask server error ({e.status_code}) "
                    "- please try again"
                )
                await ctx.error(error_msg)
                logger.exception("LunaTask server error: %s", e.status_code)
            elif e.__class__.__name__ == "LunaTaskTimeoutError":
                error_msg = (
                    "Failed to retrieve tasks: Request to LunaTask API timed out - please try again"
                )
                await ctx.error(error_msg)
                logger.warning("LunaTask API request timeout")
            else:
                # Generic LunaTask API error
                error_msg = f"Failed to retrieve tasks from LunaTask API: {e}"
                await ctx.error(error_msg)
                logger.exception("LunaTask API error")
            raise
        except Exception as e:
            error_msg = f"Unexpected error retrieving tasks: {e}"
            logger.exception(error_msg)
            await ctx.error(error_msg)
            raise LunaTaskAPIError(error_msg) from e
        else:
            await ctx.info(f"Successfully retrieved {len(tasks)} tasks from LunaTask")
            return resource_data

    async def get_task_resource(self, ctx: Context, task_id: str) -> dict[str, Any]:
        """MCP resource providing access to a single LunaTask task by ID.

        This resource retrieves a specific task from the LunaTask API and presents it
        as a structured JSON resource accessible via the URI 'lunatask://tasks/{task_id}'.

        Args:
            ctx: MCP context providing logging and execution context
            task_id: The unique identifier for the task to retrieve

        Returns:
            dict[str, Any]: JSON structure containing single task data with metadata

        Raises:
            LunaTaskBadRequestError: If the task_id parameter is empty or invalid
            LunaTaskNotFoundError: If the task with the specified ID is not found
            LunaTaskAPIError: If the LunaTask API request fails
        """
        # Defensive parameter validation for better UX
        if not task_id or not task_id.strip():
            await ctx.error("Empty or invalid task_id parameter provided")
            raise LunaTaskBadRequestError.empty_task_id()

        try:
            await ctx.info(f"Retrieving task {task_id} from LunaTask API")

            # Use the LunaTaskClient to fetch the specific task
            async with self.lunatask_client:
                task = await self.lunatask_client.get_task(task_id)

            # Convert TaskResponse object to dictionary for JSON serialization
            task_data = self._serialize_task_response(task)

            resource_data = {
                "resource_type": "lunatask_task",
                "task_id": task_id,
                "task": task_data,
                "metadata": {
                    "retrieved_at": ctx.session_id if hasattr(ctx, "session_id") else "unknown",
                    "encrypted_fields_note": (
                        "Task names and note are not included due to E2E encryption"
                    ),
                },
            }

        except LunaTaskNotFoundError:
            # Handle specific task not found error with structured MCP response
            error_msg = f"Task {task_id} not found in LunaTask"
            await ctx.error(error_msg)
            logger.warning("Task not found: %s", task_id)
            raise
        except LunaTaskAuthenticationError:
            # Handle authentication errors
            error_msg = (
                f"Failed to retrieve task {task_id}: Invalid or expired LunaTask API credentials"
            )
            await ctx.error(error_msg)
            logger.exception("Authentication error accessing LunaTask API for task %s", task_id)
            raise
        except LunaTaskRateLimitError:
            # Handle rate limit errors
            error_msg = (
                f"Failed to retrieve task {task_id}: LunaTask API rate limit exceeded - "
                "please try again later"
            )
            await ctx.error(error_msg)
            logger.warning("Rate limit exceeded for LunaTask API task %s", task_id)
            raise
        except LunaTaskServerError as e:
            # Handle server errors
            error_msg = (
                f"Failed to retrieve task {task_id}: LunaTask server error ({e.status_code}) "
                "- please try again"
            )
            await ctx.error(error_msg)
            logger.exception("LunaTask server error for task %s: %s", task_id, e.status_code)
            raise
        except LunaTaskTimeoutError:
            # Handle timeout errors
            error_msg = (
                f"Failed to retrieve task {task_id}: Request to LunaTask API timed out - "
                "please try again"
            )
            await ctx.error(error_msg)
            logger.warning("LunaTask API request timeout for task %s", task_id)
            raise
        except LunaTaskAPIError as e:
            # Handle other LunaTask API errors
            error_msg = f"Failed to retrieve task {task_id} from LunaTask API: {e}"
            await ctx.error(error_msg)
            logger.exception("LunaTask API error for task %s", task_id)
            raise
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error retrieving task {task_id}: {e}"
            logger.exception(error_msg)
            await ctx.error(error_msg)
            raise LunaTaskAPIError(error_msg) from e
        else:
            await ctx.info(f"Successfully retrieved task {task_id} from LunaTask")
            return resource_data

    async def create_task_tool(  # noqa: PLR0913, PLR0911
        self,
        ctx: Context,
        name: str,
        note: str | None = None,
        area_id: str | None = None,
        status: str = "later",
        priority: int | None = None,
    ) -> dict[str, Any]:
        """Create a new task in LunaTask.

        This MCP tool creates a new task using the LunaTask API. All task fields
        are supported, with only the name being required.

        Args:
            ctx: MCP context for logging and communication
            name: Task name (required)
            note: Optional task note
            area_id: Optional area ID the task belongs to
            status: Task status (default: "open")
            priority: Optional task priority level

        Returns:
            dict[str, Any]: Response containing task creation result with task_id

        Raises:
            LunaTaskValidationError: When task validation fails (422)
            LunaTaskSubscriptionRequiredError: When subscription required (402)
            LunaTaskAuthenticationError: When authentication fails (401)
            LunaTaskRateLimitError: When rate limit exceeded (429)
            LunaTaskServerError: When server error occurs (5xx)
            LunaTaskAPIError: For other API errors
        """
        await ctx.info(f"Creating new task: {name}")

        try:
            # Create TaskCreate object from parameters
            task_data = TaskCreate(
                name=name,
                note=note,
                area_id=area_id,
                status=status,
                priority=priority,
            )

            # Use LunaTask client to create the task
            async with self.lunatask_client as client:
                created_task = await client.create_task(task_data)

            # Return success response with task ID
            result = {
                "success": True,
                "task_id": created_task.id,
                "message": "Task created successfully",
            }

        except LunaTaskValidationError as e:
            # Handle validation errors (422)
            error_msg = f"Task validation failed: {e}"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Task validation error: %s", e)
            return result

        except LunaTaskSubscriptionRequiredError as e:
            # Handle subscription required errors (402)
            error_msg = f"Subscription required: {e}"
            result = {
                "success": False,
                "error": "subscription_required",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Subscription required for task creation: %s", e)
            return result

        except LunaTaskAuthenticationError as e:
            # Handle authentication errors (401)
            error_msg = f"Authentication failed: {e}"
            result = {
                "success": False,
                "error": "authentication_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Authentication error during task creation: %s", e)
            return result

        except LunaTaskRateLimitError as e:
            # Handle rate limit errors (429)
            error_msg = f"Rate limit exceeded: {e}"
            result = {
                "success": False,
                "error": "rate_limit_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Rate limit exceeded during task creation: %s", e)
            return result

        except LunaTaskServerError as e:
            # Handle server errors (5xx)
            error_msg = f"Server error: {e}"
            result = {
                "success": False,
                "error": "server_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Server error during task creation: %s", e)
            return result

        except LunaTaskAPIError as e:
            # Handle other API errors
            error_msg = f"API error: {e}"
            result = {
                "success": False,
                "error": "api_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("API error during task creation: %s", e)
            return result

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error creating task: {e}"
            result = {
                "success": False,
                "error": "unexpected_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.exception("Unexpected error during task creation")
            return result
        else:
            await ctx.info(f"Successfully created task {created_task.id}")
            return result

    async def update_task_tool(  # noqa: PLR0913, PLR0911, PLR0915, C901
        self,
        ctx: Context,
        id: str,  # noqa: A002
        name: str | None = None,
        note: str | None = None,
        area_id: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing task in LunaTask.

        This MCP tool updates an existing task using the LunaTask API. The task ID
        is required, and any combination of other fields can be updated.

        Args:
            ctx: MCP context for logging and communication
            id: Task ID to update (required)
            name: Updated task name (optional)
            note: Updated task note (optional)
            area_id: Updated area ID the task belongs to (optional)
            status: Updated task status (optional)
            priority: Updated task priority level (optional)
            due_date: Updated due date as ISO 8601 string (optional)

        Returns:
            dict[str, Any]: Response containing task update result with updated task data

        Raises:
            LunaTaskValidationError: When task validation fails (422)
            LunaTaskNotFoundError: When task is not found (404)
            LunaTaskAuthenticationError: When authentication fails (401)
            LunaTaskRateLimitError: When rate limit exceeded (429)
            LunaTaskServerError: When server error occurs (5xx)
            LunaTaskAPIError: For other API errors
        """
        # Validate required task ID parameter
        if not id or not id.strip():
            error_msg = "Task ID cannot be empty"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Empty task_id provided for update")
            return result

        # Validate that at least one field is provided for update
        update_fields = [name, note, area_id, status, priority, due_date]
        if all(field is None for field in update_fields):
            error_msg = "At least one field must be provided for update"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("No fields provided for task update: %s", id)
            return result

        # Parse and validate due_date if provided
        parsed_due_date = None
        if due_date is not None:
            try:
                parsed_due_date = datetime.fromisoformat(due_date)
            except (ValueError, TypeError) as e:
                error_msg = f"Invalid due_date format. Expected ISO 8601 string: {e}"
                result = {
                    "success": False,
                    "error": "validation_error",
                    "message": error_msg,
                }
                await ctx.error(error_msg)
                logger.warning("Invalid due_date format for task %s: %s", id, due_date)
                return result

        await ctx.info(f"Updating task {id}")

        try:
            # Create TaskUpdate object from provided parameters
            task_update = TaskUpdate(
                name=name,
                note=note,
                area_id=area_id,
                status=status,
                priority=priority,
                due_date=parsed_due_date,
            )

            # Use LunaTask client to update the task
            async with self.lunatask_client as client:
                updated_task = await client.update_task(id, task_update)

            # Return success response with updated task data
            result = {
                "success": True,
                "task_id": id,
                "message": "Task updated successfully",
                "task": self._serialize_task_response(updated_task),
            }

        except LunaTaskNotFoundError as e:
            # Handle task not found errors (404)
            error_msg = f"Task not found: {e}"
            result = {
                "success": False,
                "error": "not_found_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Task not found during update: %s", id)
            return result

        except LunaTaskValidationError as e:
            # Handle validation errors (422)
            error_msg = f"Task validation failed: {e}"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Task validation error during update: %s", e)
            return result

        except LunaTaskAuthenticationError as e:
            # Handle authentication errors (401)
            error_msg = f"Authentication failed: {e}"
            result = {
                "success": False,
                "error": "authentication_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Authentication error during task update: %s", e)
            return result

        except LunaTaskRateLimitError as e:
            # Handle rate limit errors (429)
            error_msg = f"Rate limit exceeded: {e}"
            result = {
                "success": False,
                "error": "rate_limit_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Rate limit exceeded during task update: %s", e)
            return result

        except LunaTaskServerError as e:
            # Handle server errors (5xx)
            error_msg = f"Server error: {e}"
            result = {
                "success": False,
                "error": "server_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Server error during task update: %s", e)
            return result

        except LunaTaskAPIError as e:
            # Handle other API errors
            error_msg = f"API error: {e}"
            result = {
                "success": False,
                "error": "api_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("API error during task update: %s", e)
            return result

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error updating task: {e}"
            result = {
                "success": False,
                "error": "unexpected_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.exception("Unexpected error during task update")
            return result
        else:
            await ctx.info(f"Successfully updated task {id}")
            return result

    async def delete_task_tool(  # noqa: PLR0911, PLR0915, C901
        self,
        ctx: Context,
        id: str,  # noqa: A002
    ) -> dict[str, Any]:
        """Delete an existing task in LunaTask.

        This MCP tool deletes an existing task using the LunaTask API. The task ID
        is required and will be permanently deleted.

        Args:
            ctx: MCP context for logging and communication
            id: Task ID to delete (required)

        Returns:
            dict[str, Any]: Response containing task deletion result with confirmation

        Raises:
            LunaTaskNotFoundError: When task is not found (404)
            LunaTaskAuthenticationError: When authentication fails (401)
            LunaTaskRateLimitError: When rate limit exceeded (429)
            LunaTaskServerError: When server error occurs (5xx)
            LunaTaskTimeoutError: When request times out
            LunaTaskAPIError: For other API errors
        """
        # Validate required task ID parameter
        if not id or not id.strip():
            error_msg = "Task ID cannot be empty"
            result = {
                "success": False,
                "error": "validation_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Empty task_id provided for deletion")
            return result

        await ctx.info(f"Deleting task {id}")

        try:
            # Use LunaTask client to delete the task
            async with self.lunatask_client as client:
                deletion_success = await client.delete_task(id)

            if deletion_success:
                # Return success response with task ID for confirmation
                result = {
                    "success": True,
                    "task_id": id,
                    "message": "Task deleted successfully",
                }
            else:
                # This shouldn't happen with current implementation, but handle gracefully
                result = {
                    "success": False,
                    "error": "unexpected_error",
                    "message": "Task deletion returned unexpected result",
                }
                await ctx.error("Task deletion returned unexpected result")
                logger.warning("Unexpected deletion result for task %s", id)
                return result

        except LunaTaskNotFoundError as e:
            # Handle task not found errors (404)
            error_msg = f"Task not found: {e}"
            result = {
                "success": False,
                "error": "not_found_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Task not found during deletion: %s", id)
            return result

        except LunaTaskAuthenticationError as e:
            # Handle authentication errors (401)
            error_msg = f"Authentication failed: {e}"
            result = {
                "success": False,
                "error": "authentication_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Authentication error during task deletion: %s", e)
            return result

        except LunaTaskRateLimitError as e:
            # Handle rate limit errors (429)
            error_msg = f"Rate limit exceeded: {e}"
            result = {
                "success": False,
                "error": "rate_limit_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Rate limit exceeded during task deletion: %s", e)
            return result

        except LunaTaskTimeoutError as e:
            # Handle timeout errors
            error_msg = f"Request timeout: {e}"
            result = {
                "success": False,
                "error": "timeout_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Timeout error during task deletion: %s", e)
            return result

        except LunaTaskServerError as e:
            # Handle server errors (5xx)
            error_msg = f"Server error: {e}"
            result = {
                "success": False,
                "error": "server_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("Server error during task deletion: %s", e)
            return result

        except LunaTaskAPIError as e:
            # Handle other API errors
            error_msg = f"API error: {e}"
            result = {
                "success": False,
                "error": "api_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.warning("API error during task deletion: %s", e)
            return result

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error deleting task: {e}"
            result = {
                "success": False,
                "error": "unexpected_error",
                "message": error_msg,
            }
            await ctx.error(error_msg)
            logger.exception("Unexpected error during task deletion")
            return result
        else:
            await ctx.info(f"Successfully deleted task {id}")
            return result
