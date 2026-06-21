"""Skript zum Sortieren von E-Mails basierend auf Klassifizierung."""
import argparse
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mcp_university.classifier.engine import EmailClassifier
from mcp_university.parser.mail_parser import MailParser
from mcp_university.config import get_config
from mcp_university.utils.encoding import decode_mime_header
from mcp_university.utils.semester import get_semester, normalize_name

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def extract_firstname(name_str: str) -> str:
    """Extrahiert den Vornamen aus einem Namensstring oder einer E-Mail-Adresse.

    Unterstützt das Format vorname.nachname@(smail.)th-koeln.de
    sowie 'Max Mustermann' oder 'Mustermann, Max'.

    Args:
        name_str: Der zu parsende Name oder die E-Mail-Adresse.

    Returns:
        str: Der extrahierte Vorname.
    """
    if not name_str or name_str == "(No Sender)" or name_str == "(No Receiver)":
        return "Unknown"

    # Suche nach E-Mail-Adresse
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_str)
    if email_match:
        email = email_match.group(0)
        if email.lower().endswith(("@smail.th-koeln.de", "@smail.fh-koeln.de", "@th-koeln.de", "@fh-koeln.de")):
            local_part = email.split("@")[0]
            if "." in local_part:
                return local_part.split(".")[0].capitalize()

    # Fallback für Namen ohne (Smail-)Adresse
    clean_name = name_str.split("<")[0].strip()

    if "," in clean_name:
        # Format: Lastname, Firstname
        parts = clean_name.split(",")
        if len(parts) > 1:
            res = parts[1].strip().split()[0]
            return res.strip("'\"")
    else:
        # Format: Firstname Lastname
        parts = clean_name.split()
        if parts:
            res = parts[0]
            return res.strip("'\"")

    return "Unknown"


def extract_firstname_simple(name_str: str) -> str:
    """Alternative, vereinfachte Extraktion des Vornamens.

    Args:
        name_str (str): Der zu parsende Name oder die E-Mail-Adresse.

    Returns:
        str: Der extrahierte Vorname.
    """
    if not name_str:
        return "Unknown"
    display_name = decode_mime_header(name_str).split("<")[0].strip()
    if "," in display_name:
        parts = display_name.split(",")
        if len(parts) > 1:
            return parts[1].strip()
    elif " " in display_name:
        return display_name.split()[0].strip()
    return "Unknown"


def extract_lastname(name_str: str) -> str:
    """Extrahiert den Nachnamen aus einem Namensstring oder einer E-Mail-Adresse.

    Folgt den spezifischen Regeln: Mailadresse bei "@" trennen.
    Falls "." im lokalen Teil vorhanden, dann ist Nachname nach dem ersten ".".
    Falls kein "." vorhanden, dann alles vor dem "@".
    Doppelnamen bei "_" oder "." werden getrennt, Teile groß geschrieben und mit "_" verbunden.
    Normalisiert Umlaute. Priorisiert Display-Namen wenn die E-Mail keinen Punkt enthält.

    Args:
        name_str (str): Der zu parsende Name oder die E-Mail-Adresse.

    Returns:
        str: Der extrahierte Nachname.
    """
    logger.debug(f"Extrahiere Nachname aus: {name_str}")
    if not name_str or name_str == "(No Sender)" or name_str == "(No Receiver)":
        return "Unknown"

    # Suche nach E-Mail-Adresse
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_str)

    # Extrahiere Anzeige-Namen (alles vor der ersten <)
    display_name = decode_mime_header(name_str).split("<")[0].strip()

    if email_match:
        email = email_match.group(0)
        local_part = email.split("@")[0]

        # Falls Punkt im lokalen Teil: Immer diese Regel anwenden (z.B. vorname.nachname)
        if "." in local_part:
            lastname_part = local_part.split(".", 1)[1]
            logger.debug(f"Punkt im lokalen Teil gefunden: {local_part} -> Extrahiere {lastname_part}")
            parts = re.split(r'[._]', lastname_part)
            res = "_".join(p[0].upper() + p[1:] for p in parts if p)
            return normalize_name(res)

        # Falls kein Punkt im lokalen Teil, aber wir haben einen validen Anzeige-Namen
        # (mit Leerzeichen oder Komma), dann ist dieser meist besser als die Mail-Adresse.
        if display_name and (" " in display_name or "," in display_name):
            pass # Weiter zum Display name parsing
        else:
            # Ansonsten Regel: Alles vor dem @
            lastname_part = local_part
            parts = re.split(r'[._]', lastname_part)
            res = "_".join(p[0].upper() + p[1:] for p in parts if p)
            return normalize_name(res)

    # Display name parsing (Fallback oder wenn Mail-Adresse unergiebig)
    if display_name:
        if "," in display_name:
            # Format: Lastname, Firstname
            res = display_name.split(",")[0].strip()
            return normalize_name(res)
        elif " " in display_name:
            # Format: Firstname Lastname
            parts = display_name.split()
            res = parts[-1].strip()
            return normalize_name(res)
        else:
            # Nur ein Wort
            return normalize_name(display_name)

    return "Unknown"


