"""Parser für E-Mail-Formate."""
import re
from pathlib import Path
from typing import Optional
import logging
import email
from email import policy
from email.utils import parsedate_to_datetime
from datetime import datetime
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

    def _parse_msg(self, file_path: Path) -> Optional[str]:
        """Parsen einer Outlook .msg Datei mit extract-msg."""
        try:
            import extract_msg
            with extract_msg.openMsg(str(file_path)) as msg:
                subject = msg.subject or '(No Subject)'
                sender = msg.sender or '(No Sender)'
                date = msg.date or '(No Date)'
                body = msg.body or ''
                return f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"
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
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body += payload.decode(charset)
                        except (UnicodeDecodeError, LookupError):
                            body += payload.decode('latin-1', errors='replace')
            else:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                try:
                    body = payload.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    body = payload.decode('latin-1', errors='replace')

            return f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"
        except Exception as e:
            logger.error(f"Error parsing mail {file_path}: {e}")
            return None
