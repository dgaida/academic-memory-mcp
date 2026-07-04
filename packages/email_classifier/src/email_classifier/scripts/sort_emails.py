"""Skript zum Sortieren von E-Mails basierend auf einer Klassifizierung.

Dieses Modul bietet Funktionen zum Extrahieren von Namen aus E-Mail-Adressen
und zum Verschieben von E-Mail-Dateien in eine strukturierte Ordnerhierarchie.
"""

import argparse
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from email_classifier.engine import EmailClassifier
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
    "admin", "office", "sekretariat", "onbehalf", "f10-request"
]


def clean_sender_name(name_string: str) -> str:
    """Bereinigt den Absendernamen von komplexen Headern wie 'im Auftrag von'.

    Args:
        name_string (str): Der zu bereinigende Namensstring.

    Returns:
        str: Der bereinigte Name.
    """
    if not name_string:
        return ""
    
    # MIME-Header dekodieren falls nötig
    name_string = decode_mime_header(name_string)
    
    if "im Auftrag von" in name_string:
        # Versuche einen echten Namen nach "im Auftrag von;" zu finden
        parts = name_string.split("im Auftrag von")
        if len(parts) > 1:
            name_candidate = parts[1].strip(":; ")
            # Falls Name leer ist oder nur Email-Teil, versuche weiter zu parsen
            if not name_candidate or "@" in name_candidate.split("<")[0]:
                 # Check if there's a name after a second semicolon or similar
                 subparts = name_candidate.split(";")
                 for sp in subparts:
                      sp = sp.strip()
                      if sp and "@" not in sp.split("<")[0]:
                           name_candidate = sp
                           break
            if name_candidate:
                return name_candidate.strip("'\" ")
        else:
            # Fallback für andere Varianten
            match = re.search(r"im Auftrag von\s*[:;]?\s*([^<;]+)", name_string)
            if match:
                return match.group(1).strip("'\" ")

    # Handle spezifisches Präfix "TH //"
    name_string = re.sub(r"^TH\s*//\s*", "", name_string)
    return name_string.strip("'\" ")


def _format_dashed_name(name_input: str) -> str:
    """Formatiert einen Namen mit Bindestrichen (Title Case pro Teil).

    Beispiel: 'studium-gm' wird zu 'Studium-Gm'.

    Args:
        name_input: Der zu formatierende Name.

    Returns:
        str: Der formatierte Name mit Großbuchstaben nach Bindestrichen.
    """
    if not name_input:
        return ""
    if "-" in name_input:
        parts = name_input.split("-")
        return "-".join(part[0].upper() + part[1:] if part else "" for part in parts)
    return name_input[0].upper() + name_input[1:]


def extract_firstname(name_input: str) -> str:
    """Extrahiert den Vornamen aus einem Namensstring oder einer E-Mail-Adresse.

    Args:
        name_input (str): Der zu parsende Name oder die E-Mail-Adresse.

    Returns:
        str: Der extrahierte Vorname oder 'Unknown'.
    """
    if not name_input or name_input in ["(No Sender)", "(No Receiver)", "Unknown"]:
        return "Unknown"

    cleaned_name = clean_sender_name(name_input)

    # Suche nach E-Mail-Adresse im bereinigten Namen bevorzugt
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", cleaned_name)
    if not email_match:
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_input)
    email_address = email_match.group(0) if email_match else ""

    # Anzeige-Name extrahieren (Teil vor der spitzen Klammer)
    display_name = cleaned_name.split("<")[0].strip()
    if display_name == email_address:
        display_name = ""
        
    # Klammern und akademische Titel entfernen
    display_name = re.sub(r"\(.*?\)", "", display_name).strip()
    display_name = re.sub(r",?\s*(B\.Sc\.|M\.Sc\.|Prof\.|Dr\.)\s*", "", display_name).strip()

    # Priorität 1: Reicher Anzeigename (mehrere Wörter oder Format 'Nachname, Vorname')
    if display_name and (" " in display_name or "," in display_name):
        if "," in display_name:
            parts = display_name.split(",")
            if len(parts) > 1:
                return parts[1].strip().split()[0].strip("'\"")
        else:
            parts = display_name.split()
            if len(parts) > 1:
                return " ".join(parts[:-1]).strip("'\"")

    # Priorität 2: E-Mail-Adresse mit Punkt im Local-Part (Hochschul-Format: vorname.nachname)
    if email_address and any(domain in email_address.lower() for domain in ["th-koeln.de", "fh-koeln.de"]):
        local_part = email_address.split("@")[0]
        if "." in local_part:
            firstname_part = local_part.split(".")[0]
            # Ersetze Unterstriche durch Leerzeichen und setze Wortanfänge groß
            parts = re.split(r'([_-])', firstname_part)
            result_firstname = ""
            for part in parts:
                if part in ["_", "-"]:
                    result_firstname += " " if part == "_" else "-"
                else:
                    if part:
                        result_firstname += part[0].upper() + part[1:]
            return result_firstname

    # Priorität 3: Fallback auf verbleibenden Anzeigenamen
    if display_name:
        return display_name

    return "Unknown"


def _clean_for_comparison(string_value: str) -> str:
    """Hilfsfunktion für den normalisierten Vergleich von Namensteilen.

    Normalisiert Umlaute und entfernt Trennzeichen für einen robusten Vergleich.

    Args:
        string_value: Der zu säubernde String.

    Returns:
        str: Der gesäuberte und normalisierte String.
    """
    return string_value.lower().replace("ß", "ss").replace("_", "").replace(".", "").replace("-", "").strip()


