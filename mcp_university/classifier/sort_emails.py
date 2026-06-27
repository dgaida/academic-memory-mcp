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

# Liste generischer Email-Local-Parts, die nicht als Name verwendet werden sollten.
GENERIC_LOCAL_PARTS = [
    "student", "onbehalfof", "no-reply", "support", "info",
    "admin", "office", "sekretariat", "onbehalf"
]

def clean_sender_name(name_str: str) -> str:
    """Bereinigt den Absendernamen von komplexen Headern wie 'im Auftrag von'.

    Args:
        name_str (str): Der zu bereinigende Namensstring.

    Returns:
        str: Der bereinigte Name.
    """
    if not name_str:
        return ""

    # MIME-Header dekodieren falls nötig
    name_str = decode_mime_header(name_str)

    if "im Auftrag von" in name_str:
        # Versuche einen echten Namen nach "im Auftrag von;" zu finden
        parts = name_str.split("im Auftrag von;")
        if len(parts) > 1:
            name_str = parts[1].split("<")[0].strip()
        else:
            # Fallback für andere Varianten
            match = re.search(r"im Auftrag von\s*[:;]?\s*([^<]+)", name_str)
            if match:
                name_str = match.group(1).strip()

    # Handle spezifisches Präfix "TH //"
    name_str = re.sub(r"^TH\s*//\s*", "", name_str)
    return name_str.strip("'\" ")


def extract_firstname(name_str: str) -> str:
    """Extrahiert den Vornamen aus einem Namensstring oder einer E-Mail-Adresse.

    Args:
        name_str (str): Der zu parsende Name oder die E-Mail-Adresse.

    Returns:
        str: Der extrahierte Vorname.
    """
    if not name_str or name_str in ["(No Sender)", "(No Receiver)", "Unknown"]:
        return "Unknown"

    name_str = clean_sender_name(name_str)

    # Suche nach E-Mail-Adresse
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_str)
    email_address = email_match.group(0) if email_match else ""

    # Anzeige-Name extrahieren
    display_name = name_str.split("<")[0].strip()
    if display_name == email_address:
        display_name = ""

    # Klammern und Titel entfernen
    display_name = re.sub(r"\(.*?\)", "", display_name).strip()
    display_name = re.sub(r",?\s*(B\.Sc\.|M\.Sc\.|Prof\.|Dr\.)\s*", "", display_name).strip()

    # Priorität 1: Reicher Anzeigename (mehrere Wörter oder Komma)
    if display_name and (" " in display_name or "," in display_name):
        if "," in display_name:
            parts = display_name.split(",")
            if len(parts) > 1:
                return parts[1].strip().split()[0].strip("'\"")
        else:
            parts = display_name.split()
            if len(parts) > 1:
                return " ".join(parts[:-1]).strip("'\"")

    # Priorität 2: E-Mail-Adresse mit Punkt im Local-Part (Hochschul-Format)
    if email_address and any(domain in email_address.lower() for domain in ["th-koeln.de", "fh-koeln.de"]):
        local_part = email_address.split("@")[0]
        if "." in local_part:
            firstname_part = local_part.split(".")[0]
            # Ersetze _ durch Leerzeichen und Großschreibung
            parts = re.split(r'([_-])', firstname_part)
            result_name = ""
            for part in parts:
                if part in ["_", "-"]:
                    result_name += " " if part == "_" else "-"
                else:
                    if part:
                        result_name += part[0].upper() + part[1:]
            return result_name

    # Priorität 3: Fallback auf Anzeigename
    if display_name:
        return display_name

    return "Unknown"

def _clean_for_comparison(string_value: str) -> str:
    """Hilfsfunktion für den normalisierten Vergleich von Namensteilen.

    Args:
        string_value: Der zu säubernde String.

    Returns:
        str: Gesäuberter String.
    """
    return string_value.lower().replace("ß", "ss").replace("_", "").replace(".", "").replace("-", "").strip()


