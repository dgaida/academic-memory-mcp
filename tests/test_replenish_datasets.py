"""Tests für das Skript replenish_datasets.py."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from scripts.replenish_datasets import (
    cleanup_folder, get_email_count, is_older_than_one_year,
    process_dataset
)


@pytest.fixture
def temp_env(tmp_path: Path) -> dict:
    """Erstellt eine temporäre Umgebung für Tests.

    Args:
        tmp_path: Temporärer Pfad von pytest.

    Returns:
        dict: Ein Dictionary mit den Pfaden der Testumgebung.
    """
    # Verzeichnisse einrichten
    train_dir = tmp_path / "train"
    test_dir = tmp_path / "test"
    source_base = tmp_path / "source"

    train_dir.mkdir()
    test_dir.mkdir()
    source_base.mkdir()

    # Klassenordner
    class_name = "ClassA"
    (train_dir / class_name / "Inbox").mkdir(parents=True)
    (source_base / class_name / "Inbox").mkdir(parents=True)

    # Konfigurationen
    paths_cfg = tmp_path / "paths.yaml"
    folders_cfg = tmp_path / "folders.yaml"

    with open(paths_cfg, "w", encoding='utf-8') as f:
        yaml.dump({"class_paths": {class_name: str(source_base / class_name)}}, f)

    with open(folders_cfg, "w", encoding='utf-8') as f:
        yaml.dump({"train_path": str(train_dir), "test_path": str(test_dir)}, f)

    return {
        "tmp_path": tmp_path,
        "train_dir": train_dir,
        "source_base": source_base,
        "paths_cfg": paths_cfg,
        "folders_cfg": folders_cfg,
        "class_name": class_name
    }


def test_get_email_count(tmp_path: Path) -> None:
    """Testet das Zählen von E-Mails.

    Args:
        tmp_path: Temporärer Pfad von pytest.
    """
    email_dir = tmp_path / "emails"
    email_dir.mkdir()
    (email_dir / "test1.msg").write_text("content", encoding='utf-8')
    (email_dir / "test2.eml").write_text("content", encoding='utf-8')
    (email_dir / "test3.txt").write_text("content", encoding='utf-8')

    assert get_email_count(email_dir) == 2


def test_is_older_than_one_year() -> None:
    """Testet die Prüfung auf E-Mails älter als ein Jahr."""
    parser = MagicMock()

    # Altes Datum simulieren
    parser.get_email_date.return_value = datetime.now() - timedelta(days=400)
    assert is_older_than_one_year(Path("old.msg"), parser) is True

    # Neues Datum simulieren
    parser.get_email_date.return_value = datetime.now() - timedelta(days=10)
    assert is_older_than_one_year(Path("new.msg"), parser) is False

    # Fehler simulieren
    parser.get_email_date.side_effect = Exception("error")
    assert is_older_than_one_year(Path("error.msg"), parser) is False


def test_cleanup_folder(tmp_path: Path) -> None:
    """Testet das Löschen eines "leeren" Ordners.

    Args:
        tmp_path: Temporärer Pfad von pytest.
    """
    folder = tmp_path / "cleanup"
    folder.mkdir()
    (folder / ".Inbox_summary.md").write_text("summary", encoding='utf-8')

    cleanup_folder(folder)
    assert not folder.exists()


def test_cleanup_folder_not_empty(tmp_path: Path) -> None:
    """Testet, dass nicht leere Ordner behalten werden.

    Args:
        tmp_path: Temporärer Pfad von pytest.
    """
    folder = tmp_path / "no_cleanup"
    folder.mkdir()
    (folder / "keep.msg").write_text("content", encoding='utf-8')

    cleanup_folder(folder)
    assert folder.exists()


def test_process_dataset_moves_files(temp_env: dict) -> None:
    """Testet, ob E-Mails korrekt verschoben werden.

    Args:
        temp_env: Temporäre Testumgebung.
    """
    class_name = temp_env["class_name"]
    source_inbox = temp_env["source_base"] / class_name / "Inbox"
    target_inbox = temp_env["train_dir"] / class_name / "Inbox"

    # Eine alte E-Mail in der Quelle erstellen
    old_mail = source_inbox / "old.msg"
    old_mail.write_text("old content", encoding='utf-8')

    # Parser simulieren, der ein altes Datum liefert
    parser = MagicMock()
    parser.get_email_date.return_value = datetime.now() - timedelta(days=500)

    class_paths = {class_name: str(temp_env["source_base"] / class_name)}

    process_dataset(temp_env["train_dir"], class_paths, n=1, parser=parser)

    assert (target_inbox / "old.msg").exists()
    assert not old_mail.exists()
    # Quellordner sollte gelöscht sein, wenn er nach dem Verschieben leer war
    assert not source_inbox.exists()


def test_process_dataset_not_moving_if_enough(temp_env: dict) -> None:
    """Testet, dass nichts verschoben wird, wenn genug E-Mails da sind.

    Args:
        temp_env: Temporäre Testumgebung.
    """
    class_name = temp_env["class_name"]
    source_inbox = temp_env["source_base"] / class_name / "Inbox"
    target_inbox = temp_env["train_dir"] / class_name / "Inbox"

    # E-Mail im Ziel erstellen
    (target_inbox / "existing.msg").write_text("content", encoding='utf-8')

    # E-Mail in der Quelle erstellen
    (source_inbox / "source.msg").write_text("content", encoding='utf-8')

    parser = MagicMock()
    parser.get_email_date.return_value = datetime.now() - timedelta(days=500)

    class_paths = {class_name: str(temp_env["source_base"] / class_name)}

    # Wir brauchen nur eine, und wir haben schon eine
    process_dataset(temp_env["train_dir"], class_paths, n=1, parser=parser)

    assert not (target_inbox / "source.msg").exists()
    assert (source_inbox / "source.msg").exists()
