"""Characterization tests for LunaTaskClient core behaviors."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import logging
import sys
from datetime import date

import httpx
import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import NoteCreate
from lunatask_mcp.config import ServerConfig
from tests.factories import create_task_response
from tests.test_api_client_common import (
    CUSTOM_API_URL,
    DEFAULT_API_URL,
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND,
    HTTP_PAYMENT_REQUIRED,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_TIMEOUT,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_UNAUTHORIZED,
    HTTP_UNPROCESSABLE_ENTITY,
    SECRET_TOKEN,
)

# Test constants
EXPECTED_RETRY_COUNT = 2
EXPECTED_MAX_LIMIT = 50


def test_lunatask_client_import_path_stable() -> None:
    """Ensure LunaTaskClient remains importable from its public path."""

    module = __import__("lunatask_mcp.api.client", fromlist=["LunaTaskClient"])

    assert module.LunaTaskClient is LunaTaskClient
    assert LunaTaskClient.__module__ == "lunatask_mcp.api.client"


def test_client_str_and_repr_redact_bearer_token() -> None:
    """Ensure bearer tokens never appear in __str__ or __repr__."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=DEFAULT_API_URL,
    )
    client = LunaTaskClient(config)

    for representation in (str(client), repr(client)):
        assert SECRET_TOKEN not in representation
        assert "***redacted***" in representation


@pytest.mark.asyncio
async def test_make_request_logs_redact_token(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure request logs redact the bearer token."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=CUSTOM_API_URL,
    )
    client = LunaTaskClient(config)

    caplog.set_level(logging.DEBUG, logger="lunatask_mcp.api.client_base")

    response_mock = mocker.Mock()
    response_mock.status_code = 200
    response_mock.raise_for_status.return_value = None
    response_mock.json.return_value = {"ok": True}

    http_client_mock = mocker.Mock()
    http_client_mock.request = mocker.AsyncMock(return_value=response_mock)

    mocker.patch.object(client, "_get_http_client", return_value=http_client_mock)
    rate_limiter_acquire = mocker.AsyncMock()
    mocker.patch.object(client._rate_limiter, "acquire", rate_limiter_acquire)

    await client.make_request("GET", "tasks")

    messages = " \n".join(record.getMessage() for record in caplog.records)

    assert SECRET_TOKEN not in messages
    assert "***redacted***" in messages


@pytest.mark.asyncio
async def test_make_request_logs_only_to_stderr(
    mocker: MockerFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    """Ensure logging output writes to stderr and not stdout."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=DEFAULT_API_URL,
    )
    client = LunaTaskClient(config)

    logging.basicConfig(level=logging.ERROR, stream=sys.stderr, force=True)

    rate_limiter_acquire = mocker.AsyncMock()
    mocker.patch.object(client._rate_limiter, "acquire", rate_limiter_acquire)

    request_url = f"{client._base_url}/tasks"
    error_response = httpx.Response(
        status_code=HTTP_BAD_REQUEST,
        request=httpx.Request("GET", request_url),
    )

    http_client_mock = mocker.Mock()
    http_client_mock.request = mocker.AsyncMock(return_value=error_response)

    mocker.patch.object(client, "_get_http_client", return_value=http_client_mock)

    with pytest.raises(LunaTaskBadRequestError):
        await client.make_request("GET", "tasks")

    captured = capfd.readouterr()

    assert "Bad request" in captured.err
    assert captured.out == ""


@pytest.mark.asyncio
async def test_make_request_retries_and_backoff_on_server_error(
    mocker: MockerFixture,
) -> None:
    """Ensure 5xx errors trigger retries with exponential backoff."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=DEFAULT_API_URL,
    )
    client = LunaTaskClient(config)

    rate_limiter_acquire = mocker.AsyncMock()
    mocker.patch.object(client._rate_limiter, "acquire", rate_limiter_acquire)

    sleep_mock = mocker.patch(
        "lunatask_mcp.api.client_base.asyncio.sleep",
        new=mocker.AsyncMock(),
    )

    request = httpx.Request("GET", f"{client._base_url}/tasks")
    responses = [
        httpx.Response(status_code=500, request=request),
        httpx.Response(status_code=200, json={"tasks": []}, request=request),
    ]

    http_client_mock = mocker.Mock()
    http_client_mock.request = mocker.AsyncMock(side_effect=responses)

    mocker.patch.object(client, "_get_http_client", return_value=http_client_mock)

    result = await client.make_request("GET", "tasks")

    assert result == {"tasks": []}
    assert http_client_mock.request.await_count == EXPECTED_RETRY_COUNT
    assert rate_limiter_acquire.await_count == EXPECTED_RETRY_COUNT
    sleep_mock.assert_awaited()
    first_sleep = sleep_mock.await_args_list[0][0][0]
    assert first_sleep == pytest.approx(config.http_backoff_start_seconds)  # type: ignore[misc]


