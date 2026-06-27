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


def clean_sender_name(name_str: str) -> str:
    """Bereinigt den Absendernamen von komplexen Headern wie 'im Auftrag von'.

    Args:
        name_str: Der zu bereinigende Namensstring.

    Returns:
        str: Der bereinigte Name.
    """
    if "im Auftrag von" in name_str:
        # Versuche einen echten Namen nach "im Auftrag von;" zu finden
        parts = name_str.split("im Auftrag von;")
        if len(parts) > 1:
            return parts[1].split("<")[0].strip()
        else:
            # Fallback für andere Varianten
            match = re.search(r"im Auftrag von\s*[:;]?\s*([^<]+)", name_str)
            if match:
                return match.group(1).strip()
    return name_str


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

    name_str = clean_sender_name(name_str)

    # Suche nach E-Mail-Adresse
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_str)
    email = email_match.group(0) if email_match else ""

    # Handle display name first if available
    display_name = decode_mime_header(name_str).split("<")[0].strip()
    if display_name == email:
        display_name = ""
    # Remove parentheses like (aspass)
    display_name = re.sub(r"\([^)]*\)", "", display_name).strip()
    # Remove titles and suffixes
    display_name = re.sub(r",?\s*(B\.Sc\.|M\.Sc\.|Prof\.|Dr\.)\s*", "", display_name).strip()

    # Priority 1: "Rich" display name
    if display_name and (" " in display_name or "," in display_name):
        if "," in display_name:
            parts = display_name.split(",")
            if len(parts) > 1:
                return parts[1].strip().split()[0].strip("'\"")
        else:
            parts = display_name.split()
            if len(parts) > 1:
                return " ".join(parts[:-1]).strip("'\"")

    # Priority 2: Email address with dot
    if email:
        if email.lower().endswith(("@smail.th-koeln.de", "@smail.fh-koeln.de", "@th-koeln.de", "@fh-koeln.de")):
            local_part = email.split("@")[0]
            if "." in local_part:
                firstname_part = local_part.split(".")[0]
                # Replace _ with space and capitalize
                parts = re.split(r'([_-])', firstname_part)
                res = ""
                for p in parts:
                    if p in ["_", "-"]:
                        res += " " if p == "_" else "-"
                    else:
                        if p:
                            res += p[0].upper() + p[1:]
                return res

    # Priority 3: Any display name
    if display_name:
        return display_name

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

    name_str = clean_sender_name(name_str)

    # Suche nach E-Mail-Adresse
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_str)
    email = email_match.group(0) if email_match else ""

    # Extrahiere Anzeige-Namen (alles vor der ersten <)
    display_name = decode_mime_header(name_str).split("<")[0].strip()
    if display_name == email:
        display_name = ""
    # Remove parentheses like (aspass)
    display_name = re.sub(r"\([^)]*\)", "", display_name).strip()
    # Remove titles
    display_name = re.sub(r",?\s*(B\.Sc\.|M\.Sc\.|Prof\.|Dr\.)\s*", "", display_name).strip()

    # Priority 1: "Rich" display name (more than one word or has comma)
    if display_name and (" " in display_name or "," in display_name):
        if "," in display_name:
            # Format: Lastname, Firstname
            return display_name.split(",")[0].strip()
        else:
            # Format: Firstname Lastname
            parts = display_name.split()
            if len(parts) > 1:
                return " ".join(parts[1:])
            return display_name

    # Priority 2: Email with dot in local part
    if email:
        local_part = email.split("@")[0]
        if "." in local_part:
            lastname_part = local_part.split(".", 1)[1]
            logger.debug(f"Punkt im lokalen Teil gefunden: {local_part} -> Extrahiere {lastname_part}")
            parts = re.split(r'([._])', lastname_part)
            res = ""
            for p in parts:
                if p == "_":
                    res += " "
                elif p == ".":
                    res += " "
                else:
                    if p:
                        if "-" in p:
                            subparts = p.split("-")
                            res += "-".join(sp[0].upper() + sp[1:] for sp in subparts if sp)
                        else:
                            res += p[0].upper() + p[1:]
            return res

    # Priority 3: System addresses or simple names
    if display_name:
        return display_name

    if email:
        local_part = email.split("@")[0]
        if "@th-koeln.de" in email.lower() and "-" in local_part:
            return local_part
        parts = re.split(r'([._-])', local_part)
        res = ""
        for p in parts:
            if p in ["_", ".", "-"]:
                res += p
            else:
                res += p[0].upper() + p[1:] if p else ""
        return res

    return "Unknown"


