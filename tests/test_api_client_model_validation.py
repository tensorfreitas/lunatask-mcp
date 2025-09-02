"""Model validation and default behavior tests for tasks."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lunatask_mcp.api.models import (
    MAX_EISENHOWER,
    MAX_PRIORITY,
    MIN_EISENHOWER,
    MIN_PRIORITY,
    TaskCreate,
    TaskMotivation,
    TaskStatus,
    TaskUpdate,
)
from tests.factories import create_task_response


class TestTaskModelValidationAndDefaults:
    """Test task model validation and defaults.

    These tests follow TDD methodology and must fail first to drive implementation.
    Testing AC: 1, 2, 3 - Request-side validation, field addition, response permissiveness.
    """

    def test_task_create_defaults_on_creation(self) -> None:
        """Test TaskCreate applies correct defaults on creation (AC: 1)."""
        # Test defaults: status="later", priority=0, motivation="unknown"
        task = TaskCreate(name="Test Task")

        assert task.status == "later"
        assert task.priority == 0
        assert task.motivation == "unknown"

    def test_task_create_status_enum_validation(self) -> None:
        """Test TaskCreate validates status enum values (AC: 1)."""
        # Valid values should pass
        valid_statuses: list[TaskStatus] = ["later", "next", "started", "waiting", "completed"]
        for status in valid_statuses:
            task = TaskCreate(name="Test Task", status=status)
            assert task.status == status

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskCreate(name="Test Task", status="invalid_status")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_create_motivation_enum_validation(self) -> None:
        """Test TaskCreate validates motivation enum values (AC: 1, 2)."""
        # Valid values should pass
        valid_motivations: list[TaskMotivation] = ["must", "should", "want", "unknown"]
        for motivation in valid_motivations:
            task = TaskCreate(name="Test Task", motivation=motivation)
            assert task.motivation == motivation

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskCreate(name="Test Task", motivation="invalid_motivation")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_create_priority_bounds_validation(self) -> None:
        """Test TaskCreate validates priority bounds (AC: 1)."""
        # Valid boundary values should pass
        valid_priorities = [MIN_PRIORITY, -1, 0, 1, MAX_PRIORITY]
        for priority in valid_priorities:
            task = TaskCreate(name="Test Task", priority=priority)
            assert task.priority == priority

        # Invalid values should raise ValidationError
        with pytest.raises(ValueError, match=f"Priority must be between {MIN_PRIORITY}"):
            TaskCreate(name="Test Task", priority=MIN_PRIORITY - 1)
        with pytest.raises(ValueError, match=f"Priority must be between {MIN_PRIORITY}"):
            TaskCreate(name="Test Task", priority=MAX_PRIORITY + 1)

    def test_task_create_eisenhower_bounds_validation(self) -> None:
        """Test TaskCreate validates eisenhower bounds (AC: 1, 2)."""
        # Valid boundary values should pass
        valid_eisenhower = [MIN_EISENHOWER, 1, 2, 3, MAX_EISENHOWER]
        for eisenhower in valid_eisenhower:
            task = TaskCreate(name="Test Task", eisenhower=eisenhower)
            assert task.eisenhower == eisenhower

        # Invalid values should raise ValidationError
        with pytest.raises(ValueError, match=f"Eisenhower must be between {MIN_EISENHOWER}"):
            TaskCreate(name="Test Task", eisenhower=MIN_EISENHOWER - 1)
        with pytest.raises(ValueError, match=f"Eisenhower must be between {MIN_EISENHOWER}"):
            TaskCreate(name="Test Task", eisenhower=MAX_EISENHOWER + 1)

    def test_task_create_optional_fields_motivation_eisenhower(self) -> None:
        """Test TaskCreate accepts optional motivation and eisenhower fields (AC: 2)."""
        # Should accept both fields as optional
        task = TaskCreate(name="Test Task", motivation="must", eisenhower=MAX_EISENHOWER)
        assert task.motivation == "must"
        assert task.eisenhower == MAX_EISENHOWER

        # Should work without these fields
        task_minimal = TaskCreate(name="Test Task")
        assert task_minimal.motivation == "unknown"  # default
        assert task_minimal.eisenhower is None  # no default

    def test_task_update_status_enum_validation(self) -> None:
        """Test TaskUpdate validates status enum values (AC: 1)."""
        # Valid values should pass
        valid_statuses: list[TaskStatus] = ["later", "next", "started", "waiting", "completed"]
        for status in valid_statuses:
            task = TaskUpdate(status=status)
            assert task.status == status

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskUpdate(status="invalid_status")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_update_motivation_enum_validation(self) -> None:
        """Test TaskUpdate validates motivation enum values (AC: 1, 2)."""
        # Valid values should pass
        valid_motivations: list[TaskMotivation] = ["must", "should", "want", "unknown"]
        for motivation in valid_motivations:
            task = TaskUpdate(motivation=motivation)
            assert task.motivation == motivation

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskUpdate(motivation="invalid_motivation")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_update_priority_bounds_validation(self) -> None:
        """Test TaskUpdate validates priority bounds (AC: 1)."""
        # Valid boundary values should pass
        valid_priorities = [MIN_PRIORITY, -1, 0, 1, MAX_PRIORITY]
        for priority in valid_priorities:
            task = TaskUpdate(priority=priority)
            assert task.priority == priority

        # Invalid values should raise ValidationError
        with pytest.raises(ValueError, match=f"Priority must be between {MIN_PRIORITY}"):
            TaskUpdate(priority=MIN_PRIORITY - 1)
        with pytest.raises(ValueError, match=f"Priority must be between {MIN_PRIORITY}"):
            TaskUpdate(priority=MAX_PRIORITY + 1)

    def test_task_update_eisenhower_bounds_validation(self) -> None:
        """Test TaskUpdate validates eisenhower bounds (AC: 1, 2)."""
        # Valid boundary values should pass
        valid_eisenhower = [MIN_EISENHOWER, 1, 2, 3, MAX_EISENHOWER]
        for eisenhower in valid_eisenhower:
            task = TaskUpdate(eisenhower=eisenhower)
            assert task.eisenhower == eisenhower

        # Invalid values should raise ValidationError
        with pytest.raises(ValueError, match=f"Eisenhower must be between {MIN_EISENHOWER}"):
            TaskUpdate(eisenhower=MIN_EISENHOWER - 1)
        with pytest.raises(ValueError, match=f"Eisenhower must be between {MIN_EISENHOWER}"):
            TaskUpdate(eisenhower=MAX_EISENHOWER + 1)

    def test_task_update_optional_fields_motivation_eisenhower(self) -> None:
        """Test TaskUpdate accepts optional motivation and eisenhower fields (AC: 2)."""
        # Should accept both fields as optional
        task = TaskUpdate(motivation="should", eisenhower=MAX_EISENHOWER - 1)
        assert task.motivation == "should"
        assert task.eisenhower == MAX_EISENHOWER - 1

        # Should work without these fields (all None)
        task_empty = TaskUpdate()
        assert task_empty.motivation is None
        assert task_empty.eisenhower is None

    def test_task_response_permissive_handling(self) -> None:
        """Test TaskResponse remains permissive with upstream values (AC: 3)."""
        # TaskResponse should accept upstream values like "open" without normalization
        # This should NOT raise validation error - response model is permissive
        try:
            task_response = create_task_response(
                task_id="test-task",
                status="open",  # upstream value not in request enum
                created_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
                motivation="high",  # upstream value not in request enum
                eisenhower=MAX_EISENHOWER + 6,  # upstream value outside request bounds
            )
            # Should parse successfully without normalization
            assert task_response.status == "open"
            assert task_response.motivation == "high"
            assert task_response.eisenhower == MAX_EISENHOWER + 6
        except ValidationError:
            pytest.fail("TaskResponse should be permissive and not reject upstream values")
