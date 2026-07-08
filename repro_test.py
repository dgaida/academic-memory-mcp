import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from email_classifier.scripts.sort_emails import extract_lastname, process_emails
from scripts.fix_email_folders import fix_folders

def test_fix_email_folders_logic_debug(tmp_path):
    base = tmp_path / "BachelorThesis"
    base.mkdir()

    mail1 = base / "mail1.msg"
    mail1.touch()
    mail2 = base / "mail2.msg"
    mail2.touch()

    config_path = tmp_path / "config.yaml"
    import yaml
    with open(config_path, "w") as f:
        yaml.dump({"BachelorThesis": str(base)}, f)

    mock_details_1 = {
        "date": "2024-05-01",
        "from_name": "A B C D",
        "from_email": "a_b.c_d@smail.th-koeln.de", "to": [], "cc": []
    }
    mock_details_2 = {
        "date": "2024-05-01",
        "from_name": "TH Köln",
        "from_email": "nils_karl.mode@smail.th-koeln.de", "to": [], "cc": []
    }

    with patch("scripts.fix_email_folders.MailParser") as mock_parser_class,           patch("scripts.fix_email_folders.get_config") as mock_get_config,           patch("scripts.fix_email_folders.get_semester") as mock_get_semester:

        mock_parser = mock_parser_class.return_value
        mock_parser.get_email_details.side_effect = [mock_details_1, mock_details_2]

        mock_conf = MagicMock()
        mock_conf.user.emails = ["daniel.gaida@th-koeln.de"]
        mock_get_config.return_value = mock_conf
        mock_get_semester.return_value = "2024_SoSe"

        print("\nBefore fix_folders:")
        for f in base.rglob("*"): print(f"  {f}")

        fix_folders(config_path, dry_run=False)

        print("After fix_folders:")
        for f in base.rglob("*"): print(f"  {f}")

        assert (base / "2024_SoSe" / "C D" / "Inbox" / "mail1.msg").exists()
        assert (base / "2024_SoSe" / "Mode" / "Inbox" / "mail2.msg").exists()

if __name__ == "__main__":
    import sys
    from pathlib import Path
    import shutil

    tmp = Path("tmp_repro")
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir()
    try:
        test_fix_email_folders_logic_debug(tmp)
        print("Test PASSED")
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
