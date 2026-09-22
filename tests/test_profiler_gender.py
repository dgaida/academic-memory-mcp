"""Tests for gender detection and storage in person profiles."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from mcp_university.summarizer.profiler import PersonProfiler

def test_extract_gender():
    profiler = PersonProfiler(storage_path=Path("Steckbriefe"))

    assert profiler._extract_gender(None) is None
    assert profiler._extract_gender("# Steckbrief\n- Geschlecht: Herr\n- Rolle: Student") == "Herr"
    assert profiler._extract_gender("# Steckbrief\n2. Geschlecht: Frau\n- Rolle: Studentin") == "Frau"
    assert profiler._extract_gender("# Steckbrief\n- Geschlecht: Herr/Frau") is None

def test_get_gender_from_existing_profile(tmp_path):
    storage_path = tmp_path / "Steckbriefe"
    storage_path.mkdir()

    email = "max.mustermann@example.com"
    profile_file = storage_path / f"{email}.md"
    profile_file.write_text("# Steckbrief\n1. Name: Max\n- Geschlecht: Herr\n", encoding="utf-8")

    profiler = PersonProfiler(storage_path=storage_path)

    with patch("mcp_university.summarizer.profiler.PersonProfiler.get_profile") as mock_get_profile, \
         patch("mcp_university.summarizer.engine.Summarizer.determine_gender") as mock_determine_gender:
        mock_get_profile.return_value = profile_file.read_text(encoding="utf-8")

        gender = profiler.get_gender(email, "Max")

        assert gender == "Herr"
        mock_determine_gender.assert_not_called()

def test_get_gender_missing_in_profile_determines_and_saves(tmp_path):
    storage_path = tmp_path / "Steckbriefe"
    storage_path.mkdir()

    email = "anna.meier@example.com"
    profile_file = storage_path / f"{email}.md"
    profile_file.write_text("# Steckbrief\n1. Name: Anna Meier\n- Rolle: Studentin\n", encoding="utf-8")

    profiler = PersonProfiler(storage_path=storage_path)

    with patch("mcp_university.summarizer.profiler.PersonProfiler.get_profile") as mock_get_profile, \
         patch("mcp_university.summarizer.engine.Summarizer.determine_gender", return_value="Frau") as mock_determine_gender:
        mock_get_profile.return_value = profile_file.read_text(encoding="utf-8")

        gender = profiler.get_gender(email, "Anna")

        assert gender == "Frau"
        mock_determine_gender.assert_called_once_with("Anna")

        # Verify profile was updated on disk with gender
        updated_content = profile_file.read_text(encoding="utf-8")
        assert "Geschlecht: Frau" in updated_content
