"""Tests for the ProfileStore class."""
from pathlib import Path
import pytest
from mcp_university.metadata.profile_store import ProfileStore


def test_profile_store_lifecycle(tmp_path: Path) -> None:
    """Tests the full lifecycle of ProfileStore.

    This includes initialization, adding processed emails, and retrieving processed filenames.

    Args:
        tmp_path: Pytest fixture representing a temporary directory path.

    Returns:
        None
    """
    db_file = tmp_path / "test_profiles.db"

    # 1. Test initialization
    store = ProfileStore(db_file)
    assert db_file.exists()

    # 2. Test get_processed_filenames for an address that does not exist yet (should be empty set)
    filenames = store.get_processed_filenames("nonexistent@example.com")
    assert filenames == set()

    # 3. Test add_processed_emails
    store.add_processed_emails("test@example.com", ["email1.msg", "email2.msg"])

    # Verify they were added (case-insensitive for email address)
    filenames = store.get_processed_filenames("TEST@EXAMPLE.COM")
    assert filenames == {"email1.msg", "email2.msg"}

    # 4. Test INSERT OR IGNORE by adding duplicate entries
    store.add_processed_emails("test@example.com", ["email1.msg", "email3.msg"])
    filenames = store.get_processed_filenames("test@example.com")
    assert filenames == {"email1.msg", "email2.msg", "email3.msg"}
