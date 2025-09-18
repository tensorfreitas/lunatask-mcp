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
    TaskResponse,
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
        # Test defaults: status="later", priority=0, motivation=None
        task = TaskCreate(name="Test Task", area_id="area-xyz")

        assert task.area_id == "area-xyz"
        assert task.name == "Test Task"
        assert task.motivation is None
        assert task.priority is None

    def test_task_create_status_enum_validation(self) -> None:
        """Test TaskCreate validates status enum values (AC: 1)."""
        # Valid values should pass
        valid_statuses = [
            TaskStatus.LATER,
            TaskStatus.NEXT,
            TaskStatus.STARTED,
            TaskStatus.WAITING,
            TaskStatus.COMPLETED,
        ]
        for status in valid_statuses:
            task = TaskCreate(name="Test Task", area_id="area-xyz", status=status)
            assert task.status == status

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskCreate(name="Test Task", area_id="area-xyz", status="invalid_status")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_create_motivation_enum_validation(self) -> None:
        """Test TaskCreate validates motivation enum values (AC: 1, 2)."""
        # Valid values should pass
        valid_motivations = [
            TaskMotivation.MUST,
            TaskMotivation.SHOULD,
            TaskMotivation.WANT,
            TaskMotivation.UNKNOWN,
        ]
        for motivation in valid_motivations:
            task = TaskCreate(name="Test Task", area_id="area-xyz", motivation=motivation)
            assert task.motivation == motivation

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskCreate(name="Test Task", area_id="area-xyz", motivation="invalid_motivation")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_create_priority_bounds_validation(self) -> None:
        """Test TaskCreate validates priority bounds (AC: 1)."""
        # Valid boundary values should pass
        valid_priorities = [MIN_PRIORITY, -1, 0, 1, MAX_PRIORITY]
        for priority in valid_priorities:
            task = TaskCreate(name="Test Task", area_id="area-xyz", priority=priority)
            assert task.priority == priority

        # Invalid values should raise Pydantic ValidationError with standard constraint messages
        with pytest.raises(ValidationError, match="greater than or equal"):
            TaskCreate(name="Test Task", area_id="area-xyz", priority=MIN_PRIORITY - 1)
        with pytest.raises(ValidationError, match="less than or equal"):
            TaskCreate(name="Test Task", area_id="area-xyz", priority=MAX_PRIORITY + 1)

    def test_task_create_eisenhower_bounds_validation(self) -> None:
        """Test TaskCreate validates eisenhower bounds (AC: 1, 2)."""
        # Valid boundary values should pass
        valid_eisenhower = [MIN_EISENHOWER, 1, 2, 3, MAX_EISENHOWER]
        for eisenhower in valid_eisenhower:
            task = TaskCreate(name="Test Task", area_id="area-xyz", eisenhower=eisenhower)
            assert task.eisenhower == eisenhower

        # Invalid values should raise Pydantic ValidationError with standard constraint messages
        with pytest.raises(ValidationError, match="greater than or equal"):
            TaskCreate(name="Test Task", area_id="area-xyz", eisenhower=MIN_EISENHOWER - 1)
        with pytest.raises(ValidationError, match="less than or equal"):
            TaskCreate(name="Test Task", area_id="area-xyz", eisenhower=MAX_EISENHOWER + 1)

    def test_task_create_optional_fields_motivation_eisenhower(self) -> None:
        """Test TaskCreate accepts optional motivation and eisenhower fields (AC: 2)."""
        # Should accept both fields
        task = TaskCreate(
            name="Test Task",
            area_id="area-xyz",
            motivation=TaskMotivation.MUST,
            eisenhower=MAX_EISENHOWER,
        )
        assert task.motivation == TaskMotivation.MUST
        assert task.eisenhower == MAX_EISENHOWER

        # Should work without these fields
        task_minimal = TaskCreate(name="Test Task", area_id="area-xyz")
        assert task_minimal.motivation is None  # default is None
        assert task_minimal.eisenhower is None  # no default

    def test_task_create_accepts_source_attributes(self) -> None:
        """TaskCreate should accept optional source and source_id fields."""
        task = TaskCreate(
            name="Source Task",
            area_id="area-xyz",
            source="github",
            source_id="issue-123",
        )

        assert task.source == "github"
        assert task.source_id == "issue-123"

        task_no_source = TaskCreate(name="No Source Task", area_id="area-xyz")
        assert task_no_source.source is None
        assert task_no_source.source_id is None

    def test_task_update_status_enum_validation(self) -> None:
        """Test TaskUpdate validates status enum values (AC: 1)."""
        # Valid values should pass
        valid_statuses = [
            TaskStatus.LATER,
            TaskStatus.NEXT,
            TaskStatus.STARTED,
            TaskStatus.WAITING,
            TaskStatus.COMPLETED,
        ]
        for status in valid_statuses:
            task = TaskUpdate(id="task-1", area_id="area-xyz", status=status)
            assert task.status == status

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskUpdate(id="task-1", area_id="area-xyz", status="invalid_status")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_update_motivation_enum_validation(self) -> None:
        """Test TaskUpdate validates motivation enum values (AC: 1, 2)."""
        # Valid values should pass
        valid_motivations = [
            TaskMotivation.MUST,
            TaskMotivation.SHOULD,
            TaskMotivation.WANT,
            TaskMotivation.UNKNOWN,
        ]
        for motivation in valid_motivations:
            task = TaskUpdate(id="task-1", area_id="area-xyz", motivation=motivation)
            assert task.motivation == motivation

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be"):
            TaskUpdate(id="task-1", area_id="area-xyz", motivation="invalid_motivation")  # type: ignore[arg-type] # Intentionally invalid for error testing

    def test_task_update_priority_bounds_validation(self) -> None:
        """Test TaskUpdate validates priority bounds (AC: 1)."""
        # Valid boundary values should pass
        valid_priorities = [MIN_PRIORITY, -1, 0, 1, MAX_PRIORITY]
        for priority in valid_priorities:
            task = TaskUpdate(id="task-1", area_id="area-xyz", priority=priority)
            assert task.priority == priority

        # Invalid values should raise Pydantic ValidationError with standard constraint messages
        with pytest.raises(ValidationError, match="greater than or equal"):
            TaskUpdate(id="task-1", area_id="area-xyz", priority=MIN_PRIORITY - 1)
        with pytest.raises(ValidationError, match="less than or equal"):
            TaskUpdate(id="task-1", area_id="area-xyz", priority=MAX_PRIORITY + 1)

    def test_task_update_eisenhower_bounds_validation(self) -> None:
        """Test TaskUpdate validates eisenhower bounds (AC: 1, 2)."""
        # Valid boundary values should pass
        valid_eisenhower = [MIN_EISENHOWER, 1, 2, 3, MAX_EISENHOWER]
        for eisenhower in valid_eisenhower:
            task = TaskUpdate(id="task-1", area_id="area-xyz", eisenhower=eisenhower)
            assert task.eisenhower == eisenhower

        # Invalid values should raise Pydantic ValidationError with standard constraint messages
        with pytest.raises(ValidationError, match="greater than or equal"):
            TaskUpdate(id="task-1", area_id="area-xyz", eisenhower=MIN_EISENHOWER - 1)
        with pytest.raises(ValidationError, match="less than or equal"):
            TaskUpdate(id="task-1", area_id="area-xyz", eisenhower=MAX_EISENHOWER + 1)

    def test_task_update_optional_fields_motivation_eisenhower(self) -> None:
        """Test TaskUpdate accepts optional motivation and eisenhower fields (AC: 2)."""
        # Should accept both fields
        task = TaskUpdate(
            id="task-1",
            area_id="area-xyz",
            motivation=TaskMotivation.SHOULD,
            eisenhower=MAX_EISENHOWER - 1,
        )
        assert task.motivation == TaskMotivation.SHOULD
        assert task.eisenhower == MAX_EISENHOWER - 1

        # Should work without these fields (all None)
        task_empty = TaskUpdate(id="task-1", area_id="area-xyz")
        assert task_empty.motivation is None
        assert task_empty.eisenhower is None

    def test_task_update_rejects_source_attributes(self) -> None:
        """TaskUpdate should reject unsupported source metadata fields."""
        with pytest.raises(ValidationError):
            TaskUpdate(
                id="task-1",
                area_id="area-xyz",
                source="github",  # type: ignore[arg-type] # Intentional invalid field for validation
                source_id="issue-123",  # type: ignore[arg-type] # Intentional invalid field for validation
            )

    def test_task_response_strict_handling_invalid_upstream(self) -> None:
        """TaskResponse should reject upstream values outside enum/range (strict)."""
        with pytest.raises(ValidationError):
            _ = create_task_response(
                task_id="test-task",
                status="open",  # invalid for TaskStatus
                created_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 8, 26, 10, 0, 0, tzinfo=UTC),
                motivation="high",  # invalid for TaskMotivation
                eisenhower=MAX_EISENHOWER + 6,  # out of range
                area_id="area-xyz",
                priority=0,
            )

    def test_task_response_exposes_source_fields(self) -> None:
        """TaskResponse should surface source and source_id attributes."""
        task = create_task_response(task_id="task-source", source="github", source_id="123")

        assert task.source == "github"
        assert task.source_id == "123"

    def test_task_response_parses_sources_array(self) -> None:
        """TaskResponse should parse sources array payloads from API."""
        raw_payload = {
            "id": "task-sourced",
            "area_id": "area-xyz",
            "status": "next",
            "priority": 1,
            "motivation": "should",
            "eisenhower": 1,
            "created_at": "2025-08-26T10:00:00Z",
            "updated_at": "2025-08-26T10:05:00Z",
            "sources": [
                {"source": "github", "source_id": "123"},
                {"source": "notion", "source_id": "alpha"},
            ],
        }

        task = TaskResponse(**raw_payload)

        expected_sources_count = 2
        assert len(task.sources) == expected_sources_count
        assert task.sources[0].source == "github"
        assert task.source == "github"
        assert task.source_id == "123"