def extract_lastname(name_str: str) -> str:
    """Extrahiert den Nachnamen aus einem Namensstring oder einer E-Mail-Adresse.

    Args:
        name_str (str): Der zu parsende Name oder die E-Mail-Adresse.

    Returns:
        str: Der extrahierte Nachname.
    """
    logger.debug(f"Extrahiere Nachname aus: {name_str}")
    if not name_str or name_str in ["(No Sender)", "(No Receiver)", "Unknown"]:
        return "Unknown"

    name_str = clean_sender_name(name_str)

    # Email und Local-Part extrahieren
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_str)
    email_address = email_match.group(0) if email_match else ""
    local_part = email_address.split("@")[0] if email_address else ""

    # Anzeige-Namen extrahieren und bereinigen
    display_name = name_str.split("<")[0].strip()
    if display_name == email_address:
        display_name = ""
    display_name = display_name.strip("'\" ")
    display_name = re.sub(r"\(.*?\)", "", display_name).strip()
    display_name = re.sub(r",?\s*(B\.Sc\.|M\.Sc\.|Prof\.|Dr\.)\s*", "", display_name).strip()
    display_name = re.sub(r"\s*\|\s*.*$", "", display_name)
    display_name = re.sub(r"\s+GmbH\b.*$", "", display_name).strip("'\" ")

    # 1. Systemadressen (Priority 1)
    if local_part:
        local_part_lower = local_part.lower()
        if "digital-science" in local_part_lower:
            return "Digital-science"
        if "kreditorenbuchhaltung" in local_part_lower:
            return "Kreditorenbuchhaltung"

    # 2. Greedy Display Name Match gegen den LETZTEN Teil des Local-Parts (Case: A B C D -> C D)
    if display_name and local_part and _clean_for_comparison(local_part) not in GENERIC_LOCAL_PARTS:
        # Wir nehmen den Teil nach dem Punkt als wahrscheinlichen Nachnamen-Teil in der Email
        local_part_lastname_segment = local_part.split(".")[-1]
        local_part_segment_normalized = _clean_for_comparison(local_part_lastname_segment)

        # Falls Komma vorhanden, nur den Teil davor betrachten
        potential_lastname_source = display_name.split(",")[-1].strip() if "," in display_name else display_name
        words = potential_lastname_source.split()

        matching_words = []
        for word in reversed(words):
            word_normalized = _clean_for_comparison(word)
            if word_normalized and word_normalized in local_part_segment_normalized:
                matching_words.insert(0, word)
            else:
                break
        if matching_words:
            return " ".join(matching_words)

    # 3. Email mit Punkt im Local-Part (vorname.nachname)
    if local_part and "." in local_part:
        lastname_part = local_part.rsplit(".", 1)[1]
        parts = re.split(r'([._])', lastname_part)
        result_lastname = ""
        for part in parts:
            if part in ["_", "."]:
                result_lastname += " "
            elif part:
                if "-" in part:
                    subparts = part.split("-")
                    result_lastname += "-".join(sub[0].upper() + sub[1:] for sub in subparts if sub)
                else:
                    result_lastname += part[0].upper() + part[1:]
        if result_lastname.strip():
            return result_lastname.strip()

    # 4. Validierung des identifizierten Nachnamens gegen Local-Part
    # Falls der Name aus dem Display-Name nicht in der Email vorkommt -> Local Part nutzen (Case: Wester Helmut -> HWester)
    display_words = display_name.split()
    standard_lastname = display_words[-1] if display_words else ""
    if "," in display_name:
        standard_lastname = display_name.split(",")[0].strip()

    if standard_lastname and local_part:
        if _clean_for_comparison(standard_lastname) not in _clean_for_comparison(local_part):
            if _clean_for_comparison(local_part) not in GENERIC_LOCAL_PARTS:
                # Falls Local-Part Großbuchstaben hat, diese bevorzugen (z.B. HWester)
                if any(character.isupper() for character in local_part):
                    return local_part
                # Falls Bindestriche vorhanden sind (z.B. praxissemester-inf)
                if "-" in local_part and any(domain in (email_address or "").lower() for domain in ["th-koeln.de", "fh-koeln.de"]):
                    return "-".join(part[0].upper() + part[1:] for part in local_part.split("-") if part)
                return local_part[0].upper() + local_part[1:] if local_part else "Unknown"

    # 5. Generische Fallbacks
    if "," in display_name:
        return display_name.split(",")[0].strip()
    if display_name:
        parts = display_name.split()
        if len(parts) > 1:
            return parts[-1]
        return display_name
    if local_part:
        if any(character.isupper() for character in local_part):
            return local_part
        return local_part[0].upper() + local_part[1:]

    return "Unknown"


