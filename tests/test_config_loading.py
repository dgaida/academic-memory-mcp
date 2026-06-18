"""Tests for the configuration loading logic."""
import pytest
from mcp_university.config import UserConfig

def test_user_config_single_email():
    """Test UserConfig with a single email string."""
    data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    user = UserConfig(**data)
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.emails == []

def test_user_config_email_list():
    """Test UserConfig with email as a list."""
    data = {
        "name": "Test User",
        "email": ["primary@example.com", "secondary@example.com"]
    }
    user = UserConfig(**data)
    assert user.name == "Test User"
    assert user.email == "primary@example.com"
    assert user.emails == ["primary@example.com", "secondary@example.com"]

def test_user_config_explicit_emails():
    """Test UserConfig with explicit emails list and single email string."""
    data = {
        "name": "Test User",
        "email": "primary@example.com",
        "emails": ["other@example.com"]
    }
    user = UserConfig(**data)
    assert user.name == "Test User"
    assert user.email == "primary@example.com"
    assert user.emails == ["other@example.com"]

def test_user_config_empty_email_list():
    """Test UserConfig with an empty email list."""
    data = {
        "name": "Test User",
        "email": []
    }
    user = UserConfig(**data)
    assert user.email == ""
    assert user.emails == []
