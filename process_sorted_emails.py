"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""

import argparse
import logging
import platform
import subprocess
import extract_msg
import yaml
from mcp_university.classifier.sort_emails import (
    process_emails,
    write_report,
    extract_lastname,
    extract_firstname,
)
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import win32com.client

    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False

from mcp_university.config import get_config
from mcp_university.summarizer.engine import Summarizer
from mcp_university.parser.mail_parser import MailParser
from mcp_university.agent import Agent

# Globaler Logger (wird in main konfiguriert)
logger = logging.getLogger(__name__)

DEBUG = True


def is_outlook_open() -> bool:
    """Prüft, ob Outlook aktuell geöffnet ist.

    Returns:
        bool: True wenn Outlook läuft, sonst False.
    """
    system = platform.system()
    try:
        if system == "Windows":
            # Prüfe mit tasklist unter Windows
            output = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq outlook.exe"',
                shell=True,
                stderr=subprocess.STDOUT,
            )
            return b"outlook.exe" in output.lower()
        elif system == "Darwin":  # macOS
            # Prüfe mit pgrep unter macOS
            try:
                subprocess.check_call(["pgrep", "-x", "Microsoft Outlook"])
                return True
            except subprocess.CalledProcessError:
                return False
        else:
            return False
    except Exception:
        return False


def run_sort_emails(source_dir: str, config_path: str) -> None:
    """Sortiert E-Mails basierend auf Klassifizierung.

    Args:
        source_dir: Quellordner mit den E-Mails.
        config_path: Pfad zur Konfigurationsdatei.
    """
    logger.info(f"Sortiere E-Mails in {source_dir}...")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if config and "class_paths" in config:
        config = config["class_paths"]

    source_root = Path(source_dir)
    model_path = Path("data/email_classifier.pkl")

    moved_emails = process_emails(source_root, model_path, config)
    write_report(source_root, moved_emails)


def parse_sorted_report(report_path: Path) -> List[Dict]:
    """Parst die sorted_emails.md Datei.

    Args:
        report_path: Pfad zum Markdown-Report.

    Returns:
        List[Dict]: Liste der extrahierten E-Mail-Daten.
    """
    emails = []
    if not report_path.exists():
        logger.warning(f"Report {report_path} existiert nicht.")
        return emails

    current_class = None
    with open(report_path, "r", encoding="utf-8") as f:
        for line in f:
            class_match = re.match(r"## (.*)", line)
            if class_match:
                current_class = class_match.group(1).strip()
                continue

            mail_match = re.search(r"- \*\*(.*?)\*\* \| (.*?) \| (.*?): `(.*?)`", line)
            if mail_match:
                emails.append(
                    {
                        "class": current_class,
                        "semester": mail_match.group(1),
                        "lastname": mail_match.group(2),
                        "folder": mail_match.group(3),
                        "path": Path(mail_match.group(4)),
                    }
                )
    return emails


def create_outlook_draft(
    subject: str,
    body: str,
    recipient: str = "",
    cc: List[str] = None,
    attachments: List[Path] = None,
) -> bool:
    """Erstellt einen E-Mail-Entwurf in Outlook.

    Args:
        subject: Betreff der E-Mail.
        body: Inhalt der E-Mail.
        recipient: Empfänger-Adresse.
        cc: Liste der CC-Adressen.
        attachments: Liste der Dateipfade für Anhänge.

    Returns:
        bool: True wenn erfolgreich, sonst False.
    """
    if not OUTLOOK_AVAILABLE:
        logger.info("pywin32 nicht installiert. Outlook-Draft nicht möglich.")
        return False

    if not is_outlook_open():
        logger.info("Outlook ist nicht geöffnet.")
        return False

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")

        target_account = "daniel.gaida@th-koeln.de"
        target_folder_name = "Work in Progress"

        # Versuche den spezifischen Ordner zu finden
        target_folder = None
        try:
            for store in namespace.Stores:
                if store.DisplayName == target_account:
                    root = store.GetRootFolder()
                    logger.info(f"Verfügbare Ordner in {target_account}:")
                    for folder in root.Folders:
                        logger.info(f" - {folder.Name}")
                        if folder.Name.lower() == target_folder_name.lower():
                            target_folder = folder
                            break

                    if not target_folder:
                        # Suche in Posteingang
                        for folder in root.Folders:
                            if folder.Name.lower() in ["posteingang", "inbox"]:
                                logger.info(f"Suche in {folder.Name}...")
                                for sub in folder.Folders:
                                    logger.info(f"   - {sub.Name}")
                                    if sub.Name.lower() == target_folder_name.lower():
                                        target_folder = sub
                                        break
                            if target_folder:
                                break
                    if target_folder:
                        break
        except Exception as e:
            logger.warning(f"Fehler beim Suchen des Zielordners: {e}")

        if target_folder:
            mail = target_folder.Items.Add(0)  # 0 = olMailItem
            logger.info(
                f"Erstelle Entwurf direkt in {target_account} -> {target_folder_name}."
            )
        else:
            mail = outlook.CreateItem(0)
            logger.warning(
                f"Zielordner {target_folder_name} nicht gefunden. Erstelle in Standard-Entwürfen."
            )

        mail.Subject = subject
        mail.Body = body
        if attachments:
            for attachment_path in attachments:
                if attachment_path.exists():
                    mail.Attachments.Add(str(attachment_path))
        if recipient:
            mail.To = recipient
        if cc:
            mail.CC = "; ".join(cc)

        mail.Save()
        mail.Display(False)

        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Outlook-Entwurfs: {e}")
        return False


