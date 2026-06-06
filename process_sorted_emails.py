"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""
import argparse
import logging
import platform
import subprocess
import extract_msg
import yaml
from mcp_university.classifier.sort_emails import (process_emails, write_report, extract_lastname, extract_firstname, get_semester, find_student_folder)
import re
import shutil
import gradio as gr
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
        source_dir (str): Quellordner mit den E-Mails.
        config_path (str): Pfad zur Konfigurationsdatei.
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
        report_path (Path): Pfad zum Markdown-Report.

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



def relocate_emails(email_changes: List[Dict], config: Dict):
    """Verschiebt E-Mails in neue Ordner basierend auf Benutzerkorrektur.

    Args:
        email_changes: Liste von Dicts mit Pfad und neuer Klasse.
        config: Klassen-Pfad-Konfiguration.
    """
    mail_parser = MailParser()
    for change in email_changes:
        old_path = Path(change['path'])
        new_class = change['new_class']
        old_class = change['class']

        if new_class == old_class:
            continue

        lastname = change['lastname']
        logger.info(f"Relocating {old_path.name} from {old_class} to {new_class}")

        if new_class == "Others":
            class_base_path = Path(r"D:\TH_Koeln\MailTrainingDataFuture\Others")
        else:
            if new_class not in config:
                logger.error(f"Klasse {new_class} nicht in Konfiguration gefunden.")
                continue
            class_base_path = Path(config[new_class])

        try:
            date = mail_parser.get_email_date(old_path)
        except Exception:
            date = datetime.now()
        semester = get_semester(date)

        if new_class == "Others":
            target_dir = class_base_path
        elif new_class.startswith(("BA_", "MA_")):
            target_dir = class_base_path / semester / change['folder']
        else:
            student_dir = find_student_folder(class_base_path, lastname)
            if not student_dir:
                student_dir = class_base_path / semester / lastname
            target_dir = student_dir / change['folder']

        target_dir.mkdir(parents=True, exist_ok=True)

        # Finde zugehörige Dateien (gleicher Zeitstempel-Präfix)
        match = re.match(r"(\d{8}_\d{6})", old_path.name)
        files_to_process = [old_path]
        if match:
            date_prefix = match.group(1)
            for md_file in old_path.parent.glob(f"{date_prefix}*.md"):
                if md_file != old_path:
                    files_to_process.append(md_file)

        for f in files_to_process:
            if new_class == "Others" and f.suffix == ".md":
                logger.info(f"Lösche {f.name}")
                f.unlink()
            else:
                dest = target_dir / f.name
                logger.info(f"Verschiebe {f.name} nach {dest}")
                if dest.exists():
                    dest.unlink()
                shutil.move(str(f), str(dest))

        # Aufräumen
        old_folder = old_path.parent
        summary_file = old_folder / ".emails_summary.md"
        if summary_file.exists():
            summary_file.unlink()

        def delete_if_empty(folder: Path):
            if folder.exists() and folder.is_dir():
                items = list(folder.iterdir())
                if not items:
                    logger.info(f"Lösche leeren Ordner {folder}")
                    folder.rmdir()
                    return True
            return False

        if delete_if_empty(old_folder):
            parent_folder = old_folder.parent
            if parent_folder.name == lastname:
                delete_if_empty(parent_folder)

