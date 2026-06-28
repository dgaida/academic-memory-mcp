"""Modul zum Sortieren von E-Mails basierend auf Klassifizierung."""

import argparse
import logging
import shutil
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

from mcp_university.config import get_config
from mcp_university.utils.semester import get_semester
from mcp_university.parser.mail_parser import MailParser
from mcp_university.classifier.engine import EmailClassifier
from mcp_university.utils.torch_utils import get_device  # noqa: F401

logger = logging.getLogger(__name__)

# Liste von generischen Local-Parts, die ignoriert werden sollen
GENERIC_LOCAL_PARTS = {
    "info", "sekretariat", "service", "kontakt", "studium", "pruefungsamt",
    "international", "career", "bibliothek", "it-service", "beratung",
    "alumni", "marketing", "presse", "events", "support", "helpdesk"
}


def normalize_name(name: str) -> str:
    """Normalisiert einen Namen für den Vergleich (entfernt Sonderzeichen, Kleinschreibung).

    Args:
        name (str): Der zu normalisierende Name.

    Returns:
        str: Der normalisierte Name.
    """
    if not name:
        return ""
    # Entferne akademische Titel und Sonderzeichen
    name = re.sub(r"(Prof\.|Dr\.|B\.Sc\.|M\.Sc\.|Dipl\.-Ing\.)", "", name, flags=re.IGNORECASE)
    # Nur Buchstaben und Bindestriche behalten
    name = re.sub(r"[^a-zA-ZäöüÄÖÜß\-]", " ", name)
    return name.strip()


def _format_dashed_name(name: str) -> str:
    """Formatiert einen Namen mit Bindestrichen korrekt (Großschreibung nach Bindestrich)."""
    parts = name.split("-")
    return "-".join(p.capitalize() for p in parts if p)


def _clean_for_comparison(s: str) -> str:
    """Bereitet einen String für den Vergleich vor (Kleinschreibung, Trim)."""
    return s.strip().lower()


def extract_firstname(sender_raw: str) -> str:
    """Extrahiert den Vornamen aus einer Sender-Zeile.

    Args:
        sender_raw (str): Die rohe Sender-Information (z.B. 'Max Mustermann <max@example.com>').

    Returns:
        str: Der extrahierte Vorname oder 'Unknown'.
    """
    if not sender_raw or sender_raw == "(No Sender)":
        return "Unknown"

    display_name = ""
    local_part = ""

    # 1. Extraktion von Display-Name und Email
    match = re.match(r"^(.*?)\s*<([^>]+)>", sender_raw)
    if match:
        display_name = match.group(1).strip().strip("'").strip('"')
        email = match.group(2).strip()
        local_part = email.split("@")[0] if "@" in email else ""
    else:
        if "@" in sender_raw:
            local_part = sender_raw.split("@")[0]
        else:
            display_name = sender_raw.strip().strip("'").strip('"')

    # 2. Heuristik für Vornamen
    if "," in display_name:
        parts = display_name.split(",")
        if len(parts) > 1:
            return parts[1].strip().split()[0]

    if display_name:
        parts = display_name.split()
        if len(parts) > 1:
            return parts[0]

    if "." in local_part:
        parts = local_part.split(".")
        if len(parts) > 1:
            first = parts[0]
            if _clean_for_comparison(first) not in GENERIC_LOCAL_PARTS:
                return first.capitalize()

    return "Unknown"


