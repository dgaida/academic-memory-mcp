"""Utility to anonymize and de-anonymize email content."""
import logging
import re
from typing import Dict, List, Set
import ollama
from ..config import get_config

logger = logging.getLogger(__name__)

def anonymize_th_koeln_names(text: str) -> str:
    """Anonymizes TH Köln names and emails in the given text.

    Replaces vorname.nachname@... with max.mustermann@... and
    replaces any occurrences of the extracted name parts with 'Max Mustermann'.
    Skips the configured user email.

    Args:
        text (str): The text to anonymize.

    Returns:
        str: Anonymized text.
    """
    if not text:
        return text

    # Pattern for TH Köln emails (smail.th-koeln.de or th-koeln.de)
    email_pattern = r'\b([a-zA-Z0-9._-]+)@((?:smail\.)?th-koeln\.de)\b'

    # Find all TH Köln emails
    emails = re.findall(email_pattern, text, re.IGNORECASE)

    names_to_replace: Set[str] = set()
    emails_to_replace: List[tuple] = []

    for local_part, domain in emails:
        cfg = get_config()
        user_email_local = cfg.user.email.split("@")[0].lower()
        if local_part.lower() == user_email_local:
            continue

        emails_to_replace.append((f"{local_part}@{domain}", domain))

        # Extract name parts
        # Split by . and _ to get individual name components
        parts = re.split(r'[._]', local_part)
        for part in parts:
            if len(part) > 2: # Ignore very short parts like initials
                names_to_replace.add(part)

    anonymized_text = text

    # 1. Temporarily replace email addresses with placeholders to avoid name replacement inside them
    email_placeholders = {}
    for i, (full_email, domain) in enumerate(emails_to_replace):
        placeholder = f"TEMP_EMAIL_PLACEHOLDER_{i}"
        email_placeholders[placeholder] = f"max.mustermann@{domain}"
        anonymized_text = re.sub(re.escape(full_email), placeholder, anonymized_text, flags=re.IGNORECASE)

    # 2. Sort names by length descending to replace longer strings first
    sorted_names = sorted(list(names_to_replace), key=len, reverse=True)

    # 3. Replace name parts with "Max Mustermann"
    for name in sorted_names:
        # Use word boundaries to avoid replacing parts of other words
        anonymized_text = re.sub(rf'\b{re.escape(name)}\b', "Max Mustermann", anonymized_text, flags=re.IGNORECASE)

    # 4. Replace email placeholders with anonymized email addresses
    for placeholder, anonymized_email in email_placeholders.items():
        anonymized_text = anonymized_text.replace(placeholder, anonymized_email)

    return anonymized_text

class Anonymizer:
    """Utility to anonymize and de-anonymize email content using a local LLM."""

    def __init__(self, model: str = None, base_url: str = None):
        """Initializes the anonymizer.

        Args:
            model (str, optional): Name of the local LLM model. Defaults to None.
            base_url (str, optional): Base URL of the Ollama server. Defaults to None.
        """
        cfg = get_config()
        self.model = model or cfg.llm.model
        self.base_url = str(base_url or cfg.llm.base_url)
        self.client = ollama.Client(host=self.base_url)
        # Placeholder -> Original
        self.mapping: Dict[str, str] = {}

    def anonymize(self, text: str, sender_name: str, sender_email: str,
                  recipient_name: str = None,
                  recipient_email: str = None) -> str:
        """Anonymizes the given text by replacing sender and recipient names/emails.

        Args:
            text (str): The text to anonymize.
            sender_name (str): Original name of the sender.
            sender_email (str): Original email of the sender.
            recipient_name (str): Original name of the recipient. Defaults to the configured user name.
            recipient_email (str): Original email of the recipient. Defaults to the configured user email.

        Returns:
            str: Anonymized text.
        """
        # First use rule-based anonymization for TH Köln specifics
        cfg = get_config()
        recipient_name = recipient_name or cfg.user.name
        recipient_email = recipient_email or cfg.user.email
        text = anonymize_th_koeln_names(text)

        # Define standard replacements
        std_sender_name = "Max Mustermann"
        std_sender_email = "max.mustermann@student.th-koeln.de"
        std_recipient_name = "Melanie Musterfrau"
        std_recipient_email = "melanie.musterfrau@th-koeln.de"

        self.mapping = {
            std_sender_name: sender_name,
            std_sender_email: sender_email,
            std_recipient_name: recipient_name,
            std_recipient_email: recipient_email
        }

        system_prompt = (
            "Du bist ein Datenschutz-Assistent. Anonymisiere die folgende E-Mail.\n"
            f"Ersetze den Absender ({sender_name} <{sender_email}>) durch '{std_sender_name}' und '{std_sender_email}'.\n"
            f"Ersetze den Empfänger ({recipient_name} <{recipient_email}>) durch '{std_recipient_name}' und '{std_recipient_email}'.\n"
            "Achte darauf, ALLE Vorkommen dieser Namen und E-Mails im gesamten Text konsistent zu ersetzen.\n"
            "Gib NUR den anonymisierten Text zurück."
        )

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': text}
                ],
                options={"temperature": 0}
            )
            anonymized_text = response['message']['content'].strip()
            logger.info("Content successfully anonymized via local LLM.")
            return anonymized_text
        except Exception as e:
            logger.error(f"Error during local LLM anonymization: {e}. Using regex/string fallback.")
            # Fallback
            t = text
            t = t.replace(sender_name, std_sender_name)
            t = t.replace(sender_email, std_sender_email)
            t = t.replace(recipient_name, std_recipient_name)
            t = t.replace(recipient_email, std_recipient_email)
            return t

    def deanonymize_text(self, text: str) -> str:
        """Replaces anonymized placeholders back with original values in a text block.

        Args:
            text (str): The text to de-anonymize.

        Returns:
            str: De-anonymized text.
        """
        if not self.mapping:
            return text

        result = text
        for placeholder, original in self.mapping.items():
            result = result.replace(placeholder, original)
        return result

    def deanonymize_args(self, args: Dict) -> Dict:
        """De-anonymizes tool arguments.

        Args:
            args (Dict): The tool arguments to de-anonymize.

        Returns:
            Dict: De-anonymized tool arguments.
        """
        if not self.mapping:
            return args

        new_args = {}
        for k, v in args.items():
            if isinstance(v, str):
                new_v = v
                for placeholder, original in self.mapping.items():
                    new_v = new_v.replace(placeholder, original)
                new_args[k] = new_v
            else:
                new_args[k] = v
        return new_args
