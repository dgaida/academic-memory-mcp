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
    """Erstellt eine temporäre Umgebung für Tests mit verschachtelter Struktur.

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

    # Verschachtelte Quellstruktur: Semester/Person/Inbox
    source_class_dir = source_base / class_name
    source_nested_inbox = source_class_dir / "2025_SoSe" / "Peters" / "Inbox"
    source_nested_inbox.mkdir(parents=True)

    # Konfigurationen
    paths_cfg = tmp_path / "paths.yaml"
    folders_cfg = tmp_path / "folders.yaml"

    with open(paths_cfg, "w", encoding='utf-8') as f:
        yaml.dump({"class_paths": {class_name: str(source_class_dir)}}, f)

    with open(folders_cfg, "w", encoding='utf-8') as f:
        yaml.dump({"train_path": str(train_dir), "test_path": str(test_dir)}, f)

    return {
        "tmp_path": tmp_path,
        "train_dir": train_dir,
        "source_base": source_base,
        "source_class_dir": source_class_dir,
        "source_nested_inbox": source_nested_inbox,
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
    """Testet das Löschen eines "leeren" Ordners und seiner Eltern.

    Args:
        tmp_path: Temporärer Pfad von pytest.
    """
    base = tmp_path / "base"
    nested = base / "level1" / "level2"
    nested.mkdir(parents=True)
    (nested / ".Inbox_summary.md").write_text("summary", encoding='utf-8')

    cleanup_folder(nested, base)
    assert not nested.exists()
    assert not (base / "level1").exists()
    assert base.exists()


def test_cleanup_folder_not_empty(tmp_path: Path) -> None:
    """Testet, dass nicht leere Ordner behalten werden.

    Args:
        tmp_path: Temporärer Pfad von pytest.
    """
    base = tmp_path / "base"
    folder = base / "no_cleanup"
    folder.mkdir(parents=True)
    (folder / "keep.msg").write_text("content", encoding='utf-8')

    cleanup_folder(folder, base)
    assert folder.exists()


def test_process_dataset_moves_files_recursively(temp_env: dict) -> None:
    """Testet, ob E-Mails rekursiv korrekt verschoben werden.

    Args:
        temp_env: Temporäre Testumgebung.
    """
    class_name = temp_env["class_name"]
    source_nested_inbox = temp_env["source_nested_inbox"]
    target_inbox = temp_env["train_dir"] / class_name / "Inbox"

    # Eine alte E-Mail in der verschachtelten Quelle erstellen
    old_mail = source_nested_inbox / "old.msg"
    old_mail.write_text("old content", encoding='utf-8')

    # Parser simulieren, der ein altes Datum liefert
    parser = MagicMock()
    parser.get_email_date.return_value = datetime.now() - timedelta(days=500)

    class_paths = {class_name: str(temp_env["source_class_dir"])}

    process_dataset(temp_env["train_dir"], class_paths, n=1, parser=parser)

    assert (target_inbox / "old.msg").exists()
    assert not old_mail.exists()
    # Gesamte Quellstruktur sollte gelöscht sein, wenn sie leer war
    assert not temp_env["source_nested_inbox"].exists()
    assert not (temp_env["source_class_dir"] / "2025_SoSe").exists()


def test_process_dataset_multiple_sources(temp_env: dict) -> None:
    """Testet das Verschieben aus mehreren Quellordnern bis n erreicht ist.

    Args:
        temp_env: Temporäre Testumgebung.
    """
    class_name = temp_env["class_name"]
    source_class_dir = temp_env["source_class_dir"]

    # Zwei Quellordner erstellen
    src1 = source_class_dir / "Sem1" / "PersonA" / "Inbox"
    src2 = source_class_dir / "Sem2" / "PersonB" / "Inbox"
    src1.mkdir(parents=True)
    src2.mkdir(parents=True)

    (src1 / "mail1.msg").write_text("mail1", encoding='utf-8')
    (src2 / "mail2.msg").write_text("mail2", encoding='utf-8')

    parser = MagicMock()
    parser.get_email_date.return_value = datetime.now() - timedelta(days=500)

    class_paths = {class_name: str(source_class_dir)}

    # Wir brauchen 2 E-Mails
    process_dataset(temp_env["train_dir"], class_paths, n=2, parser=parser)

    target_inbox = temp_env["train_dir"] / class_name / "Inbox"
    assert (target_inbox / "mail1.msg").exists()
    assert (target_inbox / "mail2.msg").exists()
    assert not src1.exists()
    assert not src2.exists()