def extract_lastname(sender_raw: str) -> str:
    """Extrahiert den Nachnamen aus einer Sender-Zeile.

    Hierarchische Extraktionslogik:
    1. Beachtet "im Auftrag von" Header.
    2. Greedy Name Matching: Abgleich von Display-Name Teilen gegen den Local-Part der Email.
       Wichtig: Falls ein Teil des Display-Namens im Local-Part vorkommt, wird dieser als Nachname bevorzugt.
       Dabei werden längere Matches (z.B. 'Mustermann') gegenüber kürzeren (z.B. 'Max') bevorzugt,
       wenn beide im Local-Part vorkommen (z.B. 'mustermann.max').
    3. Fallback auf dot-separated Local Part Segmente.
    4. Generische Fallbacks (Kommata-Separation, letztes Wort im Namen).

    Args:
        sender_raw (str): Die rohe Sender-Information.

    Returns:
        str: Der extrahierte Nachname (Title Case) oder 'Unknown'.
    """
    if not sender_raw or sender_raw == "(No Sender)":
        return "Unknown"

    display_name = ""
    local_part = ""

    # 1. "im Auftrag von" Logik (Priorisierung des eigentlichen Senders)
    if "im Auftrag von" in sender_raw:
        parts = sender_raw.split("im Auftrag von")
        sender_raw = parts[1].strip()

    # 2. Extraktion von Display-Name und Email
    match = re.match(r"^(.*?)\s*<([^>]+)>", sender_raw)
    if match:
        display_name = match.group(1).strip().strip("'").strip('"')
        email = match.group(2).strip()
        local_part = email.split("@")[0] if "@" in email else ""
    else:
        if "@" in sender_raw:
            local_part = sender_raw.split("@")[0]
        else:
            display_name = sender_raw.strip().strip("'").strip('"')

    # 3. Greedy Name Matching (Suche nach Namensteilen im Local-Part)
    # Behandelt Fälle wie 'Mustermann Max' -> 'Mustermann' im Local-Part 'mustermann.max'
    if display_name and local_part:
        # Bereinige Display-Name von Kommas für den Abgleich
        clean_display = display_name.replace(",", " ")
        name_parts = clean_display.split()
        if len(name_parts) > 1:
            # Suche nach dem Teil des Display-Namens, der im Local-Part vorkommt (ignorieren von '.' und '-')
            norm_local = normalize_name(local_part).lower().replace(".", "").replace("-", "")

            best_match = None
            best_match_len = -1

            for part in name_parts:
                norm_part = normalize_name(part).lower()
                if norm_part and norm_part in norm_local:
                    # Wir haben ein Match. Bevorzuge längere Namen (Nachnamen sind oft länger als Vornamen/Initialen)
                    # ODER wir nehmen einfach den, der im Local-Part an erster Stelle steht?
                    # Meistens ist die Struktur im Local-Part 'nachname.vorname' oder 'vorname.nachname'.
                    if len(norm_part) > best_match_len:
                        best_match = part
                        best_match_len = len(norm_part)

            if best_match:
                return _format_dashed_name(best_match) if "-" in best_match else best_match

    # 4. Dot-Separated Local Part Fallback (Priorität 2)
    if "." in local_part:
        parts = local_part.split(".")
        if len(parts) > 1:
            # Falls einer der Teile im dot-separated local part als Nachname identifiziert werden kann
            # (Nicht generisch)
            for part in reversed(parts):
                if _clean_for_comparison(part) not in GENERIC_LOCAL_PARTS:
                    # Falls Local-Part Großbuchstaben hat, diese als Bezeichner bevorzugen (z.B. HWester)
                    if any(character.isupper() for character in part):
                        return part
                    # Falls Bindestriche vorhanden sind (z.B. praxissemester-inf)
                    if "-" in part:
                        return _format_dashed_name(part)
                    return part[0].upper() + part[1:] if part else "Unknown"

    # 5. Generische Fallbacks (Priorität 3)
    if "," in display_name:
        return display_name.split(",")[0].strip()
    if display_name:
        parts = display_name.split()
        if len(parts) > 1:
            lastname_candidate = parts[-1]
            if "-" in lastname_candidate:
                return _format_dashed_name(lastname_candidate)
            return lastname_candidate
        return _format_dashed_name(display_name) if "-" in display_name else display_name
    if local_part:
        if any(character.isupper() for character in local_part):
            return local_part
        if "-" in local_part:
            return _format_dashed_name(local_part)
        return local_part[0].upper() + local_part[1:]
        
    return "Unknown"


