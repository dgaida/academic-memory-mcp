"""Skript zum Auffüllen von Trainings- und Testdatensätzen mit alten E-Mails.

Das Skript durchsucht die Klassenordner in den Trainings- und Testdaten.
Wenn ein Ordner (Inbox oder SentItems) weniger als N E-Mails enthält,
werden aus den in classifier_paths.yaml definierten Quellordnern
E-Mails verschoben, die älter als ein Jahr sind.
"""

import argparse
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import yaml

from mcp_university.parser.mail_parser import MailParser

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

SUMMARY_FILES = {".emails_summary.md", ".Inbox_summary.md", ".SentItems_summary.md"}


def load_yaml(file_path: Path) -> Dict:
    """Lädt eine YAML-Datei.

    Args:
        file_path: Pfad zur YAML-Datei.

    Returns:
        Dict: Der Inhalt der YAML-Datei oder ein leeres Dict bei Fehlern.
    """
    if not file_path.exists():
        logger.error(f"Konfigurationsdatei {file_path} nicht gefunden.")
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Fehler beim Laden von {file_path}: {e}")
            return {}


def get_email_count(path: Path) -> int:
    """Zählt die E-Mail-Dateien (.msg, .eml) in einem Verzeichnis.

    Args:
        path: Das zu durchsuchende Verzeichnis.

    Returns:
        int: Anzahl der gefundenen E-Mails.
    """
    if not path.exists():
        return 0
    return len([f for f in path.glob("*") if f.suffix.lower() in {".msg", ".eml"}])


def is_older_than_one_year(file_path: Path, parser: MailParser) -> bool:
    """Prüft, ob eine E-Mail älter als ein Jahr ist.

    Args:
        file_path: Pfad zur E-Mail-Datei.
        parser: Eine Instanz von MailParser.

    Returns:
        bool: True, wenn die E-Mail älter als 365 Tage ist, sonst False.
    """
    try:
        date = parser.get_email_date(file_path)
        if date == datetime.min:
            return False
        return date < datetime.now() - timedelta(days=365)
    except Exception as e:
        logger.error(f"Fehler beim Prüfen des Datums für {file_path}: {e}")
        return False


def cleanup_folder(path: Path, base_path: Path) -> None:
    """Löscht einen Ordner, wenn er außer Zusammenfassungsdateien leer ist,
    und geht rekursiv nach oben bis zum Basisverzeichnis.

    Args:
        path: Der zu bereinigende Ordner.
        base_path: Der Basisordner, der nicht gelöscht werden soll.
    """
    if not path.exists() or not path.is_dir() or path == base_path:
        return

    # Prüfen, ob der Ordner "leer" ist (nur Summary-Dateien oder nichts)
    entries = list(path.iterdir())
    remaining = [e for e in entries if e.name not in SUMMARY_FILES]

    if not remaining:
        logger.info(f"Bereinige leeren Ordner: {path}")
        try:
            # Zuerst Zusammenfassungsdateien löschen
            for e in entries:
                if e.is_file():
                    e.unlink()
                elif e.is_dir():
                    cleanup_folder(e, base_path)

            if path.exists() and not any(path.iterdir()):
                path.rmdir()
                # Rekursiv den Elternordner prüfen
                cleanup_folder(path.parent, base_path)
        except Exception as e:
            logger.error(f"Fehler beim Löschen von {path}: {e}")


def process_dataset(dataset_path: Path, class_paths: Dict[str, str], n: int, parser: MailParser) -> None:
    """Verarbeitet einen Datensatz (Train oder Test) und füllt ihn auf.

    Args:
        dataset_path: Pfad zum Datensatz-Verzeichnis.
        class_paths: Mapping von Klassennamen zu Quellpfaden.
        n: Mindestanzahl an E-Mails pro Ordner.
        parser: Eine Instanz von MailParser.
    """
    if not dataset_path.exists():
        logger.warning(f"Datensatz-Pfad {dataset_path} existiert nicht.")
        return

    logger.info(f"Verarbeite Datensatz: {dataset_path}")

    for class_name, source_base_path_str in class_paths.items():
        class_dir = dataset_path / class_name
        if not class_dir.is_dir():
            continue

        for subfolder in ["Inbox", "SentItems"]:
            target_dir = class_dir / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)

            count_before = get_email_count(target_dir)
            logger.info(f"Prüfe {target_dir}: {count_before} E-Mails gefunden.")

            if count_before < n:
                needed = n - count_before
                source_base_path = Path(source_base_path_str)

                logger.info(f"Suche rekursiv in {source_base_path} nach '{subfolder}'...")
                if not source_base_path.exists():
                    logger.warning(f"Quellbasisverzeichnis {source_base_path} existiert nicht.")
                    continue

                # Rekursiv nach allen Unterordnern mit dem Namen (Inbox/SentItems) suchen
                source_dirs = [d for d in source_base_path.rglob(subfolder) if d.is_dir()]

                moved_count = 0
                for source_dir in source_dirs:
                    if moved_count >= needed:
                        break

                    # Alle potenziellen E-Mails holen
                    source_emails = [f for f in source_dir.glob("*") if f.suffix.lower() in {".msg", ".eml"}]

                    for email_file in source_emails:
                        if moved_count >= needed:
                            break

                        if is_older_than_one_year(email_file, parser):
                            dest = target_dir / email_file.name
                            if not dest.exists():
                                logger.info(f"Verschiebe {email_file} nach {target_dir}")
                                shutil.move(str(email_file), str(dest))
                                moved_count += 1
                            else:
                                logger.debug(f"Datei {email_file.name} existiert bereits im Ziel, überspringe.")

                    # Quellordner bereinigen, wenn er jetzt leer ist (ohne Summaries)
                    cleanup_folder(source_dir, source_base_path)

                count_after = get_email_count(target_dir)
                logger.info(f"Abgeschlossen {target_dir}: {count_after} E-Mails insgesamt (verschoben {moved_count}).")
            else:
                logger.info(f"{target_dir} hat bereits genug E-Mails ({count_before} >= {n}).")


def main() -> None:
    """Haupteinstiegspunkt für das Skript."""
    parser = argparse.ArgumentParser(description="Füllt Trainings-/Testdatensätze mit alten E-Mails auf.")
    parser.add_argument("-n", type=int, default=100, help="Mindestanzahl E-Mails pro Ordner (Default: 100)")
    parser.add_argument("--config-paths", type=str, default="config/classifier_paths.yaml",
                        help="Pfad zu classifier_paths.yaml")
    parser.add_argument("--config-folders", type=str, default="config/train_test_folders.yaml",
                        help="Pfad zu train_test_folders.yaml")

    args = parser.parse_args()

    paths_cfg = load_yaml(Path(args.config_paths))
    folders_cfg = load_yaml(Path(args.config_folders))

    class_paths = paths_cfg.get("class_paths", {})
    train_path = Path(folders_cfg.get("train_path", "data/classifier/train"))
    test_path = Path(folders_cfg.get("test_path", "data/classifier/test"))

    mail_parser = MailParser()

    process_dataset(train_path, class_paths, args.n, mail_parser)
    process_dataset(test_path, class_paths, args.n, mail_parser)


if __name__ == "__main__":
    main()
