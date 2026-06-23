"""Tests for test_appointment_gui_logic.py."""
import pytest
import os
from datetime import datetime
from unittest.mock import MagicMock, patch
import pandas as pd
import gradio as gr

# Import the code to test
import scripts.appointment_gui as gui

def test_load_student_details_logic(tmp_path):
    """Test function docstring."""
    # Setup mock file system
    student_dir = tmp_path / "Student_Folder"
    student_dir.mkdir()

    email_file = student_dir / "20260222_201613 - Subject.msg"
    email_file.write_text("dummy email content")

    summary_file = student_dir / ".emails_summary.md"
    # Old summary
    summary_file.write_text("old summary")
    old_time = datetime(2020, 1, 1).timestamp()
    os.utime(str(summary_file), (old_time, old_time))

    # Mock Tools and other dependencies
    with patch("scripts.appointment_gui.get_class_paths") as mock_get_class_paths,          patch("scripts.appointment_gui.get_class_from_title") as mock_get_class,          patch("scripts.appointment_gui.extract_lastname") as mock_extract_lastname,          patch("scripts.appointment_gui.extract_email") as mock_extract_email,          patch("scripts.appointment_gui.find_student_folder") as mock_find_folder,          patch("scripts.appointment_gui.Tools") as mock_tools:

        mock_get_class_paths.return_value = {"TestClass": str(tmp_path)}
        mock_get_class.return_value = "TestClass"
        mock_extract_lastname.return_value = "Student"
        mock_extract_email.return_value = "student@test.com"
        mock_find_folder.return_value = student_dir

        # Setup Tool mocks
        mock_mail_parser = MagicMock()
        # Returns a new date (2026) for the email file
        mock_mail_parser.get_email_date.return_value = datetime(2026, 2, 22, 20, 16, 13)
        mock_mail_parser.parse.return_value = "Parsed Content"

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_email_conversation.return_value = "New Summary Content"

        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = "Profile Content"

        mock_tools.mail_parser.return_value = mock_mail_parser
        mock_tools.summarizer.return_value = mock_summarizer
        mock_tools.profiler.return_value = mock_profiler

        # Prepare event data
        evt = MagicMock(spec=gr.SelectData)
        evt.index = [0]
        df = pd.DataFrame([{"Betreff": "Subject", "Teilnehmer": "Student <student@test.com>"}])

        # Run the function
        summary, profile, explorer_root, folder_str = gui.load_student_details(evt, df)

        # Verify results
        assert "New Summary Content" in summary
        assert "Profile Content" in profile
        assert explorer_root == str(student_dir)

        # Verify that summarizer was called because summary was outdated
        mock_summarizer.summarize_email_conversation.assert_called_once()
        # Verify that profiler was called
        mock_profiler.get_profile.assert_called_with("student@test.com")

        # Verify file was updated
        assert summary_file.read_text(encoding="utf-8") == "New Summary Content"

def test_load_student_details_fresh_summary(tmp_path):
    """Test function docstring."""
    # Setup mock file system
    student_dir = tmp_path / "Student_Folder_Fresh"
    student_dir.mkdir()

    email_file = student_dir / "20260222_201613 - Subject.msg"
    email_file.write_text("dummy email content")

    summary_file = student_dir / ".emails_summary.md"
    # Fresh summary (newer than email)
    summary_file.write_text("fresh summary content")

    with patch("scripts.appointment_gui.get_class_paths") as mock_get_class_paths,          patch("scripts.appointment_gui.get_class_from_title") as mock_get_class,          patch("scripts.appointment_gui.extract_lastname") as mock_extract_lastname,          patch("scripts.appointment_gui.extract_email") as mock_extract_email,          patch("scripts.appointment_gui.find_student_folder") as mock_find_folder,          patch("scripts.appointment_gui.Tools") as mock_tools:

        mock_get_class_paths.return_value = {"TestClass": str(tmp_path)}
        mock_get_class.return_value = "TestClass"
        mock_extract_lastname.return_value = "Student"
        mock_extract_email.return_value = "student@test.com"
        mock_find_folder.return_value = student_dir

        mock_mail_parser = MagicMock()
        # Email date is 2026
        mock_mail_parser.get_email_date.return_value = datetime(2026, 2, 22, 20, 16, 13)

        # Summary mtime is NOW (fresher than 2026? Actually let's make it explicitly newer)
        future_time = datetime(2027, 1, 1).timestamp()
        os.utime(str(summary_file), (future_time, future_time))

        mock_summarizer = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = "Profile Content"

        mock_tools.mail_parser.return_value = mock_mail_parser
        mock_tools.summarizer.return_value = mock_summarizer
        mock_tools.profiler.return_value = mock_profiler

        evt = MagicMock(spec=gr.SelectData)
        evt.index = [0]
        df = pd.DataFrame([{"Betreff": "Subject", "Teilnehmer": "Student <student@test.com>"}])

        summary, profile, explorer_root, folder_str = gui.load_student_details(evt, df)

        # Verify results - summary should NOT be updated
        assert "fresh summary content" in summary
        mock_summarizer.summarize_email_conversation.assert_not_called()

def test_load_student_details_no_email(tmp_path):
    """Test function docstring."""
    # Setup mock file system
    student_dir = tmp_path / "Student_Folder_No_Email"
    student_dir.mkdir()

    with patch("scripts.appointment_gui.get_class_paths") as mock_get_class_paths,          patch("scripts.appointment_gui.get_class_from_title") as mock_get_class,          patch("scripts.appointment_gui.extract_lastname") as mock_extract_lastname,          patch("scripts.appointment_gui.extract_email") as mock_extract_email,          patch("scripts.appointment_gui.find_student_folder") as mock_find_folder,          patch("scripts.appointment_gui.Tools") as mock_tools:

        mock_get_class_paths.return_value = {"TestClass": str(tmp_path)}
        mock_get_class.return_value = "TestClass"
        mock_extract_lastname.return_value = "Unknown"
        mock_extract_email.return_value = None
        mock_find_folder.return_value = student_dir

        mock_profiler = MagicMock()
        mock_tools.profiler.return_value = mock_profiler

        evt = MagicMock(spec=gr.SelectData)
        evt.index = [0]
        df = pd.DataFrame([{"Betreff": "Subject", "Teilnehmer": "Unknown"}])

        summary, profile, explorer_root, folder_str = gui.load_student_details(evt, df)

        # Verify results - profile should NOT be generated if no email found
        assert "Kein Steckbrief gefunden" in profile
        mock_profiler.get_profile.assert_not_called()

if __name__ == "__main__":
    pytest.main([__file__])
