"""Skript zum Sortieren von E-Mails basierend auf Klassifizierung."""
import argparse
import logging
import shutil
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from mcp_university.classifier.engine import EmailClassifier
from mcp_university.parser.mail_parser import MailParser

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_semester(date: datetime) -> str:
    """Bestimmt den Semester-Ordnernamen basierend auf dem Datum.

    SoSe: 01.04. - 30.09. -> YYYY_SoSe
    WS: 01.10. - 31.03. -> YYYY_YY+1_WS

    Args:
        date: Das Datum der E-Mail.

    Returns:
        str: Der Name des Semester-Ordners.
    """
    year = date.year
    month = date.month

    if 4 <= month <= 9:
        return f"{year}_SoSe"
    else:
        if month >= 10:
            return f"{year}_{str(year + 1)[2:]}_WS"
        else:
            return f"{year-1}_{str(year)[2:]}_WS"

def extract_lastname(name_str: str) -> str:
    """Extrahiert den Nachnamen aus einem Namensstring.

    Z.B. 'Max Mustermann' oder 'Mustermann, Max'.

    Args:
        name_str: Der zu parsende Name.

    Returns:
        str: Der extrahierte Nachname.
    """
    if not name_str or name_str == "(No Sender)" or name_str == "(No Receiver)":
        return "Unknown"

    # Entferne E-Mail Adresse in Klammern falls vorhanden
    name_str = name_str.split('<')[0].strip()

    if ',' in name_str:
        # Format: Lastname, Firstname
        return name_str.split(',')[0].strip()
    else:
        # Format: Firstname Lastname
        parts = name_str.split()
        if parts:
            return parts[-1]
    return "Unknown"

def find_student_folder(base_path: Path, lastname: str) -> Optional[Path]:
    """Sucht nach einem existierenden Studierendenordner in allen Semesterordnern.

    Args:
        base_path: Basisverzeichnis für die Suche.
        lastname: Nachname des Studenten.

    Returns:
        Optional[Path]: Pfad zum Ordner falls gefunden, sonst None.
    """
    if not base_path.exists():
        return None

    # Suche in allen Unterordnern (Semesterordnern)
    for semester_dir in base_path.iterdir():
        if semester_dir.is_dir():
            student_dir = semester_dir / lastname
            if student_dir.exists() and student_dir.is_dir():
                return student_dir
    return None

def process_emails(source_root: Path, classifier_model: Path, config: Dict[str, str]) -> List[Dict[str, Any]]:
    """Verarbeitet E-Mails in Inbox und Sent Items.

    Args:
        source_root: Quellverzeichnis mit den E-Mails.
        classifier_model: Pfad zum trainierten Modell.
        config: Konfiguration der Zielpfade.

    Returns:
        List[Dict[str, Any]]: Liste der verschobenen E-Mails.
    """
    classifier = EmailClassifier()
    classifier.load(classifier_model)
    parser = MailParser()

    moved_emails = []

    # Die beiden Ordner, die verarbeitet werden sollen
    folders_to_process = ["Inbox", "SentItems"]

    for folder_name in folders_to_process:
        folder_path = source_root / folder_name
        if not folder_path.exists():
            logger.warning(f"Ordner {folder_path} existiert nicht. Überspringe.")
            continue

        logger.info(f"Verarbeite Ordner: {folder_name}")

        for msg_file in folder_path.glob("*.msg"):
            try:
                # Klassifizierung
                prediction = classifier.predict(msg_file)
                email_class = prediction["prediction"]

                if email_class not in config:
                    logger.warning(f"Keine Pfad-Konfiguration für Klasse '{email_class}' gefunden. Überspringe {msg_file.name}")
                    continue

                class_base_path = Path(config[email_class])

                # Datum und Semester
                date = parser.get_email_date(msg_file)
                semester = get_semester(date)

                # Name extrahieren
                lastname = "Unknown"
                import extract_msg
                with extract_msg.openMsg(str(msg_file)) as msg:
                    if folder_name == "Inbox":
                        lastname = extract_lastname(msg.sender)
                    else:
                        # Bei Sent Items den ersten Empfänger nehmen
                        recipients = msg.recipients
                        if recipients:
                            lastname = extract_lastname(recipients[0].name or recipients[0].email)

                # Ziel-Studentenordner finden oder bestimmen
                student_dir = find_student_folder(class_base_path, lastname)
                if not student_dir:
                    student_dir = class_base_path / semester / lastname

                # Endgültiger Zielordner
                target_dir = student_dir / folder_name
                target_dir.mkdir(parents=True, exist_ok=True)

                target_path = target_dir / msg_file.name

                # Datei verschieben
                shutil.move(str(msg_file), str(target_path))
                logger.info(f"Verschoben: {msg_file.name} -> {target_path}")

                moved_emails.append({
                    "class": email_class,
                    "semester": semester,
                    "lastname": lastname,
                    "folder": folder_name,
                    "path": str(target_path)
                })

            except Exception as e:
                logger.error(f"Fehler beim Verarbeiten von {msg_file}: {e}")

    return moved_emails

def write_report(source_root: Path, moved_emails: List[Dict[str, Any]]) -> None:
    """Erstellt den Markdown-Report.

    Args:
        source_root: Quellverzeichnis für den Report.
        moved_emails: Liste der verschobenen E-Mails.
    """
    if not moved_emails:
        logger.info("Keine E-Mails verschoben. Erstelle keinen Report.")
        return

    # Sortierung: Klasse, Semester, Nachname, Folder
    moved_emails.sort(key=lambda x: (x["class"], x["semester"], x["lastname"], x["folder"]))

    report_path = source_root / "sorted_emails.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Sortierte E-Mails\n\n")

        current_class = None
        for email in moved_emails:
            if email["class"] != current_class:
                current_class = email["class"]
                f.write(f"\n## {current_class}\n")

            f.write(f"- **{email['semester']}** | {email['lastname']} | {email['folder']}: `{email['path']}`\n")

    logger.info(f"Report erstellt: {report_path}")

def main() -> None:
    """Haupteinstiegspunkt für das Skript."""
    parser = argparse.ArgumentParser(description="Sortiert E-Mails basierend auf Klassifizierung.")
    parser.add_argument("source_dir", type=str, help="Quellordner mit Inbox und SentItems.")
    parser.add_argument("--config", type=str, required=True, help="Pfad zur YAML-Konfiguration (Klassen-Pfade).")
    parser.add_argument("--model", type=str, default="data/email_classifier.pkl", help="Pfad zum trainierten Modell.")

    args = parser.parse_args()

    source_root = Path(args.source_dir)
    if not source_root.exists():
        logger.error(f"Quellverzeichnis {args.source_dir} existiert nicht.")
        return

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Konfiguration {args.config} existiert nicht.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Falls die Konfiguration geschachtelt ist (z.B. unter einem 'class_paths' Key)
    if config and "class_paths" in config:
        config = config["class_paths"]

    moved_emails = process_emails(source_root, Path(args.model), config)
    write_report(source_root, moved_emails)

if __name__ == "__main__":
    main()
