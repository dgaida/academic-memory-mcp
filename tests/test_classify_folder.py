"""Tests for test_classify_folder.py."""
from pathlib import Path
from unittest.mock import patch
from mcp_university.classifier.classify_folder import classify_and_move

@patch('mcp_university.classifier.classify_folder.EmailClassifier')
def test_classify_and_move(mock_classifier_class, tmp_path):
    """Tests test_classify_and_move."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create dummy msg files
    msg1 = source_dir / "test1.msg"
    msg1.touch()
    msg2 = source_dir / "test2.msg"
    msg2.touch()

    # Mock classifier
    mock_classifier = mock_classifier_class.return_value
    mock_classifier.predict.side_effect = [
        {"prediction": "ClassA"},
        {"prediction": "ClassB"}
    ]

    classify_and_move(source_dir, Path("dummy_model"))

    # Verify files moved to correct subfolders
    assert (source_dir / "ClassA" / "test1.msg").exists()
    assert (source_dir / "ClassB" / "test2.msg").exists()
    assert not msg1.exists()
    assert not msg2.exists()

@patch('mcp_university.classifier.classify_folder.EmailClassifier')
def test_classify_and_move_with_output_dir(mock_classifier_class, tmp_path):
    """Tests test_classify_and_move_with_output_dir."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    msg1 = source_dir / "test1.msg"
    msg1.touch()

    mock_classifier = mock_classifier_class.return_value
    mock_classifier.predict.return_value = {"prediction": "ClassA"}

    classify_and_move(source_dir, Path("dummy_model"), output_dir)

    assert (output_dir / "ClassA" / "test1.msg").exists()
    assert not msg1.exists()

@patch('mcp_university.classifier.classify_folder.EmailClassifier')
def test_classify_and_move_duplicate_names(mock_classifier_class, tmp_path):
    """Tests test_classify_and_move_duplicate_names."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    msg1 = source_dir / "test.msg"
    msg1.touch()

    # Pre-create a file in the target location
    target_dir = source_dir / "ClassA"
    target_dir.mkdir()
    (target_dir / "test.msg").touch()

    mock_classifier = mock_classifier_class.return_value
    mock_classifier.predict.return_value = {"prediction": "ClassA"}

    classify_and_move(source_dir, Path("dummy_model"))

    # Should be renamed to test_1.msg
    assert (target_dir / "test.msg").exists()
    assert (target_dir / "test_1.msg").exists()