def extract_lastname(name_input: str) -> str:
    """Extrahiert den Nachnamen aus einem Namensstring oder einer E-Mail-Adresse.

    Berücksichtigt spezifische Anforderungen für Hochschul-Systemadressen, 
    multi-word Nachnamen und Fallbacks auf den E-Mail Local-Part.

    Args:
        name_input (str): Der zu parsende Name oder die E-Mail-Adresse.

    Returns:
        str: Der extrahierte Nachname oder 'Unknown'.
    """
    logger.debug(f"Extrahiere Nachname aus: {name_input}")
    if not name_input or name_input in ["(No Sender)", "(No Receiver)", "Unknown"]:
        return "Unknown"

    cleaned_name = clean_sender_name(name_input)

    # Email und Local-Part extrahieren - Bevorzugt aus bereinigtem Namen (Wichtig für 'im Auftrag von')
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", cleaned_name)
    if not email_match:
         email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_input)
    
    email_address = email_match.group(0) if email_match else ""
    local_part = email_address.split("@")[0] if email_address else ""

    # Anzeige-Namen extrahieren und bereinigen
    display_name = cleaned_name.split("<")[0].strip()
    if display_name == email_address:
        display_name = ""
    display_name = display_name.strip("'\" ")
    display_name = re.sub(r"\(.*?\)", "", display_name).strip()
    display_name = re.sub(r",?\s*(B\.Sc\.|M\.Sc\.|Prof\.|Dr\.)\s*", "", display_name).strip()
    display_name = re.sub(r"\s*\|\s*.*$", "", display_name)
    display_name = re.sub(r"\s+GmbH\b.*$", "", display_name).strip("'\" ")

    # 1. Systemadressen (Priorität 1)
    if local_part:
        local_part_lower = local_part.lower()
        if "digital-sciences" in local_part_lower:
            return "Digital-Sciences"
        if "kreditorenbuchhaltung" in local_part_lower:
            return "Kreditorenbuchhaltung"

    # 2. Greedy Match gegen den letzten Teil des Local-Parts (Priorität 2)
    # Behandelt Fälle wie 'A B C D <a_b.c_d@smail...>' -> 'C D'
    if display_name and local_part and _clean_for_comparison(local_part) not in GENERIC_LOCAL_PARTS:
        # Teil nach dem letzten Punkt im Local-Part als Referenz nehmen
        lp_lastname_segment = local_part.split(".")[-1]
        lp_segment_normalized = _clean_for_comparison(lp_lastname_segment)
        
        # Falls Komma vorhanden (Format 'Nachname, Vorname'), nur den Teil davor betrachten
        potential_source = display_name.split(",")[-1].strip() if "," in display_name else display_name
        words = potential_source.split()
        
        matching_words = []
        for word in reversed(words):
            word_normalized = _clean_for_comparison(word)
            if word_normalized and word_normalized in lp_segment_normalized:
                matching_words.insert(0, word)
            else:
                break
        if matching_words:
            return " ".join(matching_words)

    # 3. E-Mail mit Punkt im Local-Part (Hochschul-Format)
    if local_part and "." in local_part:
        lastname_part = local_part.rsplit(".", 1)[1]
        logger.debug(f"Punkt im lokalen Teil gefunden: {local_part} -> Extrahiere {lastname_part}")
        parts = re.split(r'([._])', lastname_part)
        result_lastname = ""
        for part in parts:
            if part in ["_", "."]:
                result_lastname += " "
            elif part:
                if "-" in part:
                    subparts = part.split("-")
                    result_lastname += "-".join(sub[0].upper() + sub[1:] if sub else "" for sub in subparts)
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
                # Falls Local-Part Großbuchstaben hat, diese als Bezeichner bevorzugen (z.B. HWester)
                if any(character.isupper() for character in local_part):
                    return local_part
                # Falls Bindestriche vorhanden sind (z.B. praxissemester-inf)
                if "-" in local_part:
                    return _format_dashed_name(local_part)
                return local_part[0].upper() + local_part[1:] if local_part else "Unknown"

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
    path_config: Dict[str, str],
    dry_run: bool = False
) -> List[Dict[str, Any]]:
    """Verarbeitet E-Mails aus dem Quellverzeichnis und sortiert sie ein.

    Args:
        source_root_path (Path): Verzeichnis mit den zu sortierenden .msg-Dateien.
        classifier_model_path (Path): Pfad zum trainierten Klassifizierer-Modell.
        path_config (Dict[str, str]): Pfad-Konfiguration für die E-Mail-Klassen.
        dry_run (bool): Falls True, werden die Dateien nicht verschoben.

    Returns:
        List[Dict[str, Any]]: Liste der verschobenen (oder klassifizierten) E-Mails mit Metadaten.
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
            
            if dry_run:
                moved_emails_data.append({
                    "class": assigned_class,
                    "semester": semester_identifier,
                    "lastname": final_lastname,
                    "folder": target_subfolder,
                    "path": str(msg_file),
                    "target_path": str(target_directory / msg_file.name)
                })
                logger.info(f"Klassifiziert (Dry-Run): {msg_file.name} -> {assigned_class}")
            else:
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

    HINWEIS: Alle sortierten E-Mails müssen im Report enthalten sein und später in der GUI
    angezeigt werden. Es dürfen keine E-Mails unterschlagen werden.

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
