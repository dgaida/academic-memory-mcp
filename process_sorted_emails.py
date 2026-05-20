"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""
import argparse
import logging
import platform
import subprocess
import extract_msg
import yaml
from mcp_university.classifier.sort_emails import process_emails, write_report, extract_lastname, extract_firstname
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import win32com.client
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False

from mcp_university.classifier.sort_emails import process_emails, write_report, extract_lastname
from mcp_university.config import get_config
from mcp_university.summarizer.engine import Summarizer
from mcp_university.parser.mail_parser import MailParser
from mcp_university.parser.factory import ParserFactory

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

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
                emails.append({
                    "class": current_class,
                    "semester": mail_match.group(1),
                    "lastname": mail_match.group(2),
                    "folder": mail_match.group(3),
                    "path": Path(mail_match.group(4))
                })
    return emails

def create_outlook_draft(subject: str, body: str, recipient: str = "", attachments: List[Path] = None) -> bool:
    """Erstellt einen E-Mail-Entwurf in Outlook.

    Args:
        subject: Betreff der E-Mail.
        body: Inhalt der E-Mail.
        recipient: Empfänger-Adresse.
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
                    for folder in root.Folders:
                        if folder.Name == target_folder_name:
                            target_folder = folder
                            break
                    if target_folder:
                        break
        except Exception as e:
            logger.warning(f"Fehler beim Suchen des Zielordners: {e}")

        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.Subject = f"Re: {subject}"
        mail.Body = body
        if attachments:
            for attachment_path in attachments:
                if attachment_path.exists():
                    mail.Attachments.Add(str(attachment_path))
        if recipient:
            mail.To = recipient

        if target_folder:
            mail.Save()  # Erst in Standard-Drafts speichern
            moved_mail = mail.Move(target_folder)
            logger.info(f"Entwurf in {target_account} -> {target_folder_name} gespeichert.")
            moved_mail.Display(False)
        else:
            mail.Save()
            logger.warning(f"Zielordner {target_folder_name} nicht gefunden. In Standard-Entwürfen gespeichert.")
            mail.Display(False)

        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Outlook-Entwurfs: {e}")
        return False

def generate_reply(summarizer: Summarizer, mail_path: Path, summary_content: str = "", skill_path: Path = None, conversation_content: str = "", persona_path: Path = None, additional_context: str = "") -> Tuple[str, bool]:
    """Generiert eine Antwortmail mit dem LLM.

    Args:
        summarizer: Summarizer-Instanz.
        mail_path: Pfad zur aktuellen E-Mail.
        summary_content: Inhalt der bisherigen Zusammenfassung.
        skill_path: Pfad zur SKILL-Datei.
        conversation_content: Optionaler Verlauf des Schriftverkehrs (statt Zusammenfassung).
        persona_path: Pfad zur Persona-Datei.
        additional_context: Zusätzlicher Kontext (z.B. aus einem PDF).

    Returns:
        Tuple[str, bool]: (Antwort-Text, Soll ein Anhang angehängt werden?).
    """
    parser = MailParser()
    mail_content = parser.parse(mail_path)

    skill_content = "Keine spezifischen Anweisungen vorhanden."
    if skill_path and skill_path.exists():
        skill_content = skill_path.read_text(encoding="utf-8")

    persona_content = ""
    if persona_path and persona_path.exists():
        persona_content = persona_path.read_text(encoding="utf-8")

    context_label = "SCHRIFTVERKEHR DER LETZTEN 2 WOCHEN" if conversation_content else "ZUSAMMENFASSUNG DES SCHRIFTVERKEHRS"
    context_body = conversation_content if conversation_content else summary_content

    system_prompt = "Du bist ein hilfreicher Assistent an der TH Köln. Verfasse eine Antwort-E-Mail auf Deutsch."
    user_prompt = f"""Basierend auf der folgenden E-Mail, dem Kontext des bisherigen Schriftverkehrs, der Persona und den Skill-Anweisungen, verfasse eine professionelle Antwort.