def generate_reply(
    summarizer: Summarizer,
    mail_path: Path,
    summary_content: str = "",
    skill_path: Path = None,
    conversation_content: str = "",
    persona_path: Path = None,
    additional_context: str = "",
    debug: bool = False,
    appointment_skill_path: Path = None,
) -> Tuple[str, str, bool]:
    """Generiert eine Antwortmail mit dem LLM in zwei Schritten:
    1. Prüfung auf Terminrelevanz (Appointment Skill).
    2. Falls nicht relevant, klassenspezifische Antwort mit vollem Kontext.

    Args:
        summarizer: Summarizer-Instanz.
        mail_path: Pfad zur aktuellen E-Mail.
        summary_content: Inhalt der bisherigen Zusammenfassung.
        skill_path: Pfad zur SKILL-Datei.
        conversation_content: Optionaler Verlauf des Schriftverkehrs (statt Zusammenfassung).
        persona_path: Pfad zur Persona-Datei.
        additional_context: Zusätzlicher Kontext (z.B. aus einem PDF).
        debug: Ob Debug-Informationen gespeichert werden sollen.
        appointment_skill_path: Pfad zum Terminverwaltungs-Skill.

    Returns:
        Tuple[str, str, bool]: (Betreff, Antwort-Text, Soll ein Anhang angehängt werden?).
    """
    parser = MailParser()
    mail_content = parser.parse(mail_path)

    appointment_skill_content = ""
    if appointment_skill_path and appointment_skill_path.exists():
        appointment_skill_content = appointment_skill_path.read_text(encoding="utf-8")
        logger.info(f"Appointment-Skill-Datei geladen: {appointment_skill_path.name}")

    persona_content = ""
    if persona_path and persona_path.exists():
        persona_content = persona_path.read_text(encoding="utf-8")

    agent = Agent(
        model=summarizer.model, base_url=str(summarizer.client._client.base_url)
    )
    system_prompt = "Du bist ein hilfreicher Assistent an der TH Köln. Verfasse eine Antwort-E-Mail auf Deutsch."

    # --- SCHRITT 1: TERMINVERWALTUNG ---
    logger.info("Schritt 1: Prüfe Terminrelevanz...")
    appointment_user_prompt = f"""Prüfe die folgende E-Mail auf Terminrelevanz (Anfrage oder Bestätigung) basierend auf dem TERMINVERWALTUNG SKILL.

HEUTE IST: {datetime.now().strftime("%A, den %d.%m.%Y %H:%M")}

PERSONA:
{persona_content}

TERMINVERWALTUNG SKILL:
{appointment_skill_content}

ZUSÄTZLICHER KONTEXT (Anrede etc.):
{additional_context}

AKTUELLE E-MAIL:
{mail_content}

WICHTIGE ANWEISUNG:
1. Falls die E-Mail EINEN TERMIN BESTÄTIGT: Führe den Skill aus. Wenn erfolgreich gebucht, antworte EXAKT mit 'APPOINTMENT_BOOKED'.
2. Falls die E-Mail EINEN TERMIN ANFRAGT: Schlage freie Slots vor (nutze das Tool 'get_appointment_slots').
3. Falls die E-Mail KEINERLEI Bezug zu einer Terminbuchung oder -anfrage hat, antworte EXAKT mit: NO_APPOINTMENT_RELEVANCE

Format für Terminantworten (falls relevant):
ANHANG: [JA/NEIN]
BETREFF: [Der Betreff]
TEXT:
[Der Antwort-Text]
"""
    if debug:
        prompt_file = mail_path.parent / f"{mail_path.stem}_appointment_prompt.md"
        prompt_content = f"# System Prompt\n{system_prompt}\n\n# User Prompt\n{appointment_user_prompt}"
        prompt_file.write_text(prompt_content, encoding="utf-8")

    try:
        content = agent.chat(
            messages=[{"role": "user", "content": appointment_user_prompt}],
            system_prompt=system_prompt,
        )

        if "APPOINTMENT_BOOKED" in content:
            return "APPOINTMENT_BOOKED", "APPOINTMENT_BOOKED", False

        if "NO_APPOINTMENT_RELEVANCE" not in content:
            logger.info("Terminrelevanz erkannt, generiere Termin-Antwort.")
            should_attach = "ANHANG: JA" in content
            reply_subject = ""
            if "BETREFF:" in content:
                reply_subject = (
                    content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip()
                )
            reply_text = content
            if "TEXT:" in content:
                reply_text = content.split("TEXT:", 1)[1].strip()
            return reply_subject, reply_text, should_attach

    except Exception as e:
        logger.error(f"Fehler in Schritt 1 (Appointment): {e}")

    # --- SCHRITT 2: REGULÄRE ANTWORT ---
    logger.info("Schritt 2: Generiere reguläre Antwort mit vollem Kontext...")

    skill_content = "Keine spezifischen Anweisungen vorhanden."
    if skill_path and skill_path.exists():
        skill_content = skill_path.read_text(encoding="utf-8")
        logger.info(f"Klassenspezifische Skill geladen: {skill_path.name}")

    context_label = (
        "SCHRIFTVERKEHR DER LETZTEN 2 WOCHEN"
        if conversation_content
        else "ZUSAMMENFASSUNG DES SCHRIFTVERKEHRS"
    )
    context_body = conversation_content if conversation_content else summary_content

    regular_user_prompt = f"""Basierend auf der folgenden E-Mail, dem Kontext des bisherigen Schriftverkehrs, der Persona und den Skill-Anweisungen, verfasse eine professionelle Antwort.

HEUTE IST: {datetime.now().strftime("%A, den %d.%m.%Y %H:%M")}

PERSONA:
{persona_content}

KLASSENSPEZIFISCHE SKILL ANWEISUNGEN:
{skill_content}

ZUSÄTZLICHER KONTEXT:
{additional_context}

{context_label}:
{context_body}

AKTUELLE E-MAIL:
{mail_content}

Gib die Antwort in folgendem Format zurück:
ANHANG: [JA/NEIN]
BETREFF: [Der Betreff]
TEXT:
[Der Antwort-Text]
"""
    if debug:
        prompt_file = mail_path.parent / f"{mail_path.stem}_regular_prompt.md"
        prompt_content = (
            f"# System Prompt\n{system_prompt}\n\n# User Prompt\n{regular_user_prompt}"
        )
        prompt_file.write_text(prompt_content, encoding="utf-8")

    try:
        content = agent.chat(
            messages=[{"role": "user", "content": regular_user_prompt}],
            system_prompt=system_prompt,
        )

        should_attach = "ANHANG: JA" in content
        reply_subject = ""
        if "BETREFF:" in content:
            reply_subject = content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip()
        reply_text = content
        if "TEXT:" in content:
            reply_text = content.split("TEXT:", 1)[1].strip()

        return reply_subject, reply_text, should_attach
    except Exception as e:
        logger.error(f"Fehler in Schritt 2 (Regulär): {e}")
        return "", "Fehler bei der Generierung der Antwort.", False


