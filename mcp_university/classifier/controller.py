"""Controller für die Verarbeitung und Beantwortung von E-Mails."""

import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
import shutil
import yaml
import extract_msg
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from mcp_university.config import get_config
from mcp_university.summarizer.engine import Summarizer
from mcp_university.parser.mail_parser import MailParser
from mcp_university.summarizer.profiler import PersonProfiler
from mcp_university.agent.engine import Agent
from mcp_university.agent.mcp_agent import MCPAgent
from mcp_university.classifier.engine import resolve_model_path
from mcp_university.utils.semester import get_semester
from mcp_university.classifier.sort_emails import (


    process_emails,
    write_report,
    extract_firstname,

    find_student_folder,
)
from mcp_university.retrieval.index import SearchIndex, get_model
from mcp_university.utils.memory import resolve_memory_index_names
from mcp_university.utils.outlook import create_outlook_draft

logger = logging.getLogger(__name__)


class EmailController:
    """Steuert den Prozess der E-Mail-Verarbeitung, Klassifizierungskorrektur und Antwortgenerierung."""

    ACTION_OPTIONS = [
        "1) Antwort schreiben.",
        "2) Antwort schreiben mit einem Terminvorschlag.",
        "3) Termin im Kalender anlegen und Person dazu einladen.",
        "4) E-Mail nur archivieren.",
        "5) Aufgabe im Kalender anlegen zum Lesen des Anhangs.",
        "6) Termin für Kolloquium in Kalender anlegen.",
    ]

    def __init__(
        self,
        config_path: str = "config/folders.yaml",
        use_mcp: bool = False,
        use_cloud: bool = False,
        cloud_provider: str = "openai",
        cloud_model: str = "gpt-4o",
        api_key: str = None,
        debug: bool = True,
        use_action_classifier: bool = True,
    ) -> None:
        """Initialisiert den EmailController.

        Args:
            config_path (str): Pfad zur Konfigurationsdatei.
            use_mcp (bool): Nutzt den MCP Server für Tools.
            use_cloud (bool): Nutzt ein Cloud-LLM.
            cloud_provider (str): Cloud-LLM Provider.
            cloud_model (str): Cloud-LLM Modell.
            api_key (str): Cloud-LLM API-Key.
            debug (bool): Speichert LLM Prompts als Markdown.
        """
        self.config = get_config()
        self.config_path = config_path
        self.debug = debug
        self.use_action_classifier = use_action_classifier
        self.processed_results = []
        self.mail_parser = MailParser()
        self.summarizer = Summarizer(
            model=self.config.llm.model, base_url=self.config.llm.base_url
        )
        self.profiler = PersonProfiler()

        agent_args = {
            "model": self.config.llm.model,
            "base_url": self.config.llm.base_url,
            "use_cloud": use_cloud,
            "cloud_provider": cloud_provider,
            "cloud_model": cloud_model,
            "api_key": api_key,
        }

        if use_mcp:
            logger.info("Nutze MCP Agent.")
            self.agent = MCPAgent(**agent_args)
        else:
            self.agent = Agent(**agent_args)

        if Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f)
            self.class_paths = full_config.get("class_paths", full_config)
        else:
            logger.warning(f"Config {config_path} not found. Using empty class_paths.")

            self.class_paths = {}

        # Load memory paths
        memory_config_path = Path("config/classifier_memory_paths.yaml")
        self.memory_paths = {}
        self.class_to_memory_index = {}
        if memory_config_path.exists():
            with open(memory_config_path, "r", encoding="utf-8") as f:
                memory_config = yaml.safe_load(f)
                self.memory_paths = memory_config.get("class_paths", {})
                self.class_to_memory_index = resolve_memory_index_names(
                    self.memory_paths
                )

    def _get_memory_context(self, mail_content: str, email_class: str) -> str:
        """Generiert Suchanfragen aus der E-Mail und holt relevante Chunks aus der Vektordatenbank."""
        if email_class not in self.class_to_memory_index:
            logger.debug(
                f"Keine Vektordatenbank für Klasse {email_class} konfiguriert."
            )
            return ""

        index_name = self.class_to_memory_index[email_class]
        index_dir = self.config.data_dir / "memory" / index_name
        if not index_dir.exists():
            logger.debug(f"Vektordatenbank-Verzeichnis {index_dir} existiert nicht.")
            return ""

        logger.info(f"Generiere Suchanfragen für Klasse {email_class}...")

        prompt = f"""Basierend auf der folgenden E-Mail eines Studierenden, erstelle 3 präzise Fragen, die helfen würden, die Anfrage zu beantworten.
Nutze dabei Informationen aus der Mail. Die Fragen sollen dazu dienen, in einer Wissensdatenbank nach passenden Antworten zu suchen.

E-MAIL:
{mail_content}

ANTWORTE NUR MIT DEN 3 FRAGEN, EINE PRO ZEILE, OHNE NUMMERIERUNG."""

        try:
            response = self.summarizer.client.chat(
                system_prompt="Du bist ein hilfreicher Assistent, der Suchanfragen für eine Wissensdatenbank erstellt.",
                messages=[{"role": "user", "content": prompt}],
            )
            questions_text = response.get("message", {}).get("content", "")
            questions = [
                q.strip() for q in questions_text.strip().split("\n") if q.strip()
            ][:3]

            if not questions:
                logger.warning("Keine Suchanfragen generiert.")
                return ""

            logger.info(f"Suchanfragen: {questions}")

            index = SearchIndex(location=index_dir)
            all_results = []
            for query in questions:
                results = index.search(query, top_k=3)
                all_results.extend(results)

            # Top 3 eindeutige Chunks basierend auf Score
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            unique_chunks = []
            seen_content = set()
            for res in all_results:
                if res["content"] not in seen_content:
                    unique_chunks.append(res["content"])
                    seen_content.add(res["content"])
                if len(unique_chunks) >= 3:
                    break

            if not unique_chunks:
                return ""

            context = "\n\n--- RELEVANTE INFORMATIONEN AUS DER DATENBANK ---\n"
            context += "\n\n".join(unique_chunks)
            context += "\n-------------------------------------------------\n"
            return context

        except Exception as e:
            logger.error(f"Fehler bei der Retrieval-Context-Generierung: {e}")
            return ""

    def classify_action(
        self, mail_path: Path, additional_context: str = "", email_class: str = None
    ) -> int:
        """Klassifiziert die E-Mail in eine von 6 Aktions-Optionen."""
        mail_content = self.mail_parser.parse(mail_path)
        mail_content = self.mail_parser.extract_latest_message(mail_content)


        options_str = "\n".join(self.ACTION_OPTIONS)

        system_prompt = "Du bist ein erfahrener Assistent an der TH Köln, der E-Mails effizient verarbeitet."
        user_prompt = f"""Analysiere die folgende E-Mail und wähle GENAU EINE der folgenden Optionen für die weitere Bearbeitung aus:

{options_str}

E-MAIL INHALT:
{mail_content}

ZUSÄTZLICHER KONTEXT:
{additional_context}

WICHTIGE ANWEISUNG:
Antworte NUR mit der Ziffer (1-6) der gewählten Option. Keine weitere Erklärung.
"""

        try:
            response = self.agent.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
            )
            match = re.search(r"([1-6])", response)
            if match:
                return int(match.group(1)) - 1
        except Exception as e:
            logger.error(f"Fehler bei Aktions-Klassifizierung: {e}")

        return 0  # Default: Antwort schreiben

    def execute_action(self, action_idx: int, mail_path: Path, email_data: dict) -> str:
        """Führt die gewählte Aktion für eine E-Mail aus."""
        latest_mail = mail_path
        if action_idx == 3:  # 4) Nur archivieren
            return "E-Mail archiviert."

        student_email = ""
        sender_name = ""
        try:
            with extract_msg.openMsg(str(latest_mail)) as msg:
                student_email = msg.sender
                sender_name = msg.senderName or email_data.get("lastname", "Unbekannt")
        except Exception:
            pass

        person_profile = (
            self.profiler.get_profile(student_email) if student_email else None
        )
        user_profile = self.profiler.get_profile(self.config.user.emails[0])

        first_name = "Unknown"
        try:
            with extract_msg.openMsg(str(latest_mail)) as msg:
                from mcp_university.classifier.sort_emails import extract_firstname

                first_name = extract_firstname(msg.sender)
        except Exception:
            pass

        salutation = f"Guten Tag {self.summarizer.determine_gender(first_name)} {email_data.get('lastname', '')}"
        add_ctx = f"Anrede: {salutation}\n"
        if user_profile:
            add_ctx += (
                f"\nDein eigener Steckbrief (Nutzer des Tools):\n{user_profile}\n"
            )
        if person_profile:
            add_ctx += f"\nPersonen-Steckbrief (Student):\n{person_profile}\n"
        add_ctx += f"Studenten-E-Mail: {student_email}\n"

        persona_path = Path("skills/SKILL_persona.md")
        apt_skill_path = Path("skills/SKILL_Appointment.md")
        skill_path = Path(f"skills/SKILL_{email_data.get('class', 'Other')}.md")
        if not skill_path.exists():
            skill_path = (
                Path(__file__).parent.parent
                / "skills"
                / f"SKILL_{email_data.get('class', 'Other')}.md"
            )

        # Action Logic Mapping
        reply_subject = ""
        reply = ""
        should_attach = False

        # Delayed summary generation
        summary_content = ""
        if action_idx in [0, 1, 2, 4, 5]:  # Reply-related actions
            identifier_path = email_data.get("new_identifier_path") or email_data.get(
                "identifier_path"
            )
            if identifier_path:
                summary_file = identifier_path / ".emails_summary.md"
                # For simplicity, we always re-generate or check freshness here
                # Or just load if exists, and generate if not.
                # Since we want it to be current:
                email_files = list(identifier_path.rglob("*.msg")) + list(
                    identifier_path.rglob("*.eml")
                )
                dated_emails = []
                for f in email_files:
                    try:
                        dated_emails.append((self.mail_parser.get_email_date(f), f))
                    except Exception:
                        dated_emails.append((datetime.min, f))
                dated_emails.sort(key=lambda x: x[0])

                latest_date = dated_emails[-1][0] if dated_emails else datetime.min

                if not summary_file.exists() or latest_date > datetime.fromtimestamp(
                    summary_file.stat().st_mtime
                ):
                    c_content = ""
                    for d, f in dated_emails:
                        p = self.mail_parser.parse(f)
                        if p:
                            c_content += f"\n--- EMAIL VOM {d} ---\n{p}\n"
                    summary_content = self.summarizer.summarize_email_conversation(
                        identifier_path.name, c_content
                    )
                    if summary_content:
                        summary_file.write_text(summary_content, encoding="utf-8")
                else:
                    summary_content = summary_file.read_text(encoding="utf-8")

        reply_subject, reply, should_attach = self.generate_reply(
            latest_mail,
            summary_content,
            skill_path,
            "",
            persona_path,
            add_ctx,
            apt_skill_path,
            sender_name,
            student_email,
            action_idx=action_idx,
            email_class=email_data.get("class"),
        )

        if reply_subject == "NO_REPLY_NEEDED":
            return f"Keine Antwort erforderlich ({reply})"

        if reply.startswith("APPOINTMENT_BOOKED"):
            apt_info = self.agent.last_appointment_info
            if apt_info and "start_time" in apt_info:
                return f"Termin gebucht ({apt_info['start_time']})"

            # If we are here, something went wrong although LLM said APPOINTMENT_BOOKED
            err = getattr(self.agent, "last_tool_error", None)
            return f"Fehler bei Terminbuchung: {err}" if err else "Fehler bei Terminbuchung (Tool wurde nicht erfolgreich aufgerufen)."

        # Entwurf erstellen
        cc_list = []
        try:
            with extract_msg.openMsg(str(latest_mail)) as msg:
                if msg.recipients:
                    for rec in msg.recipients:
                        rec_email = rec.email or rec.name
                        if (
                            rec_email
                            and all(
                                e.lower() not in rec_email.lower()
                                for e in self.config.user.emails
                            )
                            and rec_email.lower() != student_email.lower()
                        ):
                            cc_list.append(rec_email)
        except Exception:
            pass

        attachments = [latest_mail]
        if should_attach and email_data.get("class") == "PO-Wechsel":
            pdf = Path(
                r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf"
            )
            if pdf.exists():
                attachments.append(pdf)

        from mcp_university.utils.outlook import create_outlook_draft

        success = create_outlook_draft(
            reply_subject or latest_mail.stem,
            reply,
            recipient=student_email,
            cc=cc_list,
            attachments=attachments,
        )
        if success:
            return "Outlook Entwurf erstellt"
        else:
            identifier_path = (
                email_data.get("new_identifier_path")
                or email_data.get("identifier_path")
                or latest_mail.parent
            )
            r_path = identifier_path / f"{latest_mail.stem}_reply.md"
            r_path.write_text(reply, encoding="utf-8")
            return f"Datei erstellt: {r_path.name}"

    def run_sort(
        self, source_dir: str, method: str = "transformer", mode: str = "combined"
    ) -> None:
        """Sortiert E-Mails basierend auf Klassifizierung."""
        logger.info(f"Sortiere E-Mails in {source_dir}...")
        source_root = Path(source_dir)
        model_path = resolve_model_path("data/email_classifier.pkl", method, mode)

        if not model_path.exists():
            raise FileNotFoundError(f"Modell-Datei nicht gefunden: {model_path}")

        moved_emails = process_emails(source_root, model_path, self.class_paths)
        write_report(source_root, moved_emails)

    def parse_report(self, report_path: Path) -> List[Dict]:
        """Parst die sorted_emails.md Datei."""
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

                mail_match = re.search(
                    r"- \*\*(.*?)\*\* \| (.*?) \| (.*?): `(.*?)`", line
                )
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

    def relocate_emails(self, email_changes: List[Dict]):
        """Verschiebt E-Mails in neue Ordner basierend auf Benutzerkorrektur."""
        for change in email_changes:
            old_path = Path(change["path"])
            new_class = change["new_class"]
            old_class = change["class"]

            lastname = change["lastname"]
            try:
                date = self.mail_parser.get_email_date(old_path)
            except Exception:
                date = datetime.now()
            semester = get_semester(date)

            if new_class == "Others":
                if change["folder"] == "Inbox":
                    target_dir = Path(r"D:\TH_Koeln\StudentMails2\manuell beantworten")
                elif change["folder"] == "SentItems":
                    target_dir = Path(r"D:\TH_Koeln\StudentMails2\manuell beantwortet")
                else:
                    target_dir = Path(r"D:\TH_Koeln\MailTrainingDataFuture\Others")
            else:
                if new_class not in self.class_paths:
                    logger.error(f"Klasse {new_class} nicht in Konfiguration gefunden.")
                    continue
                class_base_path = Path(self.class_paths[new_class])

                student_dir = find_student_folder(class_base_path, lastname)
                if not student_dir:
                    student_dir = class_base_path / semester / lastname
                target_dir = student_dir / change["folder"]

            target_dir.mkdir(parents=True, exist_ok=True)

            # 1. Save attachments if requested (BEFORE moving the email, but using target info)
            if change.get("save_attachments"):
                # Save to the parent of the target folder (student folder)
                attachment_target = target_dir.parent
                logger.info(
                    f"Speichere Anhänge von {old_path.name} in {attachment_target}"
                )
                self.mail_parser.save_attachments(old_path, attachment_target)

            if new_class == old_class:
                continue

            logger.info(f"Relocating {old_path.name} from {old_class} to {new_class}")

            match = re.match(r"(\d{8}_\d{6})", old_path.name)
            files_to_process = [old_path]
            if match:
                date_prefix = match.group(1)
                for md_file in old_path.parent.glob(f"{date_prefix}*.md"):
                    if md_file != old_path:
                        files_to_process.append(md_file)

            for f in files_to_process:
                dest = target_dir / f.name
                logger.info(f"Verschiebe {f.name} nach {dest}")
                if dest.exists():
                    dest.unlink()
                shutil.move(str(f), str(dest))
                if f == old_path:
                    change["new_path"] = dest
                    change["new_identifier_path"] = target_dir.parent
            old_folder = old_path.parent
            old_student_folder = old_folder.parent
            target_student_folder = target_dir.parent

            def has_emails(student_folder: Path):
                """Prüft, ob der Student-Ordner noch E-Mails enthält."""
                for sub in ["Inbox", "SentItems"]:
                    p = student_folder / sub
                    if p.exists() and p.is_dir():
                        if any(p.glob("*.msg")) or any(p.glob("*.eml")):
                            return True
                return False

            if not has_emails(old_student_folder):
                summary_file = old_student_folder / ".emails_summary.md"
                if not summary_file.exists():
                    summary_file = old_folder / ".emails_summary.md"

                if summary_file.exists():
                    dest_summary = target_student_folder / ".emails_summary.md"
                    if not dest_summary.exists():
                        logger.info(f"Verschiebe Zusammenfassung nach {dest_summary}")
                        shutil.move(str(summary_file), str(dest_summary))
                    else:
                        logger.info(
                            f"Zusammenfassung im Ziel existiert bereits. Lösche {summary_file}"
                        )
                        summary_file.unlink()

            def delete_if_empty(folder: Path):
                """Löscht einen Ordner, wenn er leer ist."""
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

    def generate_reply(
        self,
        mail_path: Path,
        summary_content: str = "",
        skill_path: Path = None,
        conversation_content: str = "",
        persona_path: Path = None,
        additional_context: str = "",
        appointment_skill_path: Path = None,
        sender_name: str = None,
        sender_email: str = None,
        action_idx: int = None,
        email_class: str = None,
    ) -> Tuple[str, str, bool]:
        """Generiert eine Antwortmail mit dem LLM in mehreren Schritten."""
        mail_content = self.mail_parser.parse(mail_path)
        mail_content = self.mail_parser.extract_latest_message(mail_content)
        if action_idx == 3:  # 4) Nur archivieren
            return "NO_REPLY_NEEDED", "Archivieren", False

        if self.debug:
            extracted_file = mail_path.parent / f"{mail_path.stem}_extracted.md"
            extracted_file.write_text(mail_content, encoding="utf-8")


        appointment_skill_content = ""
        if appointment_skill_path and appointment_skill_path.exists():
            appointment_skill_content = appointment_skill_path.read_text(
                encoding="utf-8"
            )

        persona_content = ""
        if persona_path and persona_path.exists():
            persona_content = persona_path.read_text(encoding="utf-8")

        system_prompt = "Du bist ein hilfreicher Assistent an der TH Köln. Verfasse eine Antwort-E-Mail auf Deutsch."

        # Action-specific flags
        skip_step1 = False
        force_appointment_slots = False
        force_calendar_booking = False
        force_colloquium = False
        skip_step12 = False
        force_final_submission = False

        if action_idx is not None:
            if action_idx == 0:  # 1) Antwort schreiben
                skip_step1 = True
                skip_step12 = True
            elif action_idx == 1:  # 2) Antwort schreiben mit Terminvorschlag
                force_appointment_slots = True
                skip_step12 = True
            elif action_idx == 2:  # 3) Termin im Kalender anlegen
                force_calendar_booking = True
                skip_step12 = True
            elif action_idx == 4:  # 5) Aufgabe im Kalender / Finale Abgabe
                skip_step1 = True
                force_final_submission = True
            elif action_idx == 5:  # 6) Termin für Kolloquium
                force_colloquium = True
                skip_step12 = True

        # STEP 1: APPOINTMENT
        if not skip_step1:
            logger.info("Schritt 1: Prüfe Terminrelevanz...")

            forced_instr = ""
            if force_appointment_slots:
                forced_instr = "\nERZWUNGENE AKTION: Diese E-Mail ist eine Terminanfrage. Du MUSST ZWINGEND get_appointment_slots aufrufen."
            elif force_calendar_booking:
                forced_instr = "\nERZWUNGENE AKTION: Diese E-Mail bestätigt einen Termin. Du MUSST ZWINGEND manage_calendar_appointment aufrufen."
            elif force_colloquium:
                forced_instr = "\nERZWUNGENE AKTION: Diese E-Mail bestätigt ein Kolloquium (60 Min). Du MUSST ZWINGEND manage_calendar_appointment aufrufen."

            appointment_user_prompt = f"""Du bist ein Tool-Calling-Agent. Deine EINZIGE Aufgabe ist es, basierend auf der E-Mail und dem TERMINVERWALTUNG SKILL die korrekte Aktion auszuführen.

HEUTE IST: {datetime.now(ZoneInfo("Europe/Berlin")).strftime("%A, den %d.%m.%Y %H:%M")}

PERSONA:
{persona_content}

TERMINVERWALTUNG SKILL:
{appointment_skill_content}

ZUSÄTZLICHER KONTEXT:
{additional_context}

AKTUELLE E-MAIL:
{mail_content}{forced_instr}

WICHTIGE ANWEISUNGEN:
- Wenn eine Terminbestätigung vorliegt: Rufe SOFORT das Tool 'manage_calendar_appointment' auf. Gib KEINE textuelle Analyse oder Erklärung ab. Antworte EXAKT mit 'APPOINTMENT_BOOKED' erst NACHDEM das Tool 'ERFOLG' gemeldet hat.
- Wenn eine Terminanfrage vorliegt: Rufe SOFORT das Tool 'get_appointment_slots' auf. Gib KEINE textuelle Analyse oder Erklärung ab.
- Wenn KEIN Bezug zu Terminen vorliegt: Antworte EXAKT mit 'NO_APPOINTMENT_RELEVANCE'.

VERBOTE:
- Antworte NIEMALS mit einer Analyse des Skills.
- Antworte NIEMALS mit Sätzen wie "Basierend auf der Analyse...".
- Wenn ein Tool-Call nötig ist, darf deine Antwort NUR aus dem Tool-Call bestehen.
"""
            try:
                content = self.agent.chat(
                    messages=[{"role": "user", "content": appointment_user_prompt}],
                    system_prompt=system_prompt,
                    sender_name=sender_name,
                    sender_email=sender_email,
                )
                if "APPOINTMENT_BOOKED" in content:
                    apt_info = self.agent.last_appointment_info
                    if apt_info and "start_time" in apt_info:
                        apt_text = f"APPOINTMENT_BOOKED|{apt_info['start_time']}"
                        return "APPOINTMENT_BOOKED", apt_text, False

                    # Tool call failed or was not made
                    err = getattr(self.agent, "last_tool_error", None)
                    err_msg = f"FEHLER: Termin konnte nicht gebucht werden. {err}" if err else "FEHLER: Terminbuchungs-Tool wurde nicht aufgerufen."
                    return "APPOINTMENT_BOOKING_FAILED", err_msg, False
                if "NO_APPOINTMENT_RELEVANCE" not in content:
                    should_attach = "ANHANG: JA" in content
                    reply_subject = (
                        content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip()
                        if "BETREFF:" in content
                        else ""
                    )
                    reply_text = (
                        content.split("TEXT:", 1)[1].strip()
                        if "TEXT:" in content
                        else content
                    )
                    return reply_subject, reply_text, should_attach
            except Exception as e:
                logger.error(f"Fehler in Schritt 1 (Appointment): {e}")

        # STEP 1.2: FINAL SUBMISSION
        fs_skill_path = Path("skills/SKILL_FinalSubmission.md")
        if not fs_skill_path.exists():
            fs_skill_path = (
                Path(__file__).parent.parent / "skills" / "SKILL_FinalSubmission.md"
            )

        if not skip_step12 and fs_skill_path.exists():
            logger.info("Schritt 1.2: Prüfe auf finale Abgabe...")
            fs_content = fs_skill_path.read_text(encoding="utf-8")

            forced_instr = ""
            if force_final_submission:
                forced_instr = "\nERZWUNGENE AKTION: Dies ist eine finale Abgabe. Du MUSST ZWINGEND manage_calendar_appointment und save_email_attachments aufrufen."

            fs_prompt = f"""Prüfe die folgende E-Mail auf eine finale Abgabe basierend auf dem FINALE ABGABE SKILL.

HEUTE IST: {datetime.now(ZoneInfo("Europe/Berlin")).strftime("%A, den %d.%m.%Y %H:%M")}

FINALE ABGABE SKILL:
{fs_content}

AKTUELLE E-MAIL:
{mail_content}
PFAD ZUR E-MAIL: {mail_path}{forced_instr}

WICHTIGE ANWEISUNG:
1. Falls es eine finale Abgabe ist: Rufe ZUERST die Tools `manage_calendar_appointment` und `save_email_attachments` auf.
2. Falls es KEINE finale Abgabe ist, antworte EXAKT mit: NO_FINAL_SUBMISSION_RELEVANCE
"""
            try:
                content = self.agent.chat(
                    messages=[{"role": "user", "content": fs_prompt}],
                    system_prompt=system_prompt,
                    sender_name=sender_name,
                    sender_email=sender_email,
                )
                if "NO_FINAL_SUBMISSION_RELEVANCE" not in content:
                    should_attach = "ANHANG: JA" in content
                    reply_subject = (
                        content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip()
                        if "BETREFF:" in content
                        else ""
                    )
                    reply_text = (
                        content.split("TEXT:", 1)[1].strip()
                        if "TEXT:" in content
                        else content
                    )
                    return reply_subject, reply_text, should_attach
            except Exception as e:
                logger.error(f"Fehler in Schritt 1.2 (FinalSubmission): {e}")

        # STEP 1.5: NECESSITY (only if not forced)
        if action_idx is None:
            logger.info("Schritt 1.5: Prüfe Notwendigkeit...")
            nec_prompt = f"""Prüfe, ob die E-Mail eine Antwort erfordert.
PERSONA: {persona_content}
KONTEXT: {additional_context}
E-MAIL: {mail_content}
- Falls KEINE Antwort nötig, antworte EXAKT: NO_REPLY_NEEDED|BEGRÜNDUNG
- Sonst: REPLY_NEEDED
"""
            try:
                content = self.agent.chat(
                    messages=[{"role": "user", "content": nec_prompt}],
                    system_prompt=system_prompt,
                    sender_name=sender_name,
                    sender_email=sender_email,
                )
                if content.startswith("NO_REPLY_NEEDED"):
                    return (
                        "NO_REPLY_NEEDED",
                        content.split("|", 1)[1]
                        if "|" in content
                        else "Keine Begründung",
                        False,
                    )
            except Exception:
                pass

        # Retrieval memory logic
        if email_class:
            retrieved_context = self._get_memory_context(mail_content, email_class)
            if retrieved_context:
                additional_context += retrieved_context

        # STEP 2: REGULAR REPLY
        logger.info("Schritt 2: Generiere reguläre Antwort...")
        skill_content = (
            skill_path.read_text(encoding="utf-8")
            if skill_path and skill_path.exists()
            else ""
        )
        reg_prompt = f"""Verfasse eine Antwort auf die folgende E-Mail basierend auf der PERSONA und dem SKILL.

PERSONA:
{persona_content}

SKILL:
{skill_content}

KONTEXT:
{additional_context}
{summary_content}

AKTUELLE E-MAIL:
{mail_content}

WICHTIGE ANWEISUNGEN:
- Formatiere die Antwort im folgenden Format:
ANHANG: [JA/NEIN]
BETREFF: [Passender Betreff]
TEXT:
[Der Antworttext]
"""
        try:
            content = self.agent.chat(
                messages=[{"role": "user", "content": reg_prompt}],
                system_prompt=system_prompt,
                sender_name=sender_name,
                sender_email=sender_email,
            )
            should_attach = "ANHANG: JA" in content
            reply_subject = (
                content.split("BETREFF:", 1)[1].split("TEXT:", 1)[0].strip()
                if "BETREFF:" in content
                else ""
            )
            reply_text = (
                content.split("TEXT:", 1)[1].strip() if "TEXT:" in content else content
            )
            return reply_subject, reply_text, should_attach
        except Exception as e:
            logger.error(f"Fehler in Schritt 2: {e}")
            return "", "Fehler bei der Generierung.", False

    def process_all_emails(
        self, source_dir: Path, age_months: Optional[int] = None
    ) -> List[Dict]:
        """Verarbeitet alle sortierten E-Mails im Quellverzeichnis."""
        report_path = source_dir / "sorted_emails.md"
        emails = self.parse_report(report_path)
        logger.info(f"{len(emails)} sortierte E-Mails gefunden.")

        emails_to_process = []

        for email in emails:
            mail_path = Path(email["path"])
            identifier = mail_path.parent.parent
            email_files = list(identifier.rglob("*.msg")) + list(
                identifier.rglob("*.eml")
            )
            if not email_files:
                continue
            dated_emails = []
            for f in email_files:
                try:
                    dated_emails.append((self.mail_parser.get_email_date(f), f))
                except Exception:
                    dated_emails.append((datetime.min, f))
            dated_emails.sort(key=lambda x: x[0])
            latest_date, latest_mail = dated_emails[-1]
            # Individual email in SentItems never needs an answer
            if email.get("folder") == "SentItems":
                needs_answer = False
            else:
                needs_answer = (
                    "Inbox" in latest_mail.parts and "SentItems" not in latest_mail.parts
                )
            email.update(
                {
                    "latest_date": latest_date,
                    "latest_mail": latest_mail,
                    "dated_emails": dated_emails,
                    "identifier_path": identifier,
                    "needs_answer": needs_answer,
                }
            )
            emails_to_process.append(email)

        emails_to_process_path = source_dir / "emails_to_process.md"
        with open(emails_to_process_path, "w", encoding="utf-8") as f:
            f.write("# Zu beantwortende E-Mails\n\n| Student | Klasse | Semester |\n| :--- | :--- | :--- |\n")
            for email in emails_to_process:
                f.write(f"| {email['lastname']} | {email['class']} | {email['semester']} |\n")

        
        persona_path = Path("skills/SKILL_persona.md")
        apt_skill_path = Path("skills/SKILL_Appointment.md")

        for email in emails_to_process:
            latest_mail = email["latest_mail"]
            latest_date = email["latest_date"]

            # Check if email is old
            is_old = False
            if age_months:
                cutoff = (datetime.now() - timedelta(days=age_months * 30)).replace(
                    tzinfo=None
                )
                if latest_date.replace(tzinfo=None) < cutoff:
                    is_old = True

            # Standard suggested action: Archive if old, sent, or already answered
            is_sent = email.get("folder") == "SentItems"
            needs_answer = email.get("needs_answer", True)

            if is_old or is_sent or not needs_answer:
                if is_old:
                    reason = f"alt (> {age_months} Monate)"
                elif is_sent:
                    reason = "im SentItems Ordner"
                else:
                    reason = "bereits beantwortet"
                logger.info(
                    f"E-Mail von {email['lastname']} ist {reason}. Automatische Aktion: Archivieren."
                )
                email["suggested_action"] = 3  # index for "4) E-Mail nur archivieren"
            elif self.use_action_classifier:
                email["suggested_action"] = self.classify_action(
                    latest_mail, email_class=email["class"]
                )
            else:
                email["suggested_action"] = 0  # Default: Antwort schreiben

            if self.use_action_classifier:
                continue

            # Legacy processing (only if use_action_classifier is False)
            if is_old:
                self.processed_results.append(
                    {
                        "lastname": email["lastname"],
                        "subject": latest_mail.stem,
                        "status": f"Übersprungen (> {age_months} Monate)",
                    }
                )
                continue

            if not needs_answer:
                self.processed_results.append(
                    {
                        "lastname": email["lastname"],
                        "subject": latest_mail.stem,
                        "status": "Bereits beantwortet (Übersprungen)",
                    }
                )
                continue

            student_email = ""
            sender_name = ""
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    student_email = msg.sender
                    sender_name = msg.senderName or email["lastname"]
            except Exception:
                pass

            person_profile = (
                self.profiler.get_profile(student_email) if student_email else None
            )
            user_profile = self.profiler.get_profile(self.config.user.emails[0])
            cc_list = []
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    if msg.recipients:
                        for rec in msg.recipients:
                            rec_email = rec.email or rec.name
                            if (
                                rec_email
                                and all(
                                    e.lower() not in rec_email.lower()
                                    for e in self.config.user.emails
                                )
                                and rec_email.lower() != student_email.lower()
                            ):
                                cc_list.append(rec_email)
            except Exception:
                pass

            skill_path = Path(f"skills/SKILL_{email['class']}.md")
            if not skill_path.exists():
                skill_path = (
                    Path(__file__).parent.parent
                    / "skills"
                    / f"SKILL_{email['class']}.md"
                )

            first_name = "Unknown"
            try:
                with extract_msg.openMsg(str(latest_mail)) as msg:
                    first_name = extract_firstname(msg.sender)
            except Exception:
                pass

            salutation = f"Guten Tag {self.summarizer.determine_gender(first_name)} {email['lastname']}"
            add_ctx = f"Anrede: {salutation}\n"
            if user_profile:
                add_ctx += (
                    f"\nDein eigener Steckbrief (Nutzer des Tools):\n{user_profile}\n"
                )
            if person_profile:
                add_ctx += f"\nPersonen-Steckbrief (Student):\n{person_profile}\n"
            add_ctx += f"Studenten-E-Mail: {student_email}\n"

            if email["class"] == "PO-Wechsel":
                pdf_path = Path(
                    r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf"
                )
                if pdf_path.exists():
                    add_ctx += f"\nDu kannst bei Bedarf Details aus der Datei '{pdf_path}' mittels des read_file Tools auslesen.\n"

            # Conversation summary is now delayed until execute_action/generate_reply
            summary_content = ""
            conv_content = ""

            reply_subject, reply, should_attach = self.generate_reply(
                latest_mail,
                summary_content,
                skill_path,
                conv_content,
                persona_path,
                add_ctx,
                apt_skill_path,
                sender_name,
                student_email,
                email_class=email["class"],
            )

            if reply_subject == "NO_REPLY_NEEDED":
                self.processed_results.append(
                    {
                        "lastname": email["lastname"],
                        "subject": latest_mail.stem,
                        "status": f"Keine Antwort erforderlich ({reply})",
                    }
                )
                continue

            if reply.startswith("APPOINTMENT_BOOKED"):
                apt_info = self.agent.last_appointment_info
                status = f"Termin gebucht ({apt_info['start_time']})"
                self.processed_results.append(
                    {
                        "lastname": email["lastname"],
                        "subject": latest_mail.stem,
                        "status": status,
                    }
                )
                continue

            if reply.startswith("APPOINTMENT_BOOKING_FAILED"):
                self.processed_results.append(
                    {
                        "lastname": email["lastname"],
                        "subject": latest_mail.stem,
                        "status": reply,
                    }
                )
                continue

            attachments = [latest_mail]
            if should_attach and email["class"] == "PO-Wechsel":
                pdf = Path(
                    r"D:\TH_Koeln\PAV\Studierende\PO-Wechsel\InfosPOWechselHärtefall.pdf"
                )
                if pdf.exists():
                    attachments.append(pdf)

            success = create_outlook_draft(
                reply_subject or latest_mail.stem,
                reply,
                recipient=student_email,
                cc=cc_list,
                attachments=attachments,
            )
            if success:
                res_status = "Outlook Entwurf (Work in Progress)"
            else:
                r_path = email["identifier_path"] / f"{latest_mail.stem}_reply.md"
                r_path.write_text(reply, encoding="utf-8")
                res_status = f"Datei: {r_path}"

            self.processed_results.append(
                {
                    "lastname": email["lastname"],
                    "subject": latest_mail.stem,
                    "status": res_status,
                }
            )

        # Always return emails_to_process for GUI consistency

        if self.processed_results:
            self.write_processed_report(source_dir, self.processed_results)

        return emails_to_process

    def write_processed_report(self, source_dir: Path, results: list):
        """Schreibt den Abschlussbericht über verarbeitete E-Mails.

        Args:
            source_dir (Path): Quellverzeichnis.
            results (list): Liste von Dictionaries mit 'lastname', 'subject', 'status'.

        Returns:
            None
        """
        if not results:
            return

        report_path = source_dir / "processed_emails.md"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("# Verarbeitete E-Mails")
                f.write("| Student | Betreff | Status |")
                f.write("| :--- | :--- | :--- |")
                for res in results:
                    n_v = res.get("lastname", "Unknown")
                    s_v = res.get("subject", "No Subject")
                    t_v = res.get("status", "Unknown")
                    f.write(f"| {n_v} | {s_v} | {t_v} |\n")
            logger.info(f"Bericht in {report_path} geschrieben.")
        except Exception as e:
            logger.error(f"Fehler beim Schreiben des Berichts: {e}")

    def generate_short_summary(self, mail_path: Path) -> str:
        """Generiert eine kurze Zusammenfassung (2 Sätze) einer E-Mail."""
        try:
            parsed = self.mail_parser.parse(mail_path)
            if not parsed:
                return "Keine Zusammenfassung möglich."

            prompt = f"Fasse die folgende E-Mail in genau 2 prägnanten Sätzen zusammen:\n\n{parsed}"

            response = self.summarizer.client.chat(
                system_prompt="Du bist ein hilfreicher Assistent, der E-Mails kurz zusammenfasst.",
                messages=[{"role": "user", "content": prompt}],
            )

            content_v = response.get("message", {}).get("content", "")
            return content_v.strip() or "Zusammenfassung fehlgeschlagen."
        except Exception as e:
            logger.error(f"Fehler bei der Kurzzusammenfassung: {e}")
            return "Fehler bei Zusammenfassung."

    def get_similarity_info(self, mail_path: Path, lastname: str) -> str:
        """Findet die ähnlichsten E-Mails desselben Studenten in den konfigurierten Pfaden.

        Args:
            mail_path: Pfad zur aktuellen E-Mail.
            lastname: Nachname des Studenten.

        Returns:
            str: Markdown-formatierte Information über die ähnlichste E-Mails.
        """
        try:
            # 1. Details der aktuellen Mail
            current_details = self.mail_parser.get_email_details(mail_path)
            current_subject = current_details.get("subject", "")
            if not current_subject:
                return "Kein Betreff in aktueller Mail gefunden."

            # 2. Alle relevanten Mails des Studenten in allen Klassen-Pfaden suchen
            all_mails = []
            seen_paths = set()

            for class_name, base_path_str in self.class_paths.items():
                base_path = Path(base_path_str)
                student_dir = find_student_folder(base_path, lastname)
                if student_dir:
                    for ext in ["*.msg", "*.eml"]:
                        for f in student_dir.rglob(ext):
                            resolved_f = f.resolve()
                            if (
                                resolved_f == mail_path.resolve()
                                or resolved_f in seen_paths
                            ):
                                continue
                            try:
                                date = self.mail_parser.get_email_date(f)
                                details = self.mail_parser.get_email_details(f)
                                if details.get("subject"):
                                    all_mails.append(
                                        {
                                            "path": f,
                                            "date": date,
                                            "subject": details.get("subject"),
                                        }
                                    )
                                    seen_paths.add(resolved_f)
                            except Exception:
                                continue

            if not all_mails:
                return "Keine anderen E-Mails des Studenten in den Archiv-Ordnern gefunden."

            # 3. Die 3 neuesten nehmen
            all_mails.sort(key=lambda x: x["date"], reverse=True)
            newest_mails = all_mails[:3]

            # 4. Embeddings und Similarity

            model_name = self.config.embeddings.model

            # Lazy load similarity model on controller using shared cache
            if not hasattr(self, "_similarity_model"):
                self._similarity_model = get_model(
                    model_name, offline=self.config.offline
                )

            subjects = [m["subject"] for m in newest_mails]

            curr_emb = self._similarity_model.encode([current_subject])
            other_embs = self._similarity_model.encode(subjects)
            
                        
            similarities = cosine_similarity(curr_emb, other_embs)[0]
            best_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])
            best_mail = newest_mails[best_idx]

            return (
                f"**Ähnlichste Mail (Top 3 neuere):** {best_mail['subject']}\n\n"
                f"**Pfad:** `{best_mail['path']}`\n\n"
                f"**Cosine Similarity:** {best_score:.4f}"
            )

        except Exception as e:
            logger.error(f"Fehler bei Similarity-Suche für {lastname}: {e}")
            return f"*Fehler bei Similarity-Suche: {str(e)}*"