def find_student_folder(base_directory: Path, lastname: str) -> Optional[Path]:
    """Sucht nach dem Ordner eines Studenten basierend auf dem Nachnamen.

    Sucht rekursiv in den Semester-Unterordnern nach einem passenden Verzeichnis.

    Args:
        base_directory (Path): Das Basisverzeichnis der jeweiligen Klasse.
        lastname (str): Der Nachname des Studenten.

    Returns:
        Optional[Path]: Der Pfad zum Studentenordner oder None, falls nicht gefunden.
    """
    search_name_normalized = normalize_name(lastname).lower()
    if not base_directory.exists():
        return None
    for semester_dir in base_directory.iterdir():
        if semester_dir.is_dir():
            for student_dir in semester_dir.iterdir():
                if student_dir.is_dir():
                    if normalize_name(student_dir.name).lower() == search_name_normalized:
                        return student_dir
    return None


def process_emails(
    source_root_path: Path, 
    classifier_model_path: Path, 
    path_config: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Verarbeitet E-Mails aus dem Quellverzeichnis und sortiert sie ein.

    Args:
        source_root_path (Path): Verzeichnis mit den zu sortierenden .msg-Dateien.
        classifier_model_path (Path): Pfad zum trainierten Klassifizierer-Modell.
        path_config (Dict[str, str]): Pfad-Konfiguration für die E-Mail-Klassen.

    Returns:
        List[Dict[str, Any]]: Liste der verschobenen E-Mails mit Metadaten.
    """
    moved_emails_data = []
    classifier = EmailClassifier()
    classifier.load(classifier_model_path)
    parser = MailParser()
    university_config = get_config()
    user_emails_list = [email_addr.lower() for email_addr in university_config.user.emails]

    for msg_file in sorted(source_root_path.rglob("*.msg")):
        try:
            # Klassifizierung durchführen
            prediction_output = classifier.predict(msg_file)
            assigned_class = prediction_output["prediction"]

            if assigned_class not in path_config:
                logger.warning(f"Keine Pfad-Konfiguration für '{assigned_class}' gefunden. Überspringe {msg_file.name}")
                continue
            
            class_base_path = Path(path_config[assigned_class])
            email_date = parser.get_email_date(msg_file)
            semester_identifier = get_semester(email_date)
            final_lastname = "Unknown"
            target_subfolder = "Inbox"

            import extract_msg
            with extract_msg.openMsg(str(msg_file)) as message_item:
                sender_raw = getattr(message_item, "sender", "")
                if not isinstance(sender_raw, str):
                    sender_raw = str(sender_raw)
                
                # Bestimmung ob die Mail vom Nutzer gesendet wurde
                extracted_sender_email = ""
                email_attr = getattr(message_item, "sender_email", None)
                if isinstance(email_attr, str):
                    extracted_sender_email = email_attr.lower().strip()
                if not extracted_sender_email:
                    email_search = re.search(r"[\w\.-]+@[\w\.-]+", sender_raw)
                    if email_search:
                        extracted_sender_email = email_search.group(0).lower()
                    else:
                        extracted_sender_email = sender_raw.lower()

                is_sent_by_tool_user = any(u_email in extracted_sender_email for u_email in user_emails_list)
                
                if is_sent_by_tool_user:
                    target_subfolder = "SentItems"
                    recipients = message_item.recipients or []
                    # Rule: Bevorzuge direkte Empfänger (To) für die Ordnerbenennung, ignoriere CC
                    # TO-Empfänger haben Typ 1 in extract-msg
                    to_recipients = [r for r in recipients if getattr(r, "type", None) == 1]
                    if to_recipients:
                        first_rec = to_recipients[0]
                        final_lastname = extract_lastname(f"{first_rec.name} <{first_rec.email}>" if first_rec.name and first_rec.email else (first_rec.name or first_rec.email))
                        if (not final_lastname or final_lastname == "Unknown") and len(to_recipients) > 1:
                            second_rec = to_recipients[1]
                            final_lastname = extract_lastname(f"{second_rec.name} <{second_rec.email}>" if second_rec.name and second_rec.email else (second_rec.name or second_rec.email))
                    elif recipients:
                        any_rec = recipients[0]
                        final_lastname = extract_lastname(f"{any_rec.name} <{any_rec.email}>" if any_rec.name and any_rec.email else (any_rec.name or any_rec.email))
                else:
                    target_subfolder = "Inbox"
                    # Rule: Der Ordnername sollte der Nachname des Absenders sein
                    final_lastname = extract_lastname(sender_raw)

            # Ziel-Verzeichnis bestimmen
            student_dir_path = find_student_folder(class_base_path, final_lastname)
            if not student_dir_path:
                student_dir_path = class_base_path / semester_identifier / final_lastname
                
            target_directory = student_dir_path / target_subfolder
            target_directory.mkdir(parents=True, exist_ok=True)
            target_file_path = target_directory / msg_file.name
            shutil.move(str(msg_file), str(target_file_path))
            
            moved_emails_data.append({
                "class": assigned_class, 
                "semester": semester_identifier, 
                "lastname": final_lastname, 
                "folder": target_subfolder, 
                "path": str(target_file_path)
            })
            logger.info(f"Verschoben: {msg_file.name} -> {target_file_path}")
        except Exception as processing_error:
            logger.error(f"Fehler bei Verarbeitung von {msg_file}: {processing_error}")
            
    return moved_emails_data


def write_report(base_directory: Path, moved_emails_list: List[Dict[str, Any]]) -> None:
    """Erstellt einen Markdown-Report über die erfolgreich einsortierten E-Mails.

    Args:
        base_directory (Path): Quellverzeichnis für den Speicherort des Reports.
        moved_emails_list (List[Dict[str, Any]]): Liste der verschobenen E-Mails.
    """
    if not moved_emails_list:
        logger.info("Keine E-Mails zum Berichten vorhanden.")
        return
    
    # Sortierung für den Report
    moved_emails_list.sort(key=lambda item: (item["class"], item["semester"], item["lastname"], item["folder"]))
    report_file_path = base_directory / "sorted_emails.md"
    
    with open(report_file_path, "w", encoding="utf-8") as report_file:
        report_file.write("# Sortierte E-Mails\n\n")
        current_email_class = None
        for email_item in moved_emails_list:
            if email_item["class"] != current_email_class:
                current_email_class = email_item["class"]
                report_file.write(f"## {current_email_class}\n\n")
                report_file.write("| Semester | Nachname | Ordner | Datei |\n")
                report_file.write("| --- | --- | --- | --- |\n")
            report_file.write(f"| {email_item['semester']} | {email_item['lastname']} | {email_item['folder']} | {email_item['path']} |\n")
    logger.info(f"Report erstellt: {report_file_path}")


def main() -> None:
    """Haupteinstiegspunkt für das E-Mail-Sortier-Skript."""
    argument_parser = argparse.ArgumentParser(description="Sortiert E-Mails basierend auf Klassifizierung.")
    
    argument_parser.add_argument(
        "source_dir", 
        help="Quellverzeichnis mit E-Mails."
    )
    argument_parser.add_argument(
        "--model", 
        required=True, 
        help="Pfad zum Klassifizierer-Modell."
    )
    argument_parser.add_argument(
        "--config", 
        required=True, 
        help="Pfad zur YAML-Konfiguration."
    )
    
    cli_args = argument_parser.parse_args()
    source_path = Path(cli_args.source_dir)
    
    if not source_path.exists():
        logger.error(f"Pfad existiert nicht: {source_path}")
        return

    with open(cli_args.config, "r", encoding="utf-8") as yaml_file:
        config_dict = yaml.safe_load(yaml_file)
        
    actual_config = config_dict.get("class_paths", config_dict)
    
    sorting_results = process_emails(source_path, Path(cli_args.model), actual_config)
    write_report(source_path, sorting_results)

if __name__ == "__main__":
    main()
