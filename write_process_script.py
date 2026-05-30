import os
content = r'''"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""
import argparse
import logging
import platform
import subprocess
import extract_msg
import yaml
from mcp_university.classifier.sort_emails import process_emails, write_report, extract_lastname, extract_firstname
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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
from mcp_university.agent.mcp_agent import MCPAgent

# Globaler Logger
logger = logging.getLogger(__name__)

DEBUG = True

def is_outlook_open() -> bool:
    system = platform.system()
    try:
        if system == "Windows":
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq outlook.exe"', shell=True, stderr=subprocess.STDOUT)
            return b"outlook.exe" in output.lower()
        elif system == "Darwin":
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
    logger.info(f"Sortiere E-Mails in {source_dir}...")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if config and "class_paths" in config:
        config = config["class_paths"]
    source_root = Path(source_dir)
    model_path = Path("data/email_classifier_combined.pkl")
    moved_emails = process_emails(source_root, model_path, config)
    write_report(source_root, moved_emails)

def parse_sorted_report(report_path: Path) -> List[Dict]:
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
                    "class": current_class, "semester": mail_match.group(1),
                    "lastname": mail_match.group(2), "folder": mail_match.group(3),
                    "path": Path(mail_match.group(4))
                })
    return emails

def create_outlook_draft(subject: str, body: str, recipient: str = "", cc: List[str] = None, attachments: List[Path] = None) -> bool:
    if not OUTLOOK_AVAILABLE or not is_outlook_open():
        return False
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        target_account = "daniel.gaida@th-koeln.de"
        target_folder_name = "Work in Progress"
        target_folder = None
        for store in namespace.Stores:
            if store.DisplayName == target_account:
                root = store.GetRootFolder()
                for folder in root.Folders:
                    if folder.Name.lower() == target_folder_name.lower():
                        target_folder = folder
                        break
                if not target_folder:
                    for folder in root.Folders:
                        if folder.Name.lower() in ["posteingang", "inbox"]:
                            for sub in folder.Folders:
                                if sub.Name.lower() == target_folder_name.lower():
                                    target_folder = sub
                                    break
                        if target_folder: break
                if target_folder: break
        mail = target_folder.Items.Add(0) if target_folder else outlook.CreateItem(0)
        mail.Subject = subject
        mail.Body = body
        if attachments:
            for p in attachments:
                if p.exists(): mail.Attachments.Add(str(p))
        if recipient: mail.To = recipient
        if cc: mail.CC = "; ".join(cc)
        mail.Save()
        mail.Display(False)
        return True
    except Exception as e:
        logger.error(f"Outlook Fehler: {e}")
        return False

def generate_reply(agent, mail_path: Path, summary_content: str = "", skill_path: Path = None, conversation_content: str = "", persona_path: Path = None, additional_context: str = "", debug: bool = False, appointment_skill_path: Path = None, sender_name: str = None, sender_email: str = None) -> Tuple[str, str, bool]:
    parser = MailParser()
    mail_content = parser.parse(mail_path)
    mail_content = parser.extract_latest_message(mail_content)
    if debug:
        (mail_path.parent / f"{mail_path.stem}_extracted.md").write_text(mail_content, encoding="utf-8")

    apt_skill_content = appointment_skill_path.read_text(encoding="utf-8") if appointment_skill_path and appointment_skill_path.exists() else ""
    persona_content = persona_path.read_text(encoding="utf-8") if persona_path and persona_path.exists() else ""
    system_prompt = "Du bist ein hilfreicher Assistent an der TH Köln. Verfasse eine Antwort-E-Mail auf Deutsch."

    logger.info("Schritt 1: Prüfe Terminrelevanz...")
    apt_prompt = f"""Prüfe auf Terminrelevanz basierend auf TERMINVERWALTUNG SKILL.

HEUTE IST: {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%A, %d.%m.%Y %H:%M')}

PERSONA:
{persona_content}

SKILL:
{apt_skill_content}

KONTEXT:
{additional_context}

MAIL:
{mail_content}

ANWEISUNG: 1. Termin bestätigt -> Tool 'manage_calendar_appointment' -> 'APPOINTMENT_BOOKED'. 2. Termin angefragt -> Tool 'get_appointment_slots'. 3. Sonst -> 'NO_APPOINTMENT_RELEVANCE'.

Format: ANHANG: [JA/NEIN]
BETREFF: [Betreff]
TEXT: [Text]"""

    try:
        content = agent.chat(messages=[{'role': 'user', 'content': apt_prompt}], system_prompt=system_prompt, sender_name=sender_name, sender_email=sender_email)
        if "APPOINTMENT_BOOKED" in content:
            apt_info = agent.last_appointment_info
            return "APPOINTMENT_BOOKED", f"APPOINTMENT_BOOKED|{apt_info['start_time']}" if apt_info else "APPOINTMENT_BOOKED", False
        if "NO_APPOINTMENT_RELEVANCE" not in content:
            subject = content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip() if "BETREFF:" in content else ""
            text = content.split("TEXT:", 1)[1].strip() if "TEXT:" in content else content
            return subject, text, "ANHANG: JA" in content
    except Exception as e:
        logger.error(f"Schritt 1 Fehler: {e}")

    logger.info("Schritt 2: Reguläre Antwort...")
    skill_content = skill_path.read_text(encoding="utf-8") if skill_path and skill_path.exists() else "Keine Anweisungen."
    ctx_label = "SCHRIFTVERKEHR" if conversation_content else "ZUSAMMENFASSUNG"
    ctx_body = conversation_content or summary_content
    reg_prompt = f"""Verfasse Antwort.

HEUTE IST: {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%A, %d.%m.%Y %H:%M')}

PERSONA:
{persona_content}

SKILL:
{skill_content}

KONTEXT:
{additional_context}

{ctx_label}:
{ctx_body}

MAIL:
{mail_content}

Format: ANHANG: [JA/NEIN]
BETREFF: [Betreff]
TEXT: [Text]"""

    try:
        content = agent.chat(messages=[{'role': 'user', 'content': reg_prompt}], system_prompt=system_prompt, sender_name=sender_name, sender_email=sender_email)
        subject = content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip() if "BETREFF:" in content else ""
        text = content.split("TEXT:", 1)[1].strip() if "TEXT:" in content else content
        return subject, text, "ANHANG: JA" in content
    except Exception as e:
        logger.error(f"Schritt 2 Fehler: {e}")
        return "", "Fehler bei Generierung.", False

def main() -> None:
    config = get_config()
    config.log_path.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(config.log_path / "process_emails.log", encoding="utf-8"), logging.StreamHandler()], force=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir")
    parser.add_argument("--config", default="config/folders.yaml")
    parser.add_argument("--debug", action="store_true", default=True)
    parser.add_argument("--use-mcp", action="store_true")
    parser.add_argument("--use-cloud", action="store_true")
    parser.add_argument("--cloud-provider", default="openai")
    parser.add_argument("--cloud-model", default="gpt-4o")
    parser.add_argument("--api-key")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    try: run_sort_emails(str(source_dir), args.config)
    except Exception as e: logger.error(f"Sortierfehler: {e}")

    report_path = source_dir / "sorted_emails.md"
    emails = parse_sorted_report(report_path)
    logger.info(f"{len(emails)} E-Mails gefunden.")

    summarizer = Summarizer(model=config.llm.model, base_url=config.llm.base_url)

    if args.use_mcp:
        agent = MCPAgent(model=config.llm.model, base_url=config.llm.base_url, use_cloud=args.use_cloud, cloud_provider=args.cloud_provider, cloud_model=args.cloud_model, api_key=args.api_key)
    else:
        agent = Agent(model=config.llm.model, base_url=config.llm.base_url, use_cloud=args.use_cloud, cloud_provider=args.cloud_provider, cloud_model=args.cloud_model, api_key=args.api_key)

    mail_parser = MailParser()
    processed_results = []
    unique_emails = []
    seen_folders = set()

    for email in emails:
        mail_path = Path(email["path"])
        is_ba_ma = email["class"].startswith(("BA_", "MA_"))
        if is_ba_ma:
            semester_folder = mail_path.parent.parent
            inbox = semester_folder / "Inbox"
            sent = semester_folder / "SentItems"
            files = list(inbox.glob("*.msg")) + list(inbox.glob("*.eml")) + list(sent.glob("*.msg")) + list(sent.glob("*.eml"))
            student_emails = []
            for f in files:
                try:
                    with extract_msg.openMsg(str(f)) as msg:
                        if extract_lastname(msg.sender) == email["lastname"] or (msg.recipients and extract_lastname(msg.recipients[0].name or msg.recipients[0].email) == email["lastname"]):
                            student_emails.append((mail_parser.get_email_date(f), f))
                except: continue
            if not student_emails: continue
            student_emails.sort(key=lambda x: x[0])
            latest_date, latest_mail = student_emails[-1]
            needs_answer = "Inbox" in latest_mail.parts
            email.update({"latest_date": latest_date, "latest_mail": latest_mail, "student_emails": student_emails, "semester_folder": semester_folder})
            ident = (email["class"], email["semester"], email["lastname"])
        else:
            ident = mail_path.parent.parent
            files = list(ident.rglob("*.msg")) + list(ident.rglob("*.eml"))
            if not files: continue
            dated = []
            for f in files:
                try: dated.append((mail_parser.get_email_date(f), f))
                except: dated.append((datetime.min, f))
            dated.sort(key=lambda x: x[0])
            latest_date, latest_mail = dated[-1]
            needs_answer = "Inbox" in latest_mail.parts and "SentItems" not in latest_mail.parts
            email.update({"latest_date": latest_date, "latest_mail": latest_mail, "dated_emails": dated, "identifier_path": ident})

        if needs_answer and ident not in seen_folders:
            seen_folders.add(ident)
            unique_emails.append(email)

    persona_path = Path("skills/SKILL_persona.md")
    apt_skill_path = Path("skills/SKILL_Appointment.md")

    for email in unique_emails:
        latest_mail = email["latest_mail"]
        is_ba_ma = email["class"].startswith(("BA_", "MA_"))

        student_email = ""
        sender_name = ""
        try:
            with extract_msg.openMsg(str(latest_mail)) as msg:
                student_email = msg.sender
                sender_name = msg.senderName or email["lastname"]
        except: pass

        if is_ba_ma:
            recent = [e for e in email["student_emails"] if e[0] >= email["latest_date"] - timedelta(days=14)]
            conv = "".join([f"\n--- EMAIL VOM {d} ---\n{mail_parser.parse(f)}\n" for d, f in recent if f != latest_mail])
            salutation = f"Guten Tag {summarizer.determine_gender(extract_firstname(student_email))} {email['lastname']}"
            ctx = f"Anrede: {salutation}\nStudenten-E-Mail: {student_email}\n"
            reply_subject, reply, attach = generate_reply(agent, latest_mail, skill_path=Path(f"skills/SKILL_{email['class']}.md"), conversation_content=conv, persona_path=persona_path, additional_context=ctx, debug=args.debug, appointment_skill_path=apt_skill_path, sender_name=sender_name, sender_email=student_email)
        else:
            summary_file = email["identifier_path"] / ".emails_summary.md"
            if not summary_file.exists() or email["latest_date"] > datetime.fromtimestamp(summary_file.stat().st_mtime):
                conv = "".join([f"\n--- EMAIL VOM {d} ---\n{mail_parser.parse(f)}\n" for d, f in email["dated_emails"]])
                summary = summarizer.summarize_email_conversation(email["identifier_path"].name, conv)
                if summary: summary_file.write_text(summary, encoding="utf-8")
            summary_content = summary_file.read_text(encoding="utf-8")
            salutation = f"Guten Tag {summarizer.determine_gender(extract_firstname(student_email))} {email['lastname']}"
            ctx = f"Anrede: {salutation}\nStudenten-E-Mail: {student_email}\n"
            reply_subject, reply, attach = generate_reply(agent, latest_mail, summary_content=summary_content, skill_path=Path(f"skills/SKILL_{email['class']}.md"), persona_path=persona_path, additional_context=ctx, debug=args.debug, appointment_skill_path=apt_skill_path, sender_name=sender_name, sender_email=student_email)

        if reply.startswith("APPOINTMENT_BOOKED"):
            processed_results.append({"lastname": email["lastname"], "subject": latest_mail.stem, "status": "Termin gebucht"})
            continue

        attachments = [latest_mail]
        if attach and email["class"] == "PO-Wechsel":
            p = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
            if p.exists(): attachments.append(p)

        success = create_outlook_draft(reply_subject or latest_mail.stem, reply, recipient=student_email, attachments=attachments)
        processed_results.append({"lastname": email["lastname"], "subject": latest_mail.stem, "status": "Outlook Draft" if success else "Markdown File"})

    if processed_results:
        with open(source_dir / "processed_emails.md", "w", encoding="utf-8") as f:
            f.write("# Verarbeitete E-Mails\n\n| Student | Betreff | Status |\n| :--- | :--- | :--- |\n")
            for res in processed_results: f.write(f"| {res['lastname']} | {res['subject']} | {res['status']} |\n")

if __name__ == "__main__":
    main()
'''
with open('process_sorted_emails.py', 'w', encoding='utf-8') as f:
    f.write(content)
