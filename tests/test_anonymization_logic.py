"""Tests für die Anonymisierungs-Logik."""
import unittest
import re
from typing import Set, List, Dict, Tuple

def anonymize_th_koeln_names(text: str) -> str:
    """Anonymisiert Namen und E-Mails der TH Köln in einem Text.

    Args:
        text: Der zu anonymisierende Text.

    Returns:
        str: Der anonymisierte Text.
    """
    if not text:
        return text
    email_pattern = r'\b([a-zA-Z0-9._-]+)@((?:smail\.)?th-koeln\.de)\b'
    emails = re.findall(email_pattern, text, re.IGNORECASE)
    names_to_replace: Set[str] = set()
    emails_to_replace: List[Tuple[str, str]] = []
    for local_part, domain in emails:
        if local_part.lower() == "daniel.gaida":
            continue
        emails_to_replace.append((f"{local_part}@{domain}", domain))
        parts = re.split(r'[._]', local_part)
        for part in parts:
            if len(part) > 2:
                names_to_replace.add(part)
    anonymized_text = text
    email_placeholders: Dict[str, str] = {}
    for i, (full_email, domain) in enumerate(emails_to_replace):
        placeholder = f"TEMP_EMAIL_PLACEHOLDER_{i}"
        email_placeholders[placeholder] = f"max.mustermann@{domain}"
        anonymized_text = re.sub(re.escape(full_email), placeholder, anonymized_text, flags=re.IGNORECASE)
    sorted_names = sorted(list(names_to_replace), key=len, reverse=True)
    for name in sorted_names:
        anonymized_text = re.sub(rf'\b{re.escape(name)}\b', "Max Mustermann", anonymized_text, flags=re.IGNORECASE)
    for placeholder, anonymized_email in email_placeholders.items():
        anonymized_text = anonymized_text.replace(placeholder, anonymized_email)
    return anonymized_text

class TestAnonymization(unittest.TestCase):
    """Testklasse für die Anonymisierung."""
    def test_basic_anonymization(self) -> None:
        """Testet die grundlegende Anonymisierung."""
        text = "Hallo Erika Mustermann, erika.mustermann@smail.th-koeln.de."
        expected = "Hallo Max Mustermann Max Mustermann, max.mustermann@smail.th-koeln.de."
        self.assertEqual(anonymize_th_koeln_names(text), expected)

    def test_skip_daniel_gaida(self) -> None:
        """Testet, dass Daniel Gaida nicht anonymisiert wird."""
        text = "Daniel Gaida <daniel.gaida@th-koeln.de>"
        self.assertEqual(anonymize_th_koeln_names(text), text)

    def test_mixed_case_and_parts(self) -> None:
        """Testet gemischte Schreibweise und Namensbestandteile."""
        text = "Max Power (max.power@th-koeln.de) sent a mail. Power is a cool name."
        result = anonymize_th_koeln_names(text)
        self.assertIn("Max Mustermann", result)
        self.assertIn("max.mustermann@th-koeln.de", result)
        self.assertNotIn("Max Power", result)
        self.assertNotIn("max.power", result)

    def test_multiple_names(self) -> None:
        """Testet mehrere Namen im gleichen Text."""
        text = "John Doe (john.doe@smail.th-koeln.de) and Jane Smith (jane.smith@th-koeln.de)"
        result = anonymize_th_koeln_names(text)
        self.assertIn("max.mustermann@smail.th-koeln.de", result)
        self.assertIn("max.mustermann@th-koeln.de", result)
        self.assertNotIn("John", result)
        self.assertNotIn("Jane", result)

    def test_underscore_in_email(self) -> None:
        """Testet Unterstriche in Email-Adressen."""
        text = "vorname_nachname@th-koeln.de"
        result = anonymize_th_koeln_names(text)
        self.assertEqual(result, "max.mustermann@th-koeln.de")

if __name__ == '__main__':
    unittest.main()
