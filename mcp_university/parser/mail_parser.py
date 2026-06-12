"""Parser für E-Mail-Formate."""
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import email
from email import policy
from email.utils import parsedate_to_datetime
from datetime import datetime
from ..config import get_config
logging.getLogger("extract_msg").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

class MailParser:
    """Extrahiert Text aus E-Mail-Dateien (.eml, .msg)."""

    def parse(self, file_path: Path) -> Optional[str]:
        """Parsen einer E-Mail und Extraktion von Header und Body.

        Args:
            file_path: Pfad zur E-Mail-Datei.

        Returns:
            Extrahierter Text oder None bei Fehlern.
        """
        suffix = file_path.suffix.lower()

        if suffix == ".msg":
            return self._parse_msg(file_path)
        else:
            return self._parse_eml(file_path)

    def get_email_date(self, file_path: Path) -> datetime:
        """Extrahiert das Datum der E-Mail für die Sortierung.

        Args:
            file_path: Pfad zur E-Mail-Datei.

        Returns:
            datetime: Das Datum der E-Mail oder datetime.min bei Fehlern.
        """
        # Vorab-Check: Datum im Dateinamen (z.B. 20260222_201613 - ...)
        match = re.match(r"^(\d{8})_(\d{6})", file_path.name)
        if match:
            try:
                return datetime.strptime(match.group(0), "%Y%m%d_%H%M%S")
            except ValueError:
                logger.debug(f"Could not parse date from filename: {file_path.name}")

        suffix = file_path.suffix.lower()
        if suffix == ".msg":
            try:
                import extract_msg
                with extract_msg.openMsg(str(file_path)) as msg:
                    if msg.date:
                        if isinstance(msg.date, datetime):
                            return msg.date
                        # Falls es doch ein String ist (unwahrscheinlich bei extract-msg)
                        return parsedate_to_datetime(str(msg.date))
            except Exception as e:
                logger.debug(f"Could not extract date from .msg {file_path}: {e}")

        # Fallback for .eml or failed .msg
        try:
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)
                date_str = msg.get('Date')
                if date_str:
                    return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.debug(f"Could not extract date from .eml {file_path}: {e}")

        # Final fallback: mtime
        try:
            return datetime.fromtimestamp(file_path.stat().st_mtime)
        except Exception:
            return datetime.min

    def extract_latest_message(self, text: str) -> str:
        """Extrahiert den neuesten Teil einer E-Mail-Konversation.

        Sucht nach typischen Trennern von Antwort-Historien und gibt nur den Text
        oberhalb des ersten Trenners zurück.

        Args:
            text: Der vollständige Text der E-Mail.

        Returns:
            str: Der extrahierte neueste Teil der E-Mail.
        """
        if not text:
            return ""

        lines = text.splitlines()

        # Regex patterns
        cfg = get_config()
        user_email_esc = re.escape(cfg.user.email)
        date_wrote_pattern = re.compile(r"(Am|On) .* (schrieb|wrote):?", re.IGNORECASE)
        from_gaida_pattern = re.compile(rf"From: .*{user_email_esc}", re.IGNORECASE)
        zitat_pattern = re.compile(rf"Zitat von .*{user_email_esc}:?", re.IGNORECASE)

        def is_header_marker(line: str) -> bool:
            """Prüft, ob eine Zeile ein Header-Marker für eine Antwort ist."""
            return (zitat_pattern.search(line) is not None or
                    "-------- Weitergeleitete Nachricht --------" in line or
                    "-----Original Message-----" in line or
                    date_wrote_pattern.search(line) is not None or
                    from_gaida_pattern.search(line) is not None)

        # 1. Führende Zitate überspringen (Bottom-Posting)
        start_index = 0
        first_content_line_idx = -1
        for i, line in enumerate(lines):
            if line.strip():
                first_content_line_idx = i
                break

        did_skip_start = False
        if first_content_line_idx != -1:
            first_line = lines[first_content_line_idx]
            is_marker = is_header_marker(first_line) or first_line.strip().startswith(">")

            if is_marker:
                for i in range(first_content_line_idx, len(lines)):
                    line = lines[i]
                    if line.strip().startswith(">") or is_header_marker(line) or not line.strip():
                        continue
                    else:
                        start_index = i
                        did_skip_start = True
                        break

        # 2. Inhalt extrahieren
        new_lines = []
        quote_count = 0
        marker_found = False
        for i in range(start_index, len(lines)):
            line = lines[i]
            if is_header_marker(line):
                marker_found = True
                break

            if line.strip().startswith(">"):
                quote_count += 1
            else:
                quote_count = 0

            if quote_count >= 2:
                marker_found = True
                if new_lines:
                    new_lines.pop()
                break

            new_lines.append(line)

        extracted_text = "\n".join(new_lines).strip()

        # Fallback Logic
        extracted_lines_count = len([line for line in extracted_text.splitlines() if line.strip()])

        # Wenn wir Bottom-Posting hatten (am Anfang geskippt) oder ein Marker gefunden wurde,
        # vertrauen wir dem Ergebnis.
        if did_skip_start or marker_found:
            return extracted_text

        # Wenn wir Top-Posting haben und kein Marker gefunden wurde,
        # nehmen wir das Original als Sicherheit, falls das Ergebnis EXTREM kurz ist.
        if extracted_lines_count < 2:
            # Nur fall-back wenn wir wirklich etwas weggeschnitten haben
            original_lines_count = len([line for line in text.splitlines() if line.strip()])
            if original_lines_count > extracted_lines_count:
                return text.strip()

        return extracted_text

    def _parse_msg(self, file_path: Path) -> Optional[str]:
        """Parsen einer Outlook .msg Datei mit extract-msg."""
        try:
            import extract_msg
            with extract_msg.openMsg(str(file_path)) as msg:
                subject = msg.subject or '(No Subject)'
                sender = msg.sender or '(No Sender)'
                date = msg.date or '(No Date)'
                body = msg.body or ''

                attachment_names = []
                for att in msg.attachments:
                    name = None
                    if hasattr(att, "getFilename"):
                        try:
                            name = att.getFilename()
                        except Exception:
                            pass

                    if not name:
                        name = getattr(att, "name", None) or getattr(att, "longFilename", None)

                    if name:
                        attachment_names.append(name)

                content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"
                if attachment_names:
                    content += "\n\nAnhänge:\n" + "\n".join(attachment_names)
                return content
        except ImportError:
            logger.warning("extract-msg not installed. Falling back to basic email parser for .msg file.")
            return self._parse_eml(file_path)
        except Exception as e:
            logger.error(f"Error parsing .msg mail {file_path}: {e}")
            # Try fallback to standard email parser as a last resort
            return self._parse_eml(file_path)

    def _parse_eml(self, file_path: Path) -> Optional[str]:
        """Parsen einer .eml Datei mit dem Standard-email Modul."""
        try:
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)

            subject = msg.get('Subject', '(No Subject)')
            sender = msg.get('From', '(No Sender)')
            date = msg.get('Date', '(No Date)')

            body = ""
            attachment_names = []
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body += payload.decode(charset)
                        except (UnicodeDecodeError, LookupError):
                            body += payload.decode('latin-1', errors='replace')
                    elif "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachment_names.append(filename)
            else:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                try:
                    body = payload.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    body = payload.decode('latin-1', errors='replace')

            content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"
            if attachment_names:
                content += "\n\nAnhänge:\n" + "\n".join(attachment_names)
            return content
        except Exception as e:
            logger.error(f"Error parsing mail {file_path}: {e}")
            return None

    def get_email_details(self, file_path: Path) -> Dict[str, Any]:
        """Extrahiert detaillierte Informationen aus einer E-Mail.

        Args:
            file_path: Pfad zur E-Mail-Datei.

        Returns:
            Dict[str, Any]: Ein Dictionary mit date, from_email, from_name, to, cc, subject, body.
        """
        suffix = file_path.suffix.lower()
        if suffix == ".msg":
            return self._get_msg_details(file_path)
        else:
            return self._get_eml_details(file_path)

    def _get_msg_details(self, file_path: Path) -> Dict[str, Any]:
        """Extrahiert Details aus einer .msg Datei.

        Args:
            file_path: Pfad zur Datei.

        Returns:
            Dict[str, Any]: Extrahierte Details.
        """
        try:
            import extract_msg
            with extract_msg.openMsg(str(file_path)) as msg:
                # Basic info
                date = msg.date
                if not isinstance(date, datetime):
                    date = self.get_email_date(file_path)

                subject = msg.subject or ""
                body = msg.body or ""

                # Sender
                from_email = msg.sender
                from_name = ""
                if from_email and "<" in from_email:
                    match = re.search(r"(.*?)\s*<(.*?)>", from_email)
                    if match:
                        from_name = match.group(1).strip().strip('"').strip("'")
                        from_email = match.group(2).strip().lower()
                else:
                    from_email = (from_email or "").strip().lower()

                # Recipients
                to = []
                cc = []
                if hasattr(msg, "recipients"):
                    for rec in msg.recipients:
                        # Depending on extract-msg version, rec might be an object or a dict
                        rec_email = getattr(rec, "email", None) or getattr(rec, "email_address", None)
                        rec_name = getattr(rec, "name", "")
                        rec_type = str(getattr(rec, "type", "")).lower()

                        rec_dict = {"name": rec_name, "email": rec_email.lower() if rec_email else ""}
                        if "to" in rec_type:
                            to.append(rec_dict)
                        elif "cc" in rec_type:
                            cc.append(rec_dict)

                return {
                    "date": date,
                    "from_email": from_email,
                    "from_name": from_name,
                    "to": to,
                    "cc": cc,
                    "subject": subject,
                    "body": body
                }
        except Exception as e:
            logger.error(f"Error getting .msg details {file_path}: {e}")
            return self._get_eml_details(file_path)

    def _get_eml_details(self, file_path: Path) -> Dict[str, Any]:
        """Extrahiert Details aus einer .eml Datei.

        Args:
            file_path: Pfad zur Datei.

        Returns:
            Dict[str, Any]: Extrahierte Details.
        """
        try:
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)

            date_str = msg.get('Date')
            try:
                date = parsedate_to_datetime(date_str) if date_str else self.get_email_date(file_path)
            except Exception:
                date = self.get_email_date(file_path)

            subject = msg.get('Subject', '')

            # Helper to parse addresses
            def parse_addr(header_name):
                addrs = msg.get_all(header_name, [])
                parsed = []
                for addr in addrs:
                    addr_str = str(addr)
                    # Basic parsing for "Name <email>"
                    match = re.search(r"(.*?)\s*<(.*?)>", addr_str)
                    if match:
                        parsed.append({"name": match.group(1).strip().strip('"').strip("'"), "email": match.group(2).strip().lower()})
                    else:
                        parsed.append({"name": "", "email": addr_str.strip().lower()})
                return parsed

            from_header = str(msg.get('From', ''))
            from_match = re.search(r"(.*?)\s*<(.*?)>", from_header)
            if from_match:
                from_name = from_match.group(1).strip().strip('"').strip("'")
                from_email = from_match.group(2).strip().lower()
            else:
                from_name = ""
                from_email = from_header.strip().lower()

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            body += payload.decode(charset, errors='replace')
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')

            return {
                "date": date,
                "from_email": from_email,
                "from_name": from_name,
                "to": parse_addr('To'),
                "cc": parse_addr('Cc'),
                "subject": subject,
                "body": body
            }
        except Exception as e:
            logger.error(f"Error getting .eml details {file_path}: {e}")
            return {
                "date": datetime.min,
                "from_email": "",
                "from_name": "",
                "to": [],
                "cc": [],
                "subject": "",
                "body": ""
            }
    def save_attachments(self, file_path: Path, target_dir: Path) -> List[Path]:
        """Extrahiert Anhänge aus einer E-Mail und speichert sie im Zielverzeichnis.

        Achtet darauf, keine vorhandenen Dateien zu überschreiben (fügt _final an).

        Args:
            file_path: Pfad zur E-Mail.
            target_dir: Zielverzeichnis.

        Returns:
            List[Path]: Liste der gespeicherten Dateipfade.
        """
        suffix = file_path.suffix.lower()
        if suffix == ".msg":
            return self._save_msg_attachments(file_path, target_dir)
        else:
            return self._save_eml_attachments(file_path, target_dir)

    def _save_msg_attachments(self, file_path: Path, target_dir: Path) -> List[Path]:
        saved_paths = []
        try:
            import extract_msg
            with extract_msg.openMsg(str(file_path)) as msg:
                for att in msg.attachments:
                    filename = None
                    if hasattr(att, "getFilename"):
                        try:
                            filename = att.getFilename()
                        except Exception:
                            pass
                    if not filename:
                        filename = getattr(att, "name", None) or getattr(att, "longFilename", None)

                    if filename:
                        dest = self._get_unique_path(target_dir / filename)
                        with open(dest, 'wb') as f:
                            f.write(att.data)
                        saved_paths.append(dest)
        except Exception as e:
            logger.error(f"Error saving .msg attachments: {e}")
        return saved_paths

    def _save_eml_attachments(self, file_path: Path, target_dir: Path) -> List[Path]:
        saved_paths = []
        try:
            import email
            from email import policy
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)

            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        dest = self._get_unique_path(target_dir / filename)
                        payload = part.get_payload(decode=True)
                        if payload:
                            with open(dest, 'wb') as f:
                                f.write(payload)
                            saved_paths.append(dest)
        except Exception as e:
            logger.error(f"Error saving .eml attachments: {e}")
        return saved_paths

    def _get_unique_path(self, path: Path) -> Path:
        """Erzeugt einen eindeutigen Pfad, indem _final angehängt wird, falls die Datei existiert."""
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        new_path = path.parent / f"{stem}_final{suffix}"

        # Falls _final auch existiert, hängen wir eine Nummer an oder weiteres _final
        # Der User sagte "bspw. _final", also machen wir es einfach repetitiv oder mit counter
        counter = 1
        while new_path.exists():
            new_path = path.parent / f"{stem}_final_{counter}{suffix}"
            counter += 1
        return new_path