@pytest.mark.asyncio
async def test_make_request_retries_on_timeout(mocker: MockerFixture) -> None:
    """Ensure timeout exceptions trigger retries with backoff."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=DEFAULT_API_URL,
    )
    client = LunaTaskClient(config)

    rate_limiter_acquire = mocker.AsyncMock()
    mocker.patch.object(client._rate_limiter, "acquire", rate_limiter_acquire)

    sleep_mock = mocker.patch(
        "lunatask_mcp.api.client_base.asyncio.sleep",
        new=mocker.AsyncMock(),
    )

    request = httpx.Request("GET", f"{client._base_url}/tasks")
    success_response = httpx.Response(status_code=200, json={"tasks": []}, request=request)

    http_client_mock = mocker.Mock()
    http_client_mock.request = mocker.AsyncMock(
        side_effect=[httpx.TimeoutException("timeout"), success_response]
    )

    mocker.patch.object(client, "_get_http_client", return_value=http_client_mock)

    result = await client.make_request("GET", "tasks")

    assert result == {"tasks": []}
    assert http_client_mock.request.await_count == EXPECTED_RETRY_COUNT
    assert rate_limiter_acquire.await_count == EXPECTED_RETRY_COUNT
    sleep_mock.assert_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (HTTP_BAD_REQUEST, LunaTaskBadRequestError),
        (HTTP_UNAUTHORIZED, LunaTaskAuthenticationError),
        (HTTP_PAYMENT_REQUIRED, LunaTaskSubscriptionRequiredError),
        (HTTP_NOT_FOUND, LunaTaskNotFoundError),
        (HTTP_UNPROCESSABLE_ENTITY, LunaTaskValidationError),
        (HTTP_TOO_MANY_REQUESTS, LunaTaskRateLimitError),
        (HTTP_SERVICE_UNAVAILABLE, LunaTaskServiceUnavailableError),
        (HTTP_TIMEOUT, LunaTaskTimeoutError),
    ],
)
async def test_make_request_maps_http_errors(
    status_code: int,
    expected_exception: type[Exception],
    mocker: MockerFixture,
) -> None:
    """Ensure HTTP errors raise the correct LunaTask exceptions."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=DEFAULT_API_URL,
    )
    client = LunaTaskClient(config)

    rate_limiter_acquire = mocker.AsyncMock()
    mocker.patch.object(client._rate_limiter, "acquire", rate_limiter_acquire)

    sleep_mock = mocker.patch(
        "lunatask_mcp.api.client_base.asyncio.sleep",
        new=mocker.AsyncMock(),
    )

    request = httpx.Request("GET", f"{client._base_url}/tasks")

    retryable_statuses = {HTTP_SERVICE_UNAVAILABLE, HTTP_TIMEOUT}
    attempts = config.http_retries + 1 if status_code in retryable_statuses else 1
    responses = [httpx.Response(status_code=status_code, request=request) for _ in range(attempts)]

    http_client_mock = mocker.Mock()
    http_client_mock.request = mocker.AsyncMock(side_effect=responses)

    mocker.patch.object(client, "_get_http_client", return_value=http_client_mock)

    with pytest.raises(expected_exception) as exc_info:
        await client.make_request("GET", "tasks")

    assert http_client_mock.request.await_count == attempts
    assert rate_limiter_acquire.await_count == attempts

    if status_code in retryable_statuses:
        sleep_mock.assert_awaited()

    if status_code == HTTP_TIMEOUT:
        assert isinstance(exc_info.value, LunaTaskTimeoutError)
        assert exc_info.value.status_code == HTTP_TIMEOUT


@pytest.mark.asyncio
async def test_get_tasks_strips_open_status_and_filters(
    mocker: MockerFixture,
) -> None:
    """Ensure get_tasks removes status=open param and filters completed tasks."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=DEFAULT_API_URL,
    )
    client = LunaTaskClient(config)

    open_task = create_task_response(task_id="task-open", status="later")
    done_task = create_task_response(task_id="task-done", status="completed")

    response_payload = {
        "tasks": [open_task.model_dump(), done_task.model_dump()],
    }

    mock_make_request = mocker.patch.object(
        client,
        "make_request",
        new_callable=mocker.AsyncMock,
        return_value=response_payload,
    )

    tasks = await client.get_tasks(status="open", limit=75)

    assert [task.id for task in tasks] == ["task-open"]

    assert mock_make_request.await_args is not None
    call_kwargs = mock_make_request.await_args.kwargs
    assert call_kwargs["params"]["limit"] == EXPECTED_MAX_LIMIT
    assert "status" not in call_kwargs["params"]


@pytest.mark.asyncio
async def test_make_request_returns_empty_dict_for_no_content(
    mocker: MockerFixture,
) -> None:
    """Ensure make_request returns an empty dict for HTTP 204 responses."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=DEFAULT_API_URL,
    )
    client = LunaTaskClient(config)

    rate_limiter_acquire = mocker.AsyncMock()
    mocker.patch.object(client._rate_limiter, "acquire", rate_limiter_acquire)

    response_mock = mocker.Mock()
    response_mock.status_code = 204
    response_mock.raise_for_status.return_value = None
    response_mock.json.side_effect = AssertionError("json should not be called on 204")

    http_client_mock = mocker.Mock()
    http_client_mock.request = mocker.AsyncMock(return_value=response_mock)

    mocker.patch.object(client, "_get_http_client", return_value=http_client_mock)

    result = await client.make_request("POST", "notes")

    assert result == {}
    response_mock.json.assert_not_called()
    assert rate_limiter_acquire.await_count == 1


@pytest.mark.asyncio
async def test_create_note_returns_none_for_no_content(mocker: MockerFixture) -> None:
    """Ensure create_note returns None when API responds with no content."""

    config = ServerConfig(
        lunatask_bearer_token=SECRET_TOKEN,
        lunatask_base_url=CUSTOM_API_URL,
    )
    client = LunaTaskClient(config)

    mock_make_request = mocker.patch.object(
        client,
        "make_request",
        new_callable=mocker.AsyncMock,
        return_value={},
    )

    note = NoteCreate(
        notebook_id="notebook-123",
        name="Sync meeting notes",
        date_on=date(2025, 9, 22),
        source="asana",
        source_id="task-123",
    )

    result = await client.create_note(note)

    assert result is None
    mock_make_request.assert_awaited_once()
