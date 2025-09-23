"""Tests for LunaTask people models."""

import json
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from lunatask_mcp.api.models_people import (
    PersonCreate,
    PersonRelationshipStrength,
    PersonResponse,
)


class TestPersonRelationshipStrength:
    """Test suite for PersonRelationshipStrength enum."""

    def test_enum_has_all_required_values(self) -> None:
        """PersonRelationshipStrength should have all 7 required relationship values."""
        expected_values = {
            "family",
            "intimate-friends",
            "close-friends",
            "casual-friends",
            "acquaintances",
            "business-contacts",
            "almost-strangers",
        }
        actual_values = {member.value for member in PersonRelationshipStrength}
        assert actual_values == expected_values

    def test_enum_validation_accepts_valid_values(self) -> None:
        """PersonRelationshipStrength should validate all defined values."""
        for strength in PersonRelationshipStrength:
            # Should not raise ValidationError
            assert PersonRelationshipStrength(strength.value) == strength

    def test_enum_validation_rejects_invalid_values(self) -> None:
        """PersonRelationshipStrength should reject invalid relationship values."""
        with pytest.raises(ValueError, match="invalid-strength"):
            PersonRelationshipStrength("invalid-strength")


class TestPersonCreate:
    """Test suite for PersonCreate model."""

    def test_create_with_minimal_required_fields(self) -> None:
        """PersonCreate should work with only first_name and last_name."""
        person = PersonCreate(first_name="John", last_name="Doe")

        assert person.first_name == "John"
        assert person.last_name == "Doe"
        assert person.relationship_strength == PersonRelationshipStrength.CASUAL_FRIENDS
        assert person.source is None
        assert person.source_id is None
        assert person.email is None
        assert person.birthday is None
        assert person.phone is None

    def test_create_with_all_optional_fields(self) -> None:
        """PersonCreate should accept all optional fields."""
        person = PersonCreate(
            first_name="Jane",
            last_name="Smith",
            relationship_strength=PersonRelationshipStrength.FAMILY,
            source="salesforce",
            source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
            email="jane.smith@example.com",
            birthday=date(1990, 5, 15),
            phone="+1-555-123-4567",
        )

        assert person.first_name == "Jane"
        assert person.last_name == "Smith"
        assert person.relationship_strength == PersonRelationshipStrength.FAMILY
        assert person.source == "salesforce"
        assert person.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"
        assert person.email == "jane.smith@example.com"
        assert person.birthday == date(1990, 5, 15)
        assert person.phone == "+1-555-123-4567"

    def test_serialization_excludes_none_values(self) -> None:
        """PersonCreate serialization should exclude None values."""
        person = PersonCreate(first_name="John", last_name="Doe", source="github")

        payload = json.loads(person.model_dump_json(exclude_none=True))

        assert payload["first_name"] == "John"
        assert payload["last_name"] == "Doe"
        assert payload["relationship_strength"] == "casual-friends"
        assert payload["source"] == "github"
        # None values should be excluded
        assert "source_id" not in payload
        assert "email" not in payload
        assert "birthday" not in payload
        assert "phone" not in payload

    def test_birthday_serializes_to_iso_date_string(self) -> None:
        """PersonCreate should serialize birthday as ISO-8601 date string."""
        person = PersonCreate(first_name="Jane", last_name="Smith", birthday=date(1990, 12, 25))

        payload = json.loads(person.model_dump_json(exclude_none=True))
        assert payload["birthday"] == "1990-12-25"

    def test_validation_error_missing_first_name(self) -> None:
        """PersonCreate should raise ValidationError when first_name is missing."""
        with pytest.raises(ValidationError) as exc_info:
            PersonCreate(last_name="Doe")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("first_name",) for error in errors)

    def test_validation_error_missing_last_name(self) -> None:
        """PersonCreate should raise ValidationError when last_name is missing."""
        with pytest.raises(ValidationError) as exc_info:
            PersonCreate(first_name="John")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("last_name",) for error in errors)

    def test_extra_fields_rejected(self) -> None:
        """PersonCreate should reject extra fields not in the schema."""
        with pytest.raises(ValidationError) as exc_info:
            PersonCreate(
                first_name="John",
                last_name="Doe",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in str(error) for error in errors)

    def test_relationship_strength_default_value(self) -> None:
        """PersonCreate should default relationship_strength to casual-friends."""
        person = PersonCreate(first_name="John", last_name="Doe")
        assert person.relationship_strength == PersonRelationshipStrength.CASUAL_FRIENDS

    def test_relationship_strength_accepts_string_values(self) -> None:
        """PersonCreate should accept string values for relationship_strength."""
        person = PersonCreate(
            first_name="John",
            last_name="Doe",
            relationship_strength="family",  # type: ignore[arg-type]
        )
        assert person.relationship_strength == PersonRelationshipStrength.FAMILY


