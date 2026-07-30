"""Schema tests for user and role payload validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas.role import RoleCreate, RoleUpdate
from app.api.schemas.user import UserCreate, UserUpdate


def test_user_create_trims_and_validates_username():
    """Assert that UserCreate strips surrounding whitespace and keeps only usernames that match the allowed character set."""
    schema = UserCreate(
        username="  planner_user  ",
        email="planner@example.com",
        full_name="  Maintenance Planner  ",
        password="secret123",
    )

    assert schema.username == "planner_user"
    assert schema.full_name == "Maintenance Planner"


def test_user_create_rejects_invalid_username_characters():
    """Assert that UserCreate rejects usernames that include spaces or other unsupported characters."""
    with pytest.raises(ValidationError):
        UserCreate(
            username="invalid user",
            email="planner@example.com",
            full_name="Maintenance Planner",
            password="secret123",
        )


def test_user_update_rejects_short_passwords():
    """Assert that UserUpdate rejects replacement passwords that do not meet the minimum length requirement."""
    with pytest.raises(ValidationError):
        UserUpdate(password="123")


def test_role_create_trims_name_and_description():
    """Assert that RoleCreate strips whitespace from both the role name and its optional description."""
    schema = RoleCreate(name="  Planner  ", description="  Schedules maintenance work.  ")

    assert schema.name == "Planner"
    assert schema.description == "Schedules maintenance work."


def test_role_update_rejects_empty_name():
    """Assert that RoleUpdate rejects empty strings so updates cannot blank out role names."""
    with pytest.raises(ValidationError):
        RoleUpdate(name="   ")
