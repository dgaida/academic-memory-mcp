"""Tests für das Skript fix_email_folders.py."""
import pytest
from unittest.mock import MagicMock, patch
from scripts.fix_email_folders import fix_folders

@pytest.fixture
def temp_mail_structure(tmp_path):
    """Erstellt eine temporäre E-Mail-Struktur für Tests."""
    base = tmp_path / "BachelorThesis"
    base.mkdir()

    # Mail 1: Nils Hans Morz -> Morz/Inbox
    # (Wir simulieren die Datei im Hauptverzeichnis der Klasse)
    mail1 = base / "20240101_120000_mail1.msg"
    mail1.touch()

    config = tmp_path / "config.yaml"
    import yaml
    with open(config, "w") as f:
        yaml.dump({"BachelorThesis": str(base)}, f)

    return base, config, mail1

def test_fix_folders_requirement_2(temp_mail_structure, tmp_path):
    """Anforderung 2: TH Köln <nils_karl.mode@smail.th-koeln.de> -> Mode/Inbox."""
    base, config_path, mail_file = temp_mail_structure

    # Mock Details für MailParser
    mock_details = {
        "date": "2024-05-01",
        "from_name": "TH Köln",
        "from_email": "nils_karl.mode@smail.th-koeln.de",
        "to": [{"name": "Daniel Gaida", "email": "daniel.gaida@th-koeln.de"}]
    }

    with patch("scripts.fix_email_folders.MailParser") as mock_parser_class,          patch("scripts.fix_email_folders.get_config") as mock_get_config,          patch("scripts.fix_email_folders.get_semester") as mock_get_semester:

        mock_parser = mock_parser_class.return_value
        mock_parser.get_email_details.return_value = mock_details

        mock_conf = MagicMock()
        mock_conf.user.emails = ["daniel.gaida@th-koeln.de"]
        mock_get_config.return_value = mock_conf

        mock_get_semester.return_value = "2024_SoSe"

        # Ausführung
        fix_folders(config_path, dry_run=False)

        # Prüfung
        expected_path = base / "2024_SoSe" / "Mode" / "Inbox" / mail_file.name
        assert expected_path.exists(), f"E-Mail wurde nicht nach {expected_path} verschoben"

def test_fix_folders_requirement_1(temp_mail_structure, tmp_path):
    """Anforderung 1: A B C D <a_b.c_d@smail.th-koeln.de> -> C D/Inbox."""
    base, config_path, mail_file = temp_mail_structure

    mock_details = {
        "date": "2024-05-01",
        "from_name": "A B C D",
        "from_email": "a_b.c_d@smail.th-koeln.de",
        "to": [{"name": "Daniel Gaida", "email": "daniel.gaida@th-koeln.de"}]
    }

    with patch("scripts.fix_email_folders.MailParser") as mock_parser_class,          patch("scripts.fix_email_folders.get_config") as mock_get_config,          patch("scripts.fix_email_folders.get_semester") as mock_get_semester:

        mock_parser = mock_parser_class.return_value
        mock_parser.get_email_details.return_value = mock_details

        mock_conf = MagicMock()
        mock_conf.user.emails = ["daniel.gaida@th-koeln.de"]
        mock_get_config.return_value = mock_conf

        mock_get_semester.return_value = "2024_SoSe"

        fix_folders(config_path, dry_run=False)

        expected_path = base / "2024_SoSe" / "C D" / "Inbox" / mail_file.name
        assert expected_path.exists(), f"E-Mail wurde nicht nach {expected_path} verschoben"