def find_student_folder(base_path: Path, lastname: str) -> Optional[Path]:
    """Sucht nach einem existierenden Studierendenordner in allen Semesterordnern.

    Args:
        base_path (Path): Basisverzeichnis für die Suche.
        lastname (str): Nachname des Studenten.

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


def process_emails(
    source_root: Path, classifier_model: Path, config: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Verarbeitet E-Mails und sortiert sie basierend auf Absender/Empfänger.

    Args:
        source_root (Path): Quellverzeichnis mit den E-Mails.
        classifier_model (Path): Pfad zum trainierten Modell.
        config (Dict[str, str]): Konfiguration der Zielpfade.

    Returns:
        List[Dict[str, Any]]: Liste der verschobenen E-Mails.
    """
    classifier = EmailClassifier()
    classifier.load(classifier_model)
    parser = MailParser()

    moved_emails = []

    logger.info(f"Beginne E-Mail-Sortierung in: {source_root}")

    for msg_file in sorted(source_root.rglob("*.msg")):
        try:
            # Klassifizierung
            logger.debug(f"Klassifiziere {msg_file.name}...")
            prediction = classifier.predict(msg_file)
            email_class = prediction["prediction"]

            if email_class not in config:
                logger.warning(
                    f"Keine Pfad-Konfiguration für Klasse '{email_class}' gefunden. Überspringe {msg_file.name}"
                )
                continue

            class_base_path = Path(config[email_class])

            # Datum und Semester
            date = parser.get_email_date(msg_file)
            semester = get_semester(date)

            # Sender/Receiver und Ziel-Ordner bestimmen
            lastname = "Unknown"
            target_folder = "Inbox"  # Default

            import extract_msg

            with extract_msg.openMsg(str(msg_file)) as msg:
                sender = (msg.sender.lower() if msg.sender else "").strip()
                logger.debug(f"Analysiere Sender/Empfänger für {msg_file.name} (Klasse: {email_class}, Sender: {sender})")

                if any(e.lower() in sender for e in get_config().user.emails):
                    target_folder = "SentItems"
                    # Suche in Empfängern nach Student
                    recipients = msg.recipients
                    if recipients:
                        found_student = False
                        for rec in recipients:
                            rec_email = (rec.email or "").lower()
                            is_user = any(e.lower() in rec_email for e in get_config().user.emails)
                            if not is_user and any(domain in rec_email for domain in ["@smail.th-koeln.de", "@smail.fh-koeln.de", "@th-koeln.de", "@fh-koeln.de"]):
                                logger.debug(f"Student in Empfängern gefunden: {rec_email}")
                                lastname = extract_lastname(rec.name or rec.email)
                                found_student = True
                                break
                        if not found_student:
                            # Fallback falls kein Student in Empfängern
                            lastname = extract_lastname(recipients[0].name or recipients[0].email)
                elif any(domain in sender for domain in ["@smail.th-koeln.de", "@smail.fh-koeln.de", "@th-koeln.de", "@fh-koeln.de"]):
                    target_folder = "Inbox"
                    lastname = extract_lastname(msg.sender)
                else:
                    # Fallback falls weder noch
                    # Versuche Student in Sender oder Empfängern zu finden
                    recipients = msg.recipients
                    found_student = False
                    if recipients:
                        for rec in recipients:
                            rec_email = (rec.email or "").lower()
                            is_user = any(e.lower() in rec_email for e in get_config().user.emails)
                            if not is_user and any(domain in rec_email for domain in ["@smail.th-koeln.de", "@smail.fh-koeln.de", "@th-koeln.de", "@fh-koeln.de"]):
                                logger.debug(f"Student in Empfängern gefunden (Fallback): {rec_email}")
                                target_folder = "Inbox"
                                lastname = extract_lastname(rec.name or rec.email)
                                found_student = True
                                break

                    if not found_student:
                         # Wenn immer noch nichts, bleibe bei Inbox und versuche Sender
                         target_folder = "Inbox"
                         lastname = extract_lastname(msg.sender)

            # Ziel-Pfad bestimmen
            logger.debug(f"Bestimme Ziel-Pfad für {lastname} in {target_folder} (Semester: {semester})")
            student_dir = find_student_folder(class_base_path, lastname)
            if not student_dir:
                student_dir = class_base_path / semester / lastname
            target_dir = student_dir / target_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / msg_file.name

            # Datei verschieben
            shutil.move(str(msg_file), str(target_path))
            logger.info(f"Verschoben: {msg_file.name} -> {target_path}")

            moved_emails.append(
                {
                    "class": email_class,
                    "semester": semester,
                    "lastname": lastname,
                    "folder": target_folder,
                    "path": str(target_path),
                }
            )

        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von {msg_file}: {e}")

    return moved_emails


def write_report(source_root: Path, moved_emails: List[Dict[str, Any]]) -> None:
    """Erstellt den Markdown-Report.

    Args:
        source_root (Path): Quellverzeichnis für den Report.
        moved_emails (List[Dict[str, Any]]): Liste der verschobenen E-Mails.
    """
    if not moved_emails:
        logger.info("Keine E-Mails verschoben. Erstelle keinen Report.")
        return

    # Sortierung: Klasse, Semester, Nachname, Folder
    moved_emails.sort(
        key=lambda x: (x["class"], x["semester"], x["lastname"], x["folder"])
    )

    report_path = source_root / "sorted_emails.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Sortierte E-Mails\n\n")

        current_class = None
        for email in moved_emails:
            if email["class"] != current_class:
                current_class = email["class"]
                f.write(f"\n## {current_class}\n")

            f.write(
                f"- **{email['semester']}** | {email['lastname']} | {email['folder']}: `{email['path']}`\n"
            )

    logger.info(f"Report erstellt: {report_path}")


def main() -> None:
    """Haupteinstiegspunkt für das Skript."""
    parser = argparse.ArgumentParser(
        description="Sortiert E-Mails basierend auf Klassifizierung."
    )
    parser.add_argument(
        "source_dir", type=str, help="Quellordner mit E-Mails."
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Pfad zur YAML-Konfiguration (Klassen-Pfade).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="data/email_classifier.pkl",
        help="Pfad zum trainierten Modell.",
    )

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