class TestPersonResponse:
    """Test suite for PersonResponse model."""

    def test_create_with_required_fields(self) -> None:
        """PersonResponse should work with all required fields."""
        person = PersonResponse(
            id="5999b945-b2b1-48c6-aa72-b251b75b3c2e",
            relationship_strength=PersonRelationshipStrength.BUSINESS_CONTACTS,
            created_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
        )

        assert person.id == "5999b945-b2b1-48c6-aa72-b251b75b3c2e"
        assert person.relationship_strength == PersonRelationshipStrength.BUSINESS_CONTACTS
        assert person.created_at == datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC)
        assert person.updated_at == datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC)

    def test_create_with_optional_persisted_fields(self) -> None:
        """PersonResponse should include optional persisted fields when returned."""
        person = PersonResponse(
            id="5999b945-b2b1-48c6-aa72-b251b75b3c2e",
            relationship_strength=PersonRelationshipStrength.FAMILY,
            email="john.doe@example.com",
            birthday=date(1985, 3, 20),
            phone="+1-555-987-6543",
            created_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
        )

        assert person.email == "john.doe@example.com"
        assert person.birthday == date(1985, 3, 20)
        assert person.phone == "+1-555-987-6543"

    def test_source_normalization_from_legacy_fields(self) -> None:
        """PersonResponse should normalize legacy source fields into sources list."""
        person = PersonResponse(
            id="5999b945-b2b1-48c6-aa72-b251b75b3c2e",
            relationship_strength=PersonRelationshipStrength.BUSINESS_CONTACTS,
            source="salesforce",
            source_id="352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7",
            created_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
        )

        assert len(person.sources) == 1
        source_entry = person.sources[0]
        assert source_entry.source == "salesforce"
        assert source_entry.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"

    def test_computed_source_properties(self) -> None:
        """PersonResponse should provide computed source properties for backwards compatibility."""
        person = PersonResponse(
            id="5999b945-b2b1-48c6-aa72-b251b75b3c2e",
            relationship_strength=PersonRelationshipStrength.BUSINESS_CONTACTS,
            sources=[{"source": "salesforce", "source_id": "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"}],
            created_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
        )

        assert person.source == "salesforce"
        assert person.source_id == "352fd2d7-cdc0-4e91-a0a3-9d6cc9d440e7"

    def test_computed_source_properties_return_none_when_no_sources(self) -> None:
        """PersonResponse computed source properties should return None when no sources."""
        person = PersonResponse(
            id="5999b945-b2b1-48c6-aa72-b251b75b3c2e",
            relationship_strength=PersonRelationshipStrength.CASUAL_FRIENDS,
            created_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
        )

        assert person.sources == []
        assert person.source is None
        assert person.source_id is None

    def test_enum_serialization_uses_string_values(self) -> None:
        """PersonResponse should serialize enum values as strings in JSON."""
        person = PersonResponse(
            id="5999b945-b2b1-48c6-aa72-b251b75b3c2e",
            relationship_strength=PersonRelationshipStrength.INTIMATE_FRIENDS,
            created_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
            updated_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
        )

        payload = json.loads(person.model_dump_json())
        assert payload["relationship_strength"] == "intimate-friends"

    def test_field_validation_rejects_invalid_id(self) -> None:
        """PersonResponse should validate field constraints."""
        with pytest.raises(ValidationError) as exc_info:
            PersonResponse(
                id="",  # Empty string should fail
                relationship_strength=PersonRelationshipStrength.FAMILY,
                created_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
                updated_at=datetime(2021, 1, 10, 10, 39, 25, tzinfo=UTC),
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("id",) for error in errors)
