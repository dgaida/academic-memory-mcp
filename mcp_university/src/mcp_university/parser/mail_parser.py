from pathlib import Path
from typing import Optional, Dict, Any
import logging
import email
from email import policy

logger = logging.getLogger(__name__)

class MailParser:
    def parse(self, file_path: Path) -> Optional[str]:
        """
        Parses .eml or .msg files.
        Currently handles .eml via email package.
        """
        try:
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)

            subject = msg.get('Subject', '(No Subject)')
            sender = msg.get('From', '(No Sender)')
            date = msg.get('Date', '(No Date)')

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body += part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
            else:
                body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8')

            return f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"
        except Exception as e:
            logger.error(f"Error parsing mail {file_path}: {e}")
            return None
