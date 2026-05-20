"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""
import argparse
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

try:
    import win32com.client
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False

from mcp_university.config import get_config
from mcp_university.summarizer.engine import Summarizer
from mcp_university.parser.mail_parser import MailParser

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_sort_emails(source_dir: str, config_path: str) -> None:
    """Führt das sort_emails.py Skript aus.

    Args:
        source_dir: Quellordner mit den E-Mails.
        config_path: Pfad zur Konfigurationsdatei.
    """
    logger.info(f"Führe sort_emails.py für {source_dir} aus...")
    cmd = ["python3", "-m", "mcp_university.classifier.sort_emails", source_dir, "--config", config_path]
    subprocess.run(cmd, check=True)

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

def create_outlook_draft(subject: str, body: str, recipient: str = "") -> bool:
    """Erstellt einen E-Mail-Entwurf in Outlook.

    Args:
        subject: Betreff der E-Mail.
        body: Inhalt der E-Mail.
        recipient: Empfänger-Adresse.

    Returns:
        bool: True wenn erfolgreich, sonst False.
    """
    if not OUTLOOK_AVAILABLE:
        logger.info("pywin32 nicht installiert. Outlook-Draft nicht möglich.")
        return False

    try:
        # Check if Outlook is running
        try:
            outlook = win32com.client.GetActiveObject("Outlook.Application")
        except Exception:
            logger.info("Outlook ist nicht geöffnet.")
            return False

        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.Subject = f"Re: {subject}"
        mail.Body = body
        if recipient:
            mail.To = recipient
        mail.Save()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Outlook-Entwurfs: {e}")
        return False

def generate_reply(summarizer: Summarizer, mail_path: Path, summary_content: str, skill_path: Path) -> str:
    """Generiert eine Antwortmail mit dem LLM.

    Args:
        summarizer: Summarizer-Instanz.
        mail_path: Pfad zur aktuellen E-Mail.
        summary_content: Inhalt der bisherigen Zusammenfassung.
        skill_path: Pfad zur SKILL-Datei.

    Returns:
        str: Der generierte Antwort-Text.
    """
    parser = MailParser()
    mail_content = parser.parse(mail_path)

    skill_content = "Keine spezifischen Anweisungen vorhanden."
    if skill_path.exists():
        skill_content = skill_path.read_text(encoding="utf-8")

    system_prompt = "Du bist ein hilfreicher Assistent an der TH Köln. Verfasse eine Antwort-E-Mail auf Deutsch."
    user_prompt = f"""Basierend auf der folgenden E-Mail, der bisherigen Zusammenfassung des Schriftverkehrs und den Skill-Anweisungen, verfasse eine professionelle Antwort.

SKILL ANWEISUNGEN:
{skill_content}

ZUSAMMENFASSUNG DES SCHRIFTVERKEHRS:
{summary_content}

AKTUELLE E-MAIL:
{mail_content}

Antworte NUR mit dem Text der E-Mail.
"""
    try:
        response = summarizer.client.chat(
            model=summarizer.model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        return response['message']['content']
    except Exception as e:
        logger.error(f"Fehler bei LLM-Generierung: {e}")
        return "Fehler bei der Generierung der Antwort."

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

    # Wir tracken verarbeitete student_folders, um Mehrfachverarbeitung zu vermeiden
    processed_folders = set()

    for email in emails:
        mail_path = Path(email["path"])
        # Pfadstruktur: .../Klasse/Semester/Nachname/Inbox/mail.msg
        student_folder = mail_path.parent.parent

        if student_folder in processed_folders:
            continue
        processed_folders.add(student_folder)

        summary_file = student_folder / ".emails_summary.md"

        # 1. Update/Create Summary
        email_files = list(student_folder.rglob("*.msg")) + list(student_folder.rglob("*.eml"))
        if not email_files:
            continue

        # Sortiere chronologisch
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
            logger.info(f"Erstelle/Aktualisiere Zusammenfassung für {student_folder.name}")
            conv_content = ""
            for date, f in dated_emails:
                p = mail_parser.parse(f)
                if p:
                    conv_content += f"\n--- EMAIL VOM {date} ---\n{p}\n"

            summary_content = summarizer.summarize_email_conversation(student_folder.name, conv_content)
            if summary_content:
                summary_file.write_text(summary_content, encoding="utf-8")
        else:
            summary_content = summary_file.read_text(encoding="utf-8")

        # 2. Generate Reply if newest mail is in Inbox
        if "Inbox" in latest_mail.parts and "SentItems" not in latest_mail.parts:
            logger.info(f"Generiere Antwort für neueste Mail in {student_folder.name}: {latest_mail.name}")

            skill_path = Path(f"skills/SKILL_{email['class']}.md")
            reply = generate_reply(summarizer, latest_mail, summary_content or "", skill_path)

            # Outlook Draft or Markdown
            subject = latest_mail.stem
            success = create_outlook_draft(subject, reply)
            if success:
                logger.info(f"Outlook-Entwurf für {latest_mail.name} erstellt.")
            else:
                reply_path = student_folder / f"{latest_mail.stem}_reply.md"
                reply_path.write_text(reply, encoding="utf-8")
                logger.info(f"Antwort als Markdown gespeichert: {reply_path}")

if __name__ == "__main__":
    main()