def find_student_folder(base_path: Path, lastname: str) -> Optional[Path]:
    """Sucht nach dem Ordner eines Studenten basierend auf dem Nachnamen.

    Sucht rekursiv in den Semester-Unterordnern.

    Args:
        base_path (Path): Das Basisverzeichnis (z.B. 'BachelorThesis').
        lastname (str): Der Nachname des Studenten.

    Returns:
        Optional[Path]: Der Pfad zum Studentenordner oder None, falls nicht gefunden.
    """
    # Normalisiere den Such-Nachnamen für den Vergleich
    search_name = normalize_name(lastname).lower()

    if not base_path.exists():
        return None

    # Suche in allen Unterordnern (Semester)
    for semester_dir in base_path.iterdir():
        if semester_dir.is_dir():
            for student_dir in semester_dir.iterdir():
                if student_dir.is_dir():
                    if normalize_name(student_dir.name).lower() == search_name:
                        return student_dir
    return None


def process_emails(
    source_root: Path, classifier_model_path: Path, config: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Verarbeitet E-Mails aus dem Quellverzeichnis.

    Args:
        source_root (Path): Verzeichnis mit den zu sortierenden .msg-Dateien.
        classifier_model_path (Path): Pfad zum trainierten Klassifizierer-Modell.
        config (Dict[str, str]): Pfad-Konfiguration für die Klassen.

    Returns:
        List[Dict[str, Any]]: Liste der verschobenen E-Mails mit Metadaten.
    """
    moved_emails = []
    classifier = EmailClassifier()
    classifier.load(classifier_model_path)
    parser = MailParser()
    uni_config = get_config()
    user_emails = [email.lower() for email in uni_config.user.emails]
    student_domains = ["@smail.th-koeln.de", "@smail.fh-koeln.de"]

    def is_student(email_addr: str) -> bool:
        """Prüft ob eine E-Mail-Adresse zu einem Studenten gehört.

        Args:
            email_addr: Die zu prüfende E-Mail-Adresse.

        Returns:
            bool: True wenn es eine Studenten-E-Mail ist, sonst False.
        """
        email_addr = email_addr.lower()
        if any(u_email in email_addr for u_email in user_emails):
            return False
        return any(domain in email_addr for domain in student_domains)

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

                is_sent_by_user = any(u_email in sender for u_email in user_emails)
                recipients = msg.recipients or []

                if is_sent_by_user:
                    target_folder = "SentItems"
                    # Rule: Prioritize direct recipients (To) for folder naming, ignore CC
                    # Rule: Take first 'To' recipient, fallback to second if first fails
                    to_recipients = [r for r in recipients if getattr(r, "type", None) == 1]

                    if to_recipients:
                        lastname = extract_lastname(to_recipients[0].name or to_recipients[0].email)
                        if lastname == "Unknown" and len(to_recipients) > 1:
                            lastname = extract_lastname(to_recipients[1].name or to_recipients[1].email)
                    else:
                        # Fallback to any recipient
                        if recipients:
                            lastname = extract_lastname(recipients[0].name or recipients[0].email)
                        else:
                            lastname = "Unknown"
                else:
                    target_folder = "Inbox"
                    # Rule: Folder name should be the sender's lastname
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
                f.write(f"## {current_class}\n\n")
                f.write("| Semester | Nachname | Ordner | Datei |\n")
                f.write("| --- | --- | --- | --- |\n")

            f.write(
                f"| {email['semester']} | {email['lastname']} | {email['folder']} | {Path(email['path']).name} |\n"
            )

    logger.info(f"Report erstellt: {report_path}")


def main():
    """Hauptfunktion des Skripts."""
    parser = argparse.ArgumentParser(description="Sortiert E-Mails basierend auf Klassifizierung.")
    parser.add_argument("source_dir", type=str, help="Quellverzeichnis mit E-Mails.")
    parser.add_argument("--model", type=str, required=True, help="Pfad zum Klassifizierer-Modell.")
    parser.add_argument("--config", type=str, required=True, help="Pfad zur YAML-Konfiguration.")
    args = parser.parse_args()

    source_path = Path(args.source_dir)
    model_path = Path(args.model)
    config_path = Path(args.config)

    if not source_path.exists():
        logger.error(f"Quellverzeichnis {source_path} existiert nicht.")
        return

    if not config_path.exists():
        logger.error(f"Konfigurationsdatei {config_path} existiert nicht.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        full_config = yaml.safe_load(f)

    # Handle nested config if present
    path_config = full_config.get("class_paths", full_config)

    moved_emails = process_emails(source_path, model_path, path_config)
    write_report(source_path, moved_emails)


if __name__ == "__main__":
    main()