def run_gradio_gui(report_path: Path, config: Dict):
    """Startet die Gradio GUI zur Korrektur der Einsortierung.

    Args:
        report_path: Pfad zum sorted_emails.md Report.
        config: Klassen-Pfad-Konfiguration.
    """
    emails = parse_sorted_report(report_path)
    if not emails:
        logger.info("Keine E-Mails zum Anzeigen im Gradio GUI.")
        return

    available_classes = sorted(list(config.keys())) + ["Others"]

    with gr.Blocks(title="E-Mail Sortierung Überprüfung") as demo:
        gr.Markdown("# E-Mail Sortierung Überprüfung")
        gr.Markdown("Bitte kontrollieren Sie die automatisch vorgenommene Einsortierung.")

        dropdowns = []
        email_data = []

        for mail in emails:
            with gr.Group():
                with gr.Row():
                    with gr.Column(scale=4):
                        gr.Markdown(f"**Student:** {mail['lastname']} ({mail['semester']}) | **Ordner:** {mail['folder']}\n**Datei:** `{mail['path'].name}`")
                    with gr.Column(scale=1):
                        dd = gr.Dropdown(choices=available_classes, value=mail['class'], label="Korrektes Ziel")
                        dropdowns.append(dd)
                        email_data.append(mail)

        with gr.Row():
            btn = gr.Button("Mails neu einsortieren", variant="primary")
            status_out = gr.Textbox(label="Ergebnis")

        def handle_click(*selected_classes):
            changes = []
            for mail, new_class in zip(email_data, selected_classes):
                m = mail.copy()
                m['new_class'] = new_class
                changes.append(m)

            try:
                relocate_emails(changes, config)
                return "Verarbeitung abgeschlossen. Mails wurden ggf. verschoben und Ordner bereinigt."
            except Exception as e:
                logger.exception("Fehler bei Relokation")
                return f"Fehler: {str(e)}"

        btn.click(handle_click, inputs=dropdowns, outputs=status_out)

    demo.launch(inbrowser=True)


def create_outlook_draft(subject: str, body: str, recipient: str = "", cc: List[str] = None, attachments: List[Path] = None) -> bool:
    """Erstellt einen E-Mail-Entwurf in Outlook.

    Args:
        subject (str): Betreff der E-Mail.
        body (str): Inhalt der E-Mail.
        recipient (str): Empfänger-Adresse.
        cc (List[str], optional): Liste der CC-Adressen. Defaults to None.
        attachments (List[Path], optional): Liste der Dateipfade für Anhänge. Defaults to None.

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

        target_account = get_config().user.email
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
            logger.info(f"Erstelle Entwurf direkt in {target_account} -> {target_folder_name}.")
        else:
            mail = outlook.CreateItem(0)
            logger.warning(f"Zielordner {target_folder_name} nicht gefunden. Erstelle in Standard-Entwürfen.")

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

def generate_reply(agent, mail_path: Path, summary_content: str = "", skill_path: Path = None, conversation_content: str = "", persona_path: Path = None, additional_context: str = "", debug: bool = False, appointment_skill_path: Path = None, sender_name: str = None, sender_email: str = None) -> Tuple[str, str, bool]:
    """Generiert eine Antwortmail mit dem LLM in zwei Schritten:
    1. Prüfung auf Terminrelevanz (Appointment Skill).
    2. Falls nicht relevant, klassenspezifische Antwort mit vollem Kontext.

    Args:
        agent: Agent-Instanz.
        mail_path (Path): Pfad zur aktuellen E-Mail.
        summary_content (str): Inhalt der bisherigen Zusammenfassung.
        skill_path (Path, optional): Pfad zur SKILL-Datei.
        conversation_content (str, optional): Verlauf des Schriftverkehrs.
        persona_path (Path, optional): Pfad zur Persona-Datei.
        additional_context (str, optional): Zusätzlicher Kontext.
        debug (bool): Ob Debug-Informationen gespeichert werden sollen.
        appointment_skill_path (Path, optional): Pfad zum Terminverwaltungs-Skill.
        sender_name (str, optional): Name des Absenders (für Anonymisierung).
        sender_email (str, optional): E-Mail des Absenders (für Anonymisierung).

    Returns:
        Tuple[str, str, bool]: (Betreff, Antwort-Text, Soll ein Anhang angehängt werden?).
    """
    parser = MailParser()
    mail_content = parser.parse(mail_path)
    mail_content = parser.extract_latest_message(mail_content)

    if debug:
        extracted_file = mail_path.parent / f"{mail_path.stem}_extracted.md"
        extracted_file.write_text(mail_content, encoding="utf-8")

        # Wenn Cloud/Anonymisierung aktiv ist, speichern wir die anonymisierte Fassung
        if agent.use_cloud and agent.anonymizer and sender_name and sender_email:
            anonymized_content = agent.anonymizer.anonymize(mail_content, sender_name, sender_email)
            anon_file = mail_path.parent / f"{mail_path.stem}_anonymized.md"
            anon_file.write_text(anonymized_content, encoding="utf-8")
            logger.info(f"Anonymisierte Mail gespeichert: {anon_file}")

    appointment_skill_content = ""
    if appointment_skill_path and appointment_skill_path.exists():
        appointment_skill_content = appointment_skill_path.read_text(encoding="utf-8")
        logger.info(f"Appointment-Skill-Datei geladen: {appointment_skill_path.name}")

    persona_content = ""
    if persona_path and persona_path.exists():
        persona_content = persona_path.read_text(encoding="utf-8")

    system_prompt = "Du bist ein hilfreicher Assistent an der TH Köln. Verfasse eine Antwort-E-Mail auf Deutsch."

    # --- SCHRITT 1: TERMINVERWALTUNG ---
    logger.info("Schritt 1: Prüfe Terminrelevanz...")
    appointment_user_prompt = f"""Prüfe die folgende E-Mail auf Terminrelevanz (Anfrage oder Bestätigung) basierend auf dem TERMINVERWALTUNG SKILL.

