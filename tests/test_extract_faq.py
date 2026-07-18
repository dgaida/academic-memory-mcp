"""Unit tests for scripts/extract_faq.py."""

import pytest
import yaml
from unittest.mock import MagicMock, patch
from pathlib import Path
from scripts.extract_faq import (
    load_yaml,
    load_memory_paths,
    collect_emails,
    parse_llm_response,
    extract_existing_questions,
    save_faq,
    main,
)


def test_load_yaml(tmp_path: Path) -> None:
    """Tests loading a YAML file successfully and with a missing file.

    Args:
        tmp_path (Path): pytest temporary path fixture.

    Returns:
        None
    """
    non_existent = tmp_path / "missing.yaml"
    res_empty = load_yaml(non_existent)
    assert res_empty == {}

    valid_file = tmp_path / "valid.yaml"
    data = {"key": "value"}
    with open(valid_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    res_valid = load_yaml(valid_file)
    assert res_valid == data


def test_load_memory_paths(tmp_path: Path) -> None:
    """Tests loading memory paths, creating default if missing.

    Args:
        tmp_path (Path): pytest temporary path fixture.

    Returns:
        None
    """
    memory_config_path = tmp_path / "config" / "classifier_memory_paths.yaml"
    paths_cfg = {
        "class_paths": {
            "BachelorThesis": str(tmp_path / "BachelorThesis")
        }
    }

    # File does not exist initially
    assert not memory_config_path.exists()
    config_data = load_memory_paths(memory_config_path, paths_cfg)
    assert memory_config_path.exists()
    assert config_data["class_paths"]["BachelorThesis"] == f"{tmp_path}/BachelorThesis/Memory"

    # Loading existing file
    config_data_loaded = load_memory_paths(memory_config_path, paths_cfg)
    assert config_data_loaded == config_data


def test_collect_emails(tmp_path: Path) -> None:
    """Tests collecting emails from both classifier_paths and train_test folders.

    Args:
        tmp_path (Path): pytest temporary path fixture.

    Returns:
        None
    """
    # Setup folders
    bachelor_dir = tmp_path / "BachelorThesis"
    bachelor_dir.mkdir()
    email_1 = bachelor_dir / "email_1.eml"
    email_1.write_text("dummy")

    train_dir = tmp_path / "train" / "BachelorThesis"
    train_dir.mkdir(parents=True)
    email_2 = train_dir / "email_2.msg"
    email_2.write_text("dummy")

    paths_cfg = {
        "class_paths": {
            "BachelorThesis": str(bachelor_dir)
        }
    }
    folders_cfg = {
        "train_path": str(tmp_path / "train"),
        "test_path": str(tmp_path / "test")
    }

    emails = collect_emails("BachelorThesis", paths_cfg, folders_cfg)
    assert len(emails) == 2
    assert email_1 in emails
    assert email_2 in emails


def test_parse_llm_response() -> None:
    """Tests parsing diverse LLM responses.

    Returns:
        None
    """
    # Case 1: Suitable response
    resp_1 = "GEEIGNET: JA\nFRAGE: Wie melde ich an?\nANTWORT: Per Formular."
    parsed_1 = parse_llm_response(resp_1)
    assert parsed_1 == ("Wie melde ich an?", "Per Formular.")

    # Case 2: Unsuitable response
    resp_2 = "GEEIGNET: NEIN\nFRAGE: Keine\nANTWORT: Keine"
    parsed_2 = parse_llm_response(resp_2)
    assert parsed_2 is None

    # Case 3: Empty/None response
    assert parse_llm_response("") is None

    # Case 4: Regex fallback
    resp_4 = "Der Text ist GEEIGNET: JA. Die Frage ist FRAGE: Wann abgeben? ANTWORT: Morgen."
    parsed_4 = parse_llm_response(resp_4)
    assert parsed_4 == ("Wann abgeben?", "Morgen.")


def test_extract_existing_questions(tmp_path: Path) -> None:
    """Tests extracting existing questions from an FAQ file.

    Args:
        tmp_path (Path): pytest temporary path fixture.

    Returns:
        None
    """
    faq_path = tmp_path / "FAQ.md"
    assert extract_existing_questions(faq_path) == []

    faq_path.write_text(
        "# FAQ\n\n## Fragen & Antworten\n\n### 1. Wie melde ich an?\n**Antwort:**\nPer Formular.\n\n---\n\n### 2. Wann abgeben?\n**Antwort:**\nIn 4 Wochen.\n",
        encoding="utf-8"
    )
    existing = extract_existing_questions(faq_path)
    assert existing == ["wie melde ich an?", "wann abgeben?"]


def test_save_faq(tmp_path: Path) -> None:
    """Tests saving and updating FAQ.md, preventing duplicates.

    Args:
        tmp_path (Path): pytest temporary path fixture.

    Returns:
        None
    """
    faq_path = tmp_path / "FAQ.md"
    new_pairs = [
        ("Wie melde ich an?", "Per Formular."),
        ("Wann abgeben?", "In 4 Wochen.")
    ]

    # Create new FAQ
    save_faq(faq_path, new_pairs, "BachelorThesis")
    assert faq_path.exists()
    content = faq_path.read_text(encoding="utf-8")
    assert "Wie melde ich an?" in content
    assert "Per Formular." in content

    # Update with some duplicates and one new question
    updated_pairs = [
        ("wie melde ich an?", "A different answer"), # Duplicate question, should be skipped
        ("Welche Formatierung?", "12pt Arial.") # New question
    ]
    save_faq(faq_path, updated_pairs, "BachelorThesis")
    updated_content = faq_path.read_text(encoding="utf-8")
    # Should contain exactly 3 questions
    assert "### 1. Wie melde ich an?" in updated_content
    assert "### 2. Wann abgeben?" in updated_content
    assert "### 3. Welche Formatierung?" in updated_content
    # The duplicate's answer should not overwrite the original
    assert "Per Formular." in updated_content
    assert "A different answer" not in updated_content


@patch("scripts.extract_faq.argparse.ArgumentParser.parse_args")
@patch("scripts.extract_faq.load_yaml")
@patch("scripts.extract_faq.load_memory_paths")
@patch("scripts.extract_faq.collect_emails")
@patch("scripts.extract_faq.LLMClientWrapper")
@patch("scripts.extract_faq.get_config")
@patch("scripts.extract_faq.MailParser")
def test_main_execution(
    mock_mail_parser: MagicMock,
    mock_get_config: MagicMock,
    mock_llm_client_cls: MagicMock,
    mock_collect_emails: MagicMock,
    mock_load_memory_paths: MagicMock,
    mock_load_yaml: MagicMock,
    mock_parse_args: MagicMock,
    tmp_path: Path,
) -> None:
    """Tests the full main execution of the script.

    Args:
        mock_mail_parser: Mocked MailParser class.
        mock_get_config: Mocked get_config function.
        mock_llm_client_cls: Mocked LLMClientWrapper class.
        mock_collect_emails: Mocked collect_emails function.
        mock_load_memory_paths: Mocked load_memory_paths function.
        mock_load_yaml: Mocked load_yaml function.
        mock_parse_args: Mocked parse_args function.
        tmp_path (Path): pytest temporary path fixture.

    Returns:
        None
    """
    # Configure mock args
    mock_args = MagicMock()
    mock_args.class_name = "BachelorThesis"
    mock_args.n = 2
    mock_args.paths_config = "paths.yaml"
    mock_args.folders_config = "folders.yaml"
    mock_args.memory_config = "memory.yaml"
    mock_args.user_config = "user.yaml"
    mock_parse_args.return_value = mock_args

    # Configure load_yaml side effects
    mock_load_yaml.side_effect = [
        {"class_paths": {"BachelorThesis": "/tmp"}}, # paths_cfg
        {"train_path": "/train"}, # folders_cfg
        {"name": "Daniel Gaida"} # user_cfg
    ]

    # Configure memory_cfg
    faq_folder = tmp_path / "Memory"
    faq_folder.mkdir()
    mock_load_memory_paths.return_value = {
        "class_paths": {"BachelorThesis": str(faq_folder)}
    }

    # Emails found
    email_path = tmp_path / "email_1.eml"
    email_path.write_text("content")
    mock_collect_emails.return_value = [email_path]

    # MailParser return
    mock_parser_inst = mock_mail_parser.return_value
    mock_parser_inst.parse.return_value = "Subject: Test\nFrom: Student\nBody: Hello"

    # LLM Mock
    mock_llm_inst = mock_llm_client_cls.return_value
    mock_llm_inst.chat.return_value = {
        "message": {
            "content": "GEEIGNET: JA\nFRAGE: Wie funktioniert das?\nANTWORT: Ganz einfach."
        }
    }

    main()

    # FAQ.md should have been created
    faq_file = faq_folder / "FAQ.md"
    assert faq_file.exists()
    faq_content = faq_file.read_text(encoding="utf-8")
    assert "Wie funktioniert das?" in faq_content
    assert "Ganz einfach." in faq_content