def find_student_folder(base_path: Path, lastname: str) -> Optional[Path]:
    """Sucht nach dem Ordner eines Studenten basierend auf dem Nachnamen.

    Args:
        base_path (Path): Das Basisverzeichnis.
        lastname (str): Der Nachname des Studenten.

    Returns:
        Optional[Path]: Der Pfad zum Studentenordner oder None.
    """
    search_name_normalized = normalize_name(lastname).lower()
    if not base_path.exists():
        return None
    for semester_dir in base_path.iterdir():
        if semester_dir.is_dir():
            for student_dir in semester_dir.iterdir():
                if student_dir.is_dir():
                    if normalize_name(student_dir.name).lower() == search_name_normalized:
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
    moved_emails_list = []
    classifier = EmailClassifier()
    classifier.load(classifier_model_path)
    parser = MailParser()
    university_config = get_config()
    user_emails_list = [user_email.lower() for user_email in university_config.user.emails]

    for msg_file in sorted(source_root.rglob("*.msg")):
        try:
            # Klassifizierung
            prediction_result = classifier.predict(msg_file)
            email_class = prediction_result["prediction"]

            if email_class not in config:
                continue

            class_base_path = Path(config[email_class])
            email_date = parser.get_email_date(msg_file)
            semester_name = get_semester(email_date)
            extracted_lastname = "Unknown"
            target_subfolder = "Inbox"

            import extract_msg
            with extract_msg.openMsg(str(msg_file)) as message_object:
                sender_display_name = getattr(message_object, "sender", "")
                if not isinstance(sender_display_name, str):
                    sender_display_name = str(sender_display_name)

                # Robuste E-Mail-Extraktion für den Vergleich
                extracted_sender_email = ""
                sender_email_attribute = getattr(message_object, "sender_email", None)
                if isinstance(sender_email_attribute, str):
                    extracted_sender_email = sender_email_attribute.lower().strip()
                if not extracted_sender_email:
                    match_object = re.search(r"[\w\.-]+@[\w\.-]+", sender_display_name)
                    if match_object:
                        extracted_sender_email = match_object.group(0).lower()
                    else:
                        extracted_sender_email = sender_display_name.lower()

                is_sent_by_user = any(user_email in extracted_sender_email for user_email in user_emails_list)

                if is_sent_by_user:
                    target_subfolder = "SentItems"
                    recipients_list = message_object.recipients or []
                    to_recipients_list = [recipient for recipient in recipients_list if getattr(recipient, "type", None) == 1]
                    if to_recipients_list:
                        primary_recipient = to_recipients_list[0]
                        extracted_lastname = extract_lastname(f"{primary_recipient.name} <{primary_recipient.email}>" if primary_recipient.name and primary_recipient.email else (primary_recipient.name or primary_recipient.email))
                        if (not extracted_lastname or extracted_lastname == "Unknown") and len(to_recipients_list) > 1:
                            secondary_recipient = to_recipients_list[1]
                            extracted_lastname = extract_lastname(f"{secondary_recipient.name} <{secondary_recipient.email}>" if secondary_recipient.name and secondary_recipient.email else (secondary_recipient.name or secondary_recipient.email))
                    elif recipients_list:
                        any_recipient = recipients_list[0]
                        extracted_lastname = extract_lastname(f"{any_recipient.name} <{any_recipient.email}>" if any_recipient.name and any_recipient.email else (any_recipient.name or any_recipient.email))
                else:
                    target_subfolder = "Inbox"
                    extracted_lastname = extract_lastname(sender_display_name)

            student_directory_path = find_student_folder(class_base_path, extracted_lastname)
            if not student_directory_path:
                student_directory_path = class_base_path / semester_name / extracted_lastname

            target_directory = student_directory_path / target_subfolder
            target_directory.mkdir(parents=True, exist_ok=True)
            final_target_path = target_directory / msg_file.name
            shutil.move(str(msg_file), str(final_target_path))

            moved_emails_list.append({
                "class": email_class,
                "semester": semester_name,
                "lastname": extracted_lastname,
                "folder": target_subfolder,
                "path": str(final_target_path)
            })
        except Exception as error_instance:
            logger.error(f"Fehler bei Verarbeitung von {msg_file}: {error_instance}")

    return moved_emails_list


def write_report(source_root: Path, moved_emails_list: List[Dict[str, Any]]) -> None:
    """Erstellt den Markdown-Report über die verschobenen E-Mails.

    Args:
        source_root (Path): Quellverzeichnis für den Report.
        moved_emails_list (List[Dict[str, Any]]): Liste der verschobenen E-Mails.
    """
    if not moved_emails_list:
        return

    moved_emails_list.sort(key=lambda item: (item["class"], item["semester"], item["lastname"], item["folder"]))
    report_file_path = source_root / "sorted_emails.md"

    with open(report_file_path, "w", encoding="utf-8") as report_file:
        report_file.write("# Sortierte E-Mails\n\n")
        current_email_class = None
        for email_item in moved_emails_list:
            if email_item["class"] != current_email_class:
                current_email_class = email_item["class"]
                report_file.write(f"## {current_email_class}\n\n")
                report_file.write("| Semester | Nachname | Ordner | Datei |\n")
                report_file.write("| --- | --- | --- | --- |\n")
            report_file.write(f"| {email_item['semester']} | {email_item['lastname']} | {email_item['folder']} | {Path(email_item['path']).name} |\n")


def main() -> None:
    """Hauptfunktion des Skripts zum Sortieren von E-Mails basierend auf Klassifizierung."""
    parser_object = argparse.ArgumentParser(description="Sortiert E-Mails basierend auf Klassifizierung.")

    parser_object.add_argument(
        "source_dir",
        help="Quellverzeichnis mit E-Mails."
    )
    parser_object.add_argument(
        "--model",
        required=True,
        help="Pfad zum Klassifizierer-Modell."
    )
    parser_object.add_argument(
        "--config",
        required=True,
        help="Pfad zur YAML-Konfiguration."
    )

    command_line_arguments = parser_object.parse_args()
    source_directory_path = Path(command_line_arguments.source_dir)

    with open(command_line_arguments.config, "r", encoding="utf-8") as config_file_handle:
        full_configuration_data = yaml.safe_load(config_file_handle)

    path_configuration = full_configuration_data.get("class_paths", full_configuration_data)

    processed_emails_result = process_emails(source_directory_path, Path(command_line_arguments.model), path_configuration)
    write_report(source_directory_path, processed_emails_result)

if __name__ == "__main__":
    main()