def main() -> None:
    """Haupteinstiegspunkt des Skripts."""
    config = get_config()

    # Log-Verzeichnis sicherstellen
    config.log_path.mkdir(parents=True, exist_ok=True)

    # Logging konfigurieren
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    file_handler = logging.FileHandler(
        config.log_path / "process_emails.log", encoding="utf-8"
    )
    stream_handler = logging.StreamHandler()

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[file_handler, stream_handler],
        force=True,  # Vorhandene Konfiguration überschreiben
    )

    parser = argparse.ArgumentParser(
        description="Verarbeitet sortierte E-Mails und generiert Antworten."
    )
    parser.add_argument("source_dir", help="Quellordner der E-Mails")
    parser.add_argument(
        "--config", default="config/folders.yaml", help="Pfad zur Konfiguration"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=DEBUG,
        help="Speichert LLM Prompts als Markdown (Default: True)",
    )
    parser.add_argument(
        "--no-debug",
        action="store_false",
        dest="debug",
        help="Deaktiviert das Speichern von Prompts",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    # 1. Sortieren
    try:
        run_sort_emails(str(source_dir), args.config)
    except Exception as e:
        logger.error(f"Fehler beim Sortieren: {e}")

    # 2. Report parsen
    report_path = source_dir / "sorted_emails.md"
    emails = parse_sorted_report(report_path)
    logger.info(f"{len(emails)} sortierte E-Mails gefunden.")

    summarizer = Summarizer(model=config.llm.model, base_url=config.llm.base_url)
    mail_parser = MailParser()

    # Wir tracken verarbeitete student_folders, um Mehrfachverarbeitung zu vermeiden
    processed_results = []

    # Liste der zu beantwortenden E-Mails erstellen
    emails_to_process_path = source_dir / "emails_to_process.md"
    unique_emails_to_process = []
    temp_folders = set()

    for email in emails:
        mail_path = Path(email["path"])
        is_ba_ma = email["class"].startswith(("BA_", "MA_"))
        if is_ba_ma:
            identifier = (email["class"], email["semester"], email["lastname"])
            # BA/MA logic to find latest mail
            semester_folder = mail_path.parent.parent
            inbox_folder = semester_folder / "Inbox"
            sent_folder = semester_folder / "SentItems"
            all_files = []
            if inbox_folder.exists():
                all_files.extend(
                    list(inbox_folder.glob("*.msg")) + list(inbox_folder.glob("*.eml"))
                )
            if sent_folder.exists():
                all_files.extend(
                    list(sent_folder.glob("*.msg")) + list(sent_folder.glob("*.eml"))
                )

            student_emails = []
            for f in all_files:
                try:
                    with extract_msg.openMsg(str(f)) as msg:
                        sender_lastname = extract_lastname(msg.sender)
                        recipient_lastname = "None"
                        if msg.recipients:
                            recipient_lastname = extract_lastname(
                                msg.recipients[0].name or msg.recipients[0].email
                            )
                        if (
                            sender_lastname == email["lastname"]
                            or recipient_lastname == email["lastname"]
                        ):
                            date = mail_parser.get_email_date(f)
                            student_emails.append((date, f))
                except Exception:
                    continue

            if not student_emails:
                continue
            student_emails.sort(key=lambda x: x[0])
            latest_date, latest_mail = student_emails[-1]
            needs_answer = "Inbox" in latest_mail.parts

            # Bereicherung des E-Mail-Dicts für spätere Verarbeitung
            email["latest_date"] = latest_date
            email["latest_mail"] = latest_mail
            email["student_emails"] = student_emails
            email["semester_folder"] = semester_folder
        else:
            identifier = mail_path.parent.parent
            # Normal student folder logic
            email_files = list(identifier.rglob("*.msg")) + list(
                identifier.rglob("*.eml")
            )
            if not email_files:
                continue
            dated_emails = []
            for f in email_files:
                try:
                    date = mail_parser.get_email_date(f)
                    dated_emails.append((date, f))
                except Exception:
                    dated_emails.append((datetime.min, f))
            dated_emails.sort(key=lambda x: x[0])
            latest_date, latest_mail = dated_emails[-1]
            needs_answer = (
                "Inbox" in latest_mail.parts and "SentItems" not in latest_mail.parts
            )

            # Bereicherung des E-Mail-Dicts für spätere Verarbeitung
            email["latest_date"] = latest_date
            email["latest_mail"] = latest_mail
            email["dated_emails"] = dated_emails
            email["identifier_path"] = identifier

        if needs_answer and identifier not in temp_folders:
            temp_folders.add(identifier)
            unique_emails_to_process.append(email)

    with open(emails_to_process_path, "w", encoding="utf-8") as f:
        f.write("# Zu beantwortende E-Mails\n\n")
        f.write("| Student | Klasse | Semester |\n")
        f.write("| :--- | :--- | :--- |\n")
        for email in unique_emails_to_process:
            f.write(
                "| {} | {} | {} |\n".format(
                    email["lastname"], email["class"], email["semester"]
                )
            )
    logger.info(
        f"Liste der zu beantwortenden E-Mails erstellt: {emails_to_process_path}"
    )

    persona_path = Path("skills/SKILL_persona.md")
    appointment_skill_path = Path("skills/SKILL_Appointment.md")

    for email in unique_emails_to_process:
        latest_mail = email["latest_mail"]
        latest_date = email["latest_date"]
        is_ba_ma = email["class"].startswith(("BA_", "MA_"))

        if is_ba_ma:
            semester_folder = email["semester_folder"]
            student_emails = email["student_emails"]

            logger.info(
                f"Verarbeite BA/MA E-Mails für {email['lastname']} in {email['class']}"
            )

            threshold_date = latest_date - timedelta(days=14)
            recent_emails = [e for e in student_emails if e[0] >= threshold_date]

            conversation_content = ""
            for date, f in recent_emails:
                if f == latest_mail:
                    continue
                p = mail_parser.parse(f)
                if p:
                    conversation_content += f"\n--- EMAIL VOM {date} ---\n{p}\n"

            # Extraktion von Empfänger und CC
            student_email = ""
            cc_list = []
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    student_email = msg.sender
                    if msg.recipients:
                        for rec in msg.recipients:
                            rec_email = rec.email or rec.name
                            if (
                                rec_email
                                and "daniel.gaida@th-koeln.de" not in rec_email.lower()
                            ):
                                if rec_email.lower() != student_email.lower():
                                    cc_list.append(rec_email)
            except Exception:
                pass

            # Gender Determination und Salutation
            first_name = "Unknown"
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    first_name = extract_firstname(msg.sender)
            except Exception:
                pass
            gender_salutation = summarizer.determine_gender(first_name)
            salutation = f"Guten Tag {gender_salutation} {email['lastname']}"

            skill_path = Path(f"skills/SKILL_{email['class']}.md")

            # Zusätzlicher Kontext (z.B. PO-Wechsel)
            additional_context = f"Anrede: {salutation}\n"
            additional_context += f"Studenten-E-Mail: {student_email}\n"
            attachments = []
            if email["class"] == "PO-Wechsel":
                pdf_path = Path(
                    r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf"
                )
                if pdf_path.exists():
                    additional_context += f"\nDu kannst bei Bedarf Details aus der Datei '{pdf_path}' mittels des read_file Tools auslesen.\n"

            reply_subject, reply, should_attach = generate_reply(
                summarizer,
                latest_mail,
                skill_path=skill_path,
                conversation_content=conversation_content,
                persona_path=persona_path,
                additional_context=additional_context,
                debug=args.debug,
                appointment_skill_path=appointment_skill_path,
            )

            if reply == "APPOINTMENT_BOOKED":
                logger.info(
                    f"Termin für {email['lastname']} wurde erfolgreich gebucht."
                )
                processed_results.append(
                    {
                        "lastname": email["lastname"],
                        "subject": latest_mail.stem,
                        "status": "Termin gebucht (Kalender)",
                    }
                )
                continue

            if should_attach and email["class"] == "PO-Wechsel":
                pdf_path = Path(
                    r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf"
                )
                if pdf_path.exists():
                    attachments.append(pdf_path)

            # Speichere Antwort
            subject = latest_mail.stem
            success = create_outlook_draft(
                reply_subject or subject,
                reply,
                recipient=student_email,
                cc=cc_list,
                attachments=attachments,
            )
            if success:
                logger.info(f"Outlook-Entwurf für {latest_mail.name} erstellt.")
                result_status = "Outlook Entwurf (Work in Progress)"
            else:
                reply_path = (
                    semester_folder / f"{latest_mail.stem}_{email['lastname']}_reply.md"
                )
                reply_path.write_text(reply, encoding="utf-8")
                logger.info(f"Antwort als Markdown gespeichert: {reply_path}")
                result_status = f"Datei: {reply_path}"

            processed_results.append(
                {
                    "lastname": email["lastname"],
                    "subject": subject,
                    "status": result_status,
                }
            )

        else:
            identifier = email["identifier_path"]
            dated_emails = email["dated_emails"]

            summary_file = identifier / ".emails_summary.md"

            should_update = False
            if not summary_file.exists():
                should_update = True
            else:
                summary_mtime = datetime.fromtimestamp(summary_file.stat().st_mtime)
                if latest_date > summary_mtime:
                    should_update = True

            summary_content = ""
            if should_update:
                logger.info(
                    f"Erstelle/Aktualisiere Zusammenfassung für {identifier.name}"
                )
                conv_content = ""
                for date, f in dated_emails:
                    p = mail_parser.parse(f)
                    if p:
                        conv_content += f"\n--- EMAIL VOM {date} ---\n{p}\n"

                summary_content = summarizer.summarize_email_conversation(
                    identifier.name, conv_content
                )
                if summary_content:
                    summary_file.write_text(summary_content, encoding="utf-8")
            else:
                summary_content = summary_file.read_text(encoding="utf-8")

            logger.info(
                f"Generiere Antwort für neueste Mail in {identifier.name}: {latest_mail.name}"
            )

            # Extraktion von Empfänger und CC
            student_email = ""
            cc_list = []
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    student_email = msg.sender
                    if msg.recipients:
                        for rec in msg.recipients:
                            rec_email = rec.email or rec.name
                            if (
                                rec_email
                                and "daniel.gaida@th-koeln.de" not in rec_email.lower()
                            ):
                                if rec_email.lower() != student_email.lower():
                                    cc_list.append(rec_email)
            except Exception:
                pass

            # Gender Determination und Salutation
            first_name = "Unknown"
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    first_name = extract_firstname(msg.sender)
            except Exception:
                pass
            gender_salutation = summarizer.determine_gender(first_name)
            salutation = f"Guten Tag {gender_salutation} {email['lastname']}"

            skill_path = Path(f"skills/SKILL_{email['class']}.md")
            if not skill_path.exists():
                # Fallback to script directory
                skill_path = (
                    Path(__file__).parent / "skills" / f"SKILL_{email['class']}.md"
                )

            additional_context = f"Anrede: {salutation}\n"
            additional_context += f"Studenten-E-Mail: {student_email}\n"
            attachments = []
            if email["class"] == "PO-Wechsel":
                pdf_path = Path(
                    r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf"
                )
                if pdf_path.exists():
                    additional_context += f"\nDu kannst bei Bedarf Details aus der Datei '{pdf_path}' mittels des read_file Tools auslesen.\n"

            reply_subject, reply, should_attach = generate_reply(
                summarizer,
                latest_mail,
                summary_content or "",
                skill_path,
                persona_path=persona_path,
                additional_context=additional_context,
                debug=args.debug,
                appointment_skill_path=appointment_skill_path,
            )

            if reply == "APPOINTMENT_BOOKED":
                logger.info(
                    f"Termin für {email['lastname']} wurde erfolgreich gebucht."
                )
                processed_results.append(
                    {
                        "lastname": email["lastname"],
                        "subject": latest_mail.stem,
                        "status": "Termin gebucht (Kalender)",
                    }
                )
                continue

            if should_attach and email["class"] == "PO-Wechsel":
                pdf_path = Path(
                    r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf"
                )
                if pdf_path.exists():
                    attachments.append(pdf_path)

            subject = latest_mail.stem
            success = create_outlook_draft(
                reply_subject or subject,
                reply,
                recipient=student_email,
                cc=cc_list,
                attachments=attachments,
            )
            if success:
                logger.info(f"Outlook-Entwurf für {latest_mail.name} erstellt.")
                result_status = "Outlook Entwurf (Work in Progress)"
            else:
                reply_path = identifier / f"{latest_mail.stem}_reply.md"
                reply_path.write_text(reply, encoding="utf-8")
                logger.info(f"Antwort als Markdown gespeichert: {reply_path}")
                result_status = f"Datei: {reply_path}"

            processed_results.append(
                {
                    "lastname": email["lastname"],
                    "subject": subject,
                    "status": result_status,
                }
            )

    # 3. Abschluss-Bericht erstellen und aufräumen
    if processed_results:
        processed_report_path = source_dir / "processed_emails.md"
        with open(processed_report_path, "w", encoding="utf-8") as f:
            f.write("# Verarbeitete E-Mails\n\n")
            f.write("| Student | Betreff | Status |\n")
            f.write("| :--- | :--- | :--- |\n")
            for res in processed_results:
                f.write(f"| {res['lastname']} | {res['subject']} | {res['status']} |\n")
        logger.info(f"Abschlussbericht erstellt: {processed_report_path}")

    if report_path.exists():
        report_path.unlink()
        logger.info(f"Temporärer Report gelöscht: {report_path}")


if __name__ == "__main__":
    main()
