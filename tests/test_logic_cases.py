"""Tests für die spezifischen Logik-Fälle aus check_logic.py."""
import pytest
from mcp_university.classifier.sort_emails import extract_lastname

@pytest.mark.parametrize("input_str, expected", [
    ("A B C D <a_b.c_d@smail.th-koeln.de>", "C D"),
    ("TH Köln <nils_karl.mode@smail.th-koeln.de>", "Mode"),
    ("Praxissemestersystem der F10 <praxissemester-inf@f10.th-koeln.de>", "Praxissemester-Inf"),
    ("Wester Helmut <HWester@tuev.com>", "HWester")
])
def test_extract_lastname_cases(input_str: str, expected: str) -> None:
    """Testet die Extraktion des Nachnamens für spezifische Testfälle.

    Args:
        input_str: Der Eingabestring.
        expected: Der erwartete Nachname.
    """
    assert extract_lastname(input_str) == expected