PERSONA:
{persona_content}

SKILL ANWEISUNGEN:
{skill_content}

ZUSÄTZLICHER KONTEXT:
{additional_context}

{context_label}:
{context_body}

AKTUELLE E-MAIL:
{mail_content}

Gib die Antwort in folgendem Format zurück:
ANHANG: [JA/NEIN]
TEXT:
[Der Antwort-Text]

Antworte NUR in diesem Format.
"""
    try:
        response = summarizer.client.chat(
            model=summarizer.model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        content = response['message']['content']

        should_attach = False
        if "ANHANG: JA" in content:
            should_attach = True

        reply_text = content
        if "TEXT:" in content:
            reply_text = content.split("TEXT:", 1)[1].strip()

        return reply_text, should_attach
    except Exception as e:
        logger.error(f"Fehler bei LLM-Generierung: {e}")
        return "Fehler bei der Generierung der Antwort.", False

def main() -> None:
    """Haupteinstiegspunkt des Skripts."""
    parser = argparse.ArgumentParser(description="Verarbeitet sortierte E-Mails und generiert Antworten.")
    parser.add_argument("source_dir", help="Quellordner der E-Mails")
    parser.add_argument("--config", required=True, help="Pfad zur classifier_paths.yaml")
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

    config = get_config()
    summarizer = Summarizer(model=config.llm.model, base_url=config.llm.base_url)
    mail_parser = MailParser()
    parser_factory = ParserFactory(config.data_dir / "cache")

    # Wir tracken verarbeitete student_folders, um Mehrfachverarbeitung zu vermeiden
    processed_folders = set()
    processed_results = []

    persona_path = Path("skills/SKILL_persona.md")

    for email in emails:
        mail_path = Path(email["path"])
        is_ba_ma = email["class"].startswith(("BA_", "MA_"))

        if is_ba_ma:
            # Bei BA/MA tracken wir (class, semester, lastname)
            identifier = (email["class"], email["semester"], email["lastname"])
        else:
            # Pfadstruktur: .../Klasse/Semester/Nachname/Inbox/mail.msg
            student_folder = mail_path.parent.parent
            identifier = student_folder

        if identifier in processed_folders:
            continue
        processed_folders.add(identifier)

        subject = mail_path.stem
        result_status = "Übersprungen"

        if is_ba_ma:
            # Speziallogik für BA/MA: Sammle alle Mails des Studenten in diesem Semester
            semester_folder = mail_path.parent.parent
            inbox_folder = semester_folder / "Inbox"
            sent_folder = semester_folder / "SentItems"

            all_files = []
            if inbox_folder.exists():
                all_files.extend(list(inbox_folder.glob("*.msg")) + list(inbox_folder.glob("*.eml")))
            if sent_folder.exists():
                all_files.extend(list(sent_folder.glob("*.msg")) + list(sent_folder.glob("*.eml")))

            student_emails = []
            for f in all_files:
                try:
                    with extract_msg.openMsg(str(f)) as msg:
                        sender_lastname = extract_lastname(msg.sender)
                        recipient_lastname = "None"
                        if msg.recipients:
                            recipient_lastname = extract_lastname(msg.recipients[0].name or msg.recipients[0].email)

                        if sender_lastname == email["lastname"] or recipient_lastname == email["lastname"]:
                            date = mail_parser.get_email_date(f)
                            student_emails.append((date, f))
                except Exception:
                    continue

            if not student_emails:
                continue

            student_emails.sort(key=lambda x: x[0])
            latest_date, latest_mail = student_emails[-1]

            if "Inbox" not in latest_mail.parts:
                continue

            logger.info(f"Verarbeite BA/MA E-Mails für {email['lastname']} in {email['class']}")

            threshold_date = latest_date - timedelta(days=14)
            recent_emails = [e for e in student_emails if e[0] >= threshold_date]

            conversation_content = ""
            for date, f in recent_emails:
                if f == latest_mail:
                    continue
                p = mail_parser.parse(f)
                if p:
                    conversation_content += f"\n--- EMAIL VOM {date} ---\n{p}\n"

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
            attachments = []
            if email["class"] == "PO-Wechsel":
                pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                if pdf_path.exists():
                    pdf_content = parser_factory.parse(pdf_path)
                    if pdf_content:
                        additional_context += f"\nINHALT INFOS PDF:\n{pdf_content}\n"

            reply, should_attach = generate_reply(summarizer, latest_mail, skill_path=skill_path, conversation_content=conversation_content, persona_path=persona_path, additional_context=additional_context)

            if should_attach and email["class"] == "PO-Wechsel":
                pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                if pdf_path.exists():
                    attachments.append(pdf_path)

            # Speichere Antwort
            subject = latest_mail.stem
            success = create_outlook_draft(subject, reply, attachments=attachments)
            if success:
                logger.info(f"Outlook-Entwurf für {latest_mail.name} erstellt.")
                result_status = "Outlook Entwurf (Work in Progress)"
            else:
                reply_path = semester_folder / f"{latest_mail.stem}_{email['lastname']}_reply.md"
                reply_path.write_text(reply, encoding="utf-8")
                logger.info(f"Antwort als Markdown gespeichert: {reply_path}")
                result_status = f"Datei: {reply_path}"

            processed_results.append({"lastname": email["lastname"], "subject": subject, "status": result_status})

        else:
            summary_file = identifier / ".emails_summary.md"
            email_files = list(identifier.rglob("*.msg")) + list(identifier.rglob("*.eml"))
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

            should_update = False
            if not summary_file.exists():
                should_update = True
            else:
                summary_mtime = datetime.fromtimestamp(summary_file.stat().st_mtime)
                if latest_date > summary_mtime:
                    should_update = True

            summary_content = ""
            if should_update:
                logger.info(f"Erstelle/Aktualisiere Zusammenfassung für {identifier.name}")
                conv_content = ""
                for date, f in dated_emails:
                    p = mail_parser.parse(f)
                    if p:
                        conv_content += f"\n--- EMAIL VOM {date} ---\n{p}\n"

                summary_content = summarizer.summarize_email_conversation(identifier.name, conv_content)
                if summary_content:
                    summary_file.write_text(summary_content, encoding="utf-8")
            else:
                summary_content = summary_file.read_text(encoding="utf-8")

            if "Inbox" in latest_mail.parts and "SentItems" not in latest_mail.parts:
                logger.info(f"Generiere Antwort für neueste Mail in {identifier.name}: {latest_mail.name}")

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

                additional_context = f"Anrede: {salutation}\n"
                attachments = []
                if email["class"] == "PO-Wechsel":
                    pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                    if pdf_path.exists():
                        pdf_content = parser_factory.parse(pdf_path)
                        if pdf_content:
                            additional_context += f"\nINHALT INFOS PDF:\n{pdf_content}\n"

                reply, should_attach = generate_reply(summarizer, latest_mail, summary_content or "", skill_path, persona_path=persona_path, additional_context=additional_context)

                if should_attach and email["class"] == "PO-Wechsel":
                    pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                    if pdf_path.exists():
                        attachments.append(pdf_path)

                subject = latest_mail.stem
                success = create_outlook_draft(subject, reply, attachments=attachments)
                if success:
                    logger.info(f"Outlook-Entwurf für {latest_mail.name} erstellt.")
                    result_status = "Outlook Entwurf (Work in Progress)"
                else:
                    reply_path = identifier / f"{latest_mail.stem}_reply.md"
                    reply_path.write_text(reply, encoding="utf-8")
                    logger.info(f"Antwort als Markdown gespeichert: {reply_path}")
                    result_status = f"Datei: {reply_path}"

                processed_results.append({"lastname": email["lastname"], "subject": subject, "status": result_status})

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
