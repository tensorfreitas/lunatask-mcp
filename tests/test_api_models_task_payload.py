"""Unit tests for `TaskPayload` base model.

These tests validate that shared constraints and enum serialization are centralized
in the base class without changing behavior of existing request models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lunatask_mcp.api.models import (
    MAX_EISENHOWER,
    MAX_PRIORITY,
    MIN_EISENHOWER,
    MIN_PRIORITY,
    TaskMotivation,
    TaskPayload,
    TaskStatus,
)


def test_task_payload_optional_fields_default_none() -> None:
    # area_id is required, so we need to provide it
    payload = TaskPayload()

    # Optional relational/content fields
    assert payload.goal_id is None

    # Fields with defaults
    assert payload.status == TaskStatus.LATER  # Has default
    assert payload.priority == 0  # Has default

    # Optional prioritization/scheduling fields (default None)
    assert payload.estimate is None
    assert payload.progress is None
    assert payload.motivation is None
    assert payload.eisenhower is None
    assert payload.scheduled_on is None
    assert payload.source is None
    assert payload.name is None
    assert payload.note is None


def test_task_payload_serializes_enum_values() -> None:
    # area_id is required, so we need to provide it
    payload = TaskPayload(status=TaskStatus.NEXT, motivation=TaskMotivation.SHOULD)
    dumped = payload.model_dump()

    # Pydantic should serialize enums to their string values
    assert dumped["status"] == "next"
    assert dumped["motivation"] == "should"


@pytest.mark.parametrize(
    "priority",
    [MIN_PRIORITY - 1, MAX_PRIORITY + 1],
)
def test_task_payload_priority_bounds(priority: int) -> None:
    with pytest.raises(ValidationError):
        TaskPayload(priority=priority)


@pytest.mark.parametrize(
    "eisenhower",
    [MIN_EISENHOWER - 1, MAX_EISENHOWER + 1],
)
def test_task_payload_eisenhower_bounds(eisenhower: int) -> None:
    with pytest.raises(ValidationError):
        TaskPayload(eisenhower=eisenhower)


def test_task_payload_status_rejects_invalid_string() -> None:
    with pytest.raises(ValidationError):
        TaskPayload(status="not-a-valid-status")  # type: ignore[arg-type]
