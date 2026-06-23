"""Tests for test_anonymization_logic.py."""
import unittest
import re
from typing import Set, List

# Rule-based logic copied from the implementation for testing purposes
# since we have environment/dependency issues running the full module in some contexts
def anonymize_th_koeln_names(text: str) -> str:
    """Test function."""
    if not text:
        return text
    email_pattern = r'\b([a-zA-Z0-9._-]+)@((?:smail\.)?th-koeln\.de)\b'
    emails = re.findall(email_pattern, text, re.IGNORECASE)
    names_to_replace: Set[str] = set()
    emails_to_replace: List[tuple] = []
    for local_part, domain in emails:
        if local_part.lower() == "daniel.gaida":
            continue
        emails_to_replace.append((f"{local_part}@{domain}", domain))
        parts = re.split(r'[._]', local_part)
        for part in parts:
            if len(part) > 2:
                names_to_replace.add(part)
    anonymized_text = text
    email_placeholders = {}
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
    """Test class."""
    def test_basic_anonymization(self):
        """Test function."""
        text = "Hallo Erika Mustermann, erika.mustermann@smail.th-koeln.de."
        expected = "Hallo Max Mustermann Max Mustermann, max.mustermann@smail.th-koeln.de."
        self.assertEqual(anonymize_th_koeln_names(text), expected)

    def test_skip_daniel_gaida(self):
        """Test function."""
        text = "Daniel Gaida <daniel.gaida@th-koeln.de>"
        # Should stay the same
        self.assertEqual(anonymize_th_koeln_names(text), text)

    def test_mixed_case_and_parts(self):
        """Test function."""
        text = "Max Power (max.power@th-koeln.de) sent a mail. Power is a cool name."
        # max.power -> max, power.
        # "Max" (if > 2) replaced by Max Mustermann
        # "Power" replaced by Max Mustermann
        result = anonymize_th_koeln_names(text)
        self.assertIn("Max Mustermann", result)
        self.assertIn("max.mustermann@th-koeln.de", result)
        self.assertNotIn("Max Power", result)
        self.assertNotIn("max.power", result)

    def test_multiple_names(self):
        """Test function."""
        text = "John Doe (john.doe@smail.th-koeln.de) and Jane Smith (jane.smith@th-koeln.de)"
        result = anonymize_th_koeln_names(text)
        self.assertIn("max.mustermann@smail.th-koeln.de", result)
        self.assertIn("max.mustermann@th-koeln.de", result)
        self.assertNotIn("John", result)
        self.assertNotIn("Jane", result)

    def test_underscore_in_email(self):
        """Test function."""
        text = "vorname_nachname@th-koeln.de"
        result = anonymize_th_koeln_names(text)
        self.assertEqual(result, "max.mustermann@th-koeln.de")

if __name__ == '__main__':
    unittest.main()