HEUTE IST: {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%A, den %d.%m.%Y %H:%M')}

PERSONA:
{persona_content}

TERMINVERWALTUNG SKILL:
{appointment_skill_content}

ZUSÄTZLICHER KONTEXT (Anrede etc.):
{additional_context}

AKTUELLE E-MAIL:
{mail_content}

WICHTIGE ANWEISUNG:
1. Falls die E-Mail EINEN TERMIN BESTÄTIGT: RUFE ZWINGEND das Tool 'manage_calendar_appointment' auf. Du MUSST ALLE erforderlichen Parameter (start_time, end_time, subject, student_email) übergeben. Achte auf das korrekte JAHR (2026). Bei Kolloquien muss die Dauer 60 Minuten betragen. Erst wenn das Tool 'ERFOLG' zurückgibt, antworte EXAKT mit 'APPOINTMENT_BOOKED'. Antworte NIEMALS mit 'APPOINTMENT_BOOKED' ohne vorher das Tool erfolgreich aufgerufen zu haben!
2. Falls die E-Mail EINEN TERMIN ANFRAGT: Du MUSST ZWINGEND das Tool 'get_appointment_slots' aufrufen, um die verfügbaren Terminvorschläge zu erhalten und diese in die Antwort einzubinden. Antworte erst, nachdem du das Tool aufgerufen und die Daten erhalten hast.
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
            messages=[{'role': 'user', 'content': appointment_user_prompt}],
            system_prompt=system_prompt,
            sender_name=sender_name,
            sender_email=sender_email
        )
        logger.info(f"Antwort von Agent (Appointment-Check): {content}")

        if "APPOINTMENT_BOOKED" in content:
            apt_info = agent.last_appointment_info
            apt_text = "APPOINTMENT_BOOKED"
            if apt_info and "start_time" in apt_info:
                apt_text = f"APPOINTMENT_BOOKED|{apt_info['start_time']}"
            return "APPOINTMENT_BOOKED", apt_text, False

        if "NO_APPOINTMENT_RELEVANCE" not in content:
            logger.info("Terminrelevanz erkannt, generiere Termin-Antwort.")
            should_attach = "ANHANG: JA" in content
            reply_subject = ""
            if "BETREFF:" in content:
                reply_subject = content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip()
            reply_text = content
            if "TEXT:" in content:
                reply_text = content.split("TEXT:", 1)[1].strip()
            return reply_subject, reply_text, should_attach

    except Exception as e:
        logger.error(f"Fehler in Schritt 1 (Appointment): {e}")

    # --- SCHRITT 1.5: NOTWENDIGKEITSPRÜFUNG ---
    logger.info("Schritt 1.5: Prüfe, ob eine Antwort notwendig ist...")
    necessity_user_prompt = f"""Prüfe, ob die folgende E-Mail eine Antwort erfordert oder ob es sich lediglich um eine Informationsmail handelt, die keiner Antwort bedarf.

PERSONA:
{persona_content}

ZUSÄTZLICHER KONTEXT (Anrede etc.):
{additional_context}

AKTUELLE E-MAIL:
{mail_content}

WICHTIGE ANWEISUNG:
- Falls die E-Mail KEINE Antwort erfordert (z.B. reine Bestätigung ohne Fragen, reine Information, Dankesmail ohne weitere Anliegen), antworte EXAKT im Format: NO_REPLY_NEEDED|BEGRÜNDUNG
- Falls die E-Mail eine Antwort erfordert, antworte EXAKT mit: REPLY_NEEDED
"""
    try:
        necessity_content = agent.chat(
            messages=[{"role": "user", "content": necessity_user_prompt}],
            system_prompt=system_prompt,
            sender_name=sender_name,
            sender_email=sender_email
        )
        logger.info(f"Antwort von Agent (Necessity-Check): {necessity_content}")

        if necessity_content.startswith("NO_REPLY_NEEDED"):
            reason = necessity_content.split("|", 1)[1] if "|" in necessity_content else "Keine Begründung angegeben."
            return "NO_REPLY_NEEDED", reason, False
    except Exception as e:
        logger.error(f"Fehler in Schritt 1.5 (Necessity-Check): {e}")
    # --- SCHRITT 2: REGULÄRE ANTWORT ---
    logger.info("Schritt 2: Generiere reguläre Antwort mit vollem Kontext...")

    skill_content = "Keine spezifischen Anweisungen vorhanden."
    if skill_path and skill_path.exists():
        skill_content = skill_path.read_text(encoding="utf-8")
        logger.info(f"Klassenspezifische Skill geladen: {skill_path.name}")

    context_label = "SCHRIFTVERKEHR DER LETZTEN 2 WOCHEN" if conversation_content else "ZUSAMMENFASSUNG DES SCHRIFTVERKEHRS"
    context_body = conversation_content if conversation_content else summary_content

    regular_user_prompt = f"""Basierend auf der folgenden E-Mail, dem Kontext des bisherigen Schriftverkehrs, der Persona und den Skill-Anweisungen, verfasse eine professionelle Antwort.

HEUTE IST: {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%A, den %d.%m.%Y %H:%M')}

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
        prompt_content = f"# System Prompt\n{system_prompt}\n\n# User Prompt\n{regular_user_prompt}"
        prompt_file.write_text(prompt_content, encoding="utf-8")

    try:
        content = agent.chat(
            messages=[{'role': 'user', 'content': regular_user_prompt}],
            system_prompt=system_prompt,
            sender_name=sender_name,
            sender_email=sender_email
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
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    file_handler = logging.FileHandler(config.log_path / "process_emails.log", encoding="utf-8")
    stream_handler = logging.StreamHandler()

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[file_handler, stream_handler],
        force=True # Vorhandene Konfiguration überschreiben
    )

    parser = argparse.ArgumentParser(description="Verarbeitet sortierte E-Mails und generiert Antworten.")
    parser.add_argument("source_dir", help="Quellordner der E-Mails")
    parser.add_argument("--config", default="config/folders.yaml", help="Pfad zur Konfiguration")
    parser.add_argument("--debug", action="store_true", default=DEBUG, help="Speichert LLM Prompts als Markdown (Default: True)")
    parser.add_argument("--no-debug", action="store_false", dest="debug", help="Deaktiviert das Speichern von Prompts")
    parser.add_argument("--use-mcp", action="store_true", help="Nutzt den MCP Server für Tools")
    parser.add_argument("--use-cloud", action="store_true", help="Nutzt ein Cloud-LLM (mit Anonymisierung)")
    parser.add_argument("--cloud-provider", default="openai", help="Cloud-LLM Provider")
    parser.add_argument("--cloud-model", default="gpt-4o", help="Cloud-LLM Modell")
    parser.add_argument("--api-key", help="Cloud-LLM API-Key")
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

    agent_args = {
        "model": config.llm.model,
        "base_url": config.llm.base_url,
        "use_cloud": args.use_cloud,
        "cloud_provider": args.cloud_provider,
        "cloud_model": args.cloud_model,
        "api_key": args.api_key
    }

    if args.use_mcp:
        logger.info("Nutze MCP Agent.")
        agent = MCPAgent(**agent_args)
    else:
        agent = Agent(**agent_args)

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
            needs_answer = "Inbox" in latest_mail.parts

            # Bereicherung des E-Mail-Dicts für spätere Verarbeitung
            email["latest_date"] = latest_date
            email["latest_mail"] = latest_mail
            email["student_emails"] = student_emails
            email["semester_folder"] = semester_folder
        else:
            identifier = mail_path.parent.parent
            # Normal student folder logic
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
            needs_answer = "Inbox" in latest_mail.parts and "SentItems" not in latest_mail.parts

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
            f.write("| {} | {} | {} |\n".format(email["lastname"], email["class"], email["semester"]))
    logger.info(f"Liste der zu beantwortenden E-Mails erstellt: {emails_to_process_path}")

    persona_path = Path("skills/SKILL_persona.md")
    appointment_skill_path = Path("skills/SKILL_Appointment.md")

    for email in unique_emails_to_process:
        latest_mail = email["latest_mail"]
        latest_date = email["latest_date"]
        is_ba_ma = email["class"].startswith(("BA_", "MA_"))

        student_email = ""
        sender_name = ""
        try:
            with extract_msg.openMsg(str(latest_mail)) as msg:
                student_email = msg.sender
                sender_name = msg.senderName or email["lastname"]
        except Exception:
            pass

        if is_ba_ma:
            semester_folder = email["semester_folder"]
            student_emails = email["student_emails"]

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

            # Extraktion von Empfänger und CC
            cc_list = []
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    if msg.recipients:
                        for rec in msg.recipients:
                            rec_email = rec.email or rec.name
                            if rec_email and get_config().user.email not in rec_email.lower():
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
                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email['class']}.md"

            # Zusätzlicher Kontext (z.B. PO-Wechsel)
            additional_context = f"Anrede: {salutation}\n"
            additional_context += f"Studenten-E-Mail: {student_email}\n"
            attachments = []
            if email["class"] == "PO-Wechsel":
                pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                if pdf_path.exists():
                    additional_context += f"\nDu kannst bei Bedarf Details aus der Datei '{pdf_path}' mittels des read_file Tools auslesen.\n"

            reply_subject, reply, should_attach = generate_reply(agent, latest_mail, skill_path=skill_path, conversation_content=conversation_content, persona_path=persona_path, additional_context=additional_context, debug=args.debug, appointment_skill_path=appointment_skill_path, sender_name=sender_name, sender_email=student_email)

            if reply_subject == "NO_REPLY_NEEDED":
                logger.info(f"Keine Antwort für {email['lastname']} erforderlich. Grund: {reply}")
                status = f"Keine Antwort erforderlich ({reply})"
                processed_results.append({"lastname": email['lastname'], "subject": latest_mail.stem, "status": status})
                continue

            if reply.startswith("APPOINTMENT_BOOKED"):
                apt_info = agent.last_appointment_info
                if apt_info and "start_time" in apt_info:
                    apt_time = apt_info['start_time']
                    logger.info(f"ERFOLG: Termin für {email['lastname']} wurde am {apt_time} im Kalender gebucht.")
                    status = f"Termin gebucht ({apt_time})"
                else:
                    # Fallback
                    apt_time = reply.split("|")[1] if "|" in reply else ""
                    logger.info(f"Termin für {email['lastname']} wurde erfolgreich gebucht{f' am {apt_time}' if apt_time else ''}.")
                    status = f"Termin gebucht ({apt_time})" if apt_time else "Termin gebucht (Kalender)"

                processed_results.append({"lastname": email["lastname"], "subject": latest_mail.stem, "status": status})
                continue

            attachments.append(latest_mail)
            if should_attach and email["class"] == "PO-Wechsel":
                pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                if pdf_path.exists():
                    attachments.append(pdf_path)

            # Speichere Antwort
            subject = latest_mail.stem
            success = create_outlook_draft(reply_subject or subject, reply, recipient=student_email, cc=cc_list, attachments=attachments)
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

            logger.info(f"Generiere Antwort für neueste Mail in {identifier.name}: {latest_mail.name}")

            # Extraktion von Empfänger und CC
            cc_list = []
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    if msg.recipients:
                        for rec in msg.recipients:
                            rec_email = rec.email or rec.name
                            if rec_email and get_config().user.email not in rec_email.lower():
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
                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email['class']}.md"

            additional_context = f"Anrede: {salutation}\n"
            additional_context += f"Studenten-E-Mail: {student_email}\n"
            attachments = []
            if email["class"] == "PO-Wechsel":
                pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                if pdf_path.exists():
                    additional_context += f"\nDu kannst bei Bedarf Details aus der Datei '{pdf_path}' mittels des read_file Tools auslesen.\n"

            reply_subject, reply, should_attach = generate_reply(agent, latest_mail, summary_content or "", skill_path, persona_path=persona_path, additional_context=additional_context, debug=args.debug, appointment_skill_path=appointment_skill_path, sender_name=sender_name, sender_email=student_email)

            if reply_subject == "NO_REPLY_NEEDED":
                logger.info(f"Keine Antwort für {email['lastname']} erforderlich. Grund: {reply}")
                status = f"Keine Antwort erforderlich ({reply})"
                processed_results.append({"lastname": email['lastname'], "subject": latest_mail.stem, "status": status})
                continue

            if reply.startswith("APPOINTMENT_BOOKED"):
                apt_info = agent.last_appointment_info
                if apt_info and "start_time" in apt_info:
                    apt_time = apt_info['start_time']
                    logger.info(f"ERFOLG: Termin für {email['lastname']} wurde am {apt_time} im Kalender gebucht.")
                    status = f"Termin gebucht ({apt_time})"
                else:
                    # Fallback
                    apt_time = reply.split("|")[1] if "|" in reply else ""
                    logger.info(f"Termin für {email['lastname']} wurde erfolgreich gebucht{f' am {apt_time}' if apt_time else ''}.")
                    status = f"Termin gebucht ({apt_time})" if apt_time else "Termin gebucht (Kalender)"

                processed_results.append({"lastname": email["lastname"], "subject": latest_mail.stem, "status": status})
                continue

            attachments.append(latest_mail)
            if should_attach and email["class"] == "PO-Wechsel":
                pdf_path = Path(r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf")
                if pdf_path.exists():
                    attachments.append(pdf_path)

            subject = latest_mail.stem
            success = create_outlook_draft(reply_subject or subject, reply, recipient=student_email, cc=cc_list, attachments=attachments)
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



    # 4. Gradio GUI zur Überprüfung der Sortierung
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f)
        class_paths = full_config.get("class_paths", full_config)
        run_gradio_gui(report_path, class_paths)
    except Exception as e:
        logger.error(f"Fehler beim Starten der Gradio GUI: {e}")



if __name__ == "__main__":
    main()
