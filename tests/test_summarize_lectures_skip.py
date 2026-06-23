"""Tests for test_summarize_lectures_skip.py."""
"""Tests for the skip logic in summarize_lectures.py."""
import os
import time

from unittest.mock import patch

import pytest
from scripts.summarize_lectures import main

@pytest.fixture
def temp_dirs(tmp_path):
    """Provides temporary source and target directories."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    return source_dir, target_dir

def test_skip_logic(temp_dirs):
    """Tests test_skip_logic."""
    """Tests that a PDF is skipped if a newer MD summary exists."""
    source_dir, target_dir = temp_dirs
    pdf_path = source_dir / "test.pdf"
    pdf_path.write_text("dummy pdf")

    md_path = target_dir / "test.md"
    md_path.write_text("existing summary")

    # Set MD file to be newer than PDF
    os.utime(pdf_path, (time.time() - 100, time.time() - 100))
    os.utime(md_path, (time.time(), time.time()))

    with patch("scripts.summarize_lectures.LLMClient"),          patch("scripts.summarize_lectures.PDFParser"),          patch("scripts.summarize_lectures.summarize_pdf") as mock_summarize:

        mock_summarize.return_value = "Summary"

        main(source_dir, target_dir)

        # If skip logic works, summarize_pdf should NOT be called
        mock_summarize.assert_not_called()

def test_process_if_pdf_newer(temp_dirs):
    """Tests test_process_if_pdf_newer."""
    """Tests that a PDF is processed if it is newer than the existing MD summary."""
    source_dir, target_dir = temp_dirs
    pdf_path = source_dir / "test.pdf"
    pdf_path.write_text("dummy pdf")

    md_path = target_dir / "test.md"
    md_path.write_text("old summary")

    # Set PDF file to be newer than MD
    os.utime(md_path, (time.time() - 100, time.time() - 100))
    os.utime(pdf_path, (time.time(), time.time()))

    with patch("scripts.summarize_lectures.LLMClient"),          patch("scripts.summarize_lectures.PDFParser"),          patch("scripts.summarize_lectures.summarize_pdf") as mock_summarize:

        mock_summarize.return_value = "New summary"

        main(source_dir, target_dir)

        # summarize_pdf SHOULD be called
        mock_summarize.assert_called_once()
