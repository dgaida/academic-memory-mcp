from unittest.mock import MagicMock, patch
from mcp_university.parser.pdf_parser import PDFParser
from mcp_university.parser.mail_parser import MailParser

def test_pdf_parser_modern_syntax(tmp_path):
    """Testet den PDFParser mit der modernen magic-pdf Syntax."""
    cache_dir = tmp_path / "cache"

    # Mock Path.home() to return tmp_path for this test
    with patch("mcp_university.parser.pdf_parser.Path.home") as mock_home:
        mock_home.return_value = tmp_path
        config_path = tmp_path / "magic-pdf.json"
        config_path.touch()

        parser = PDFParser(cache_dir)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        # Mock subprocess.run to simulate magic-pdf v1.x behavior
        with patch("subprocess.run") as mock_run:
            # Mocking the folder structure created by magic-pdf v1.x
            output_subdir = cache_dir / "test"
            output_subdir.mkdir(parents=True)
            md_file = output_subdir / "test.md"
            md_file.write_text("Parsed content")

            # magic-pdf -p ...
            mock_run.return_value = MagicMock(returncode=0)

            content = parser.parse(pdf_file)
            assert content == "Parsed content"

            # Verify the call was with the new syntax
            args, _ = mock_run.call_args_list[0]
            assert "-p" in args[0]
            assert "-o" in args[0]

def test_mail_parser_msg_handling(tmp_path):
    """Testet die Verarbeitung von .msg Dateien im MailParser."""
    parser = MailParser()
    msg_file = tmp_path / "test.msg"
    msg_file.touch()

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_msg.subject = "Test Subject"
        mock_msg.sender = "sender@example.com"
        mock_msg.date = "Mon, 1 Jan 2024"
        mock_msg.body = "This is a test message body."
        mock_open.return_value.__enter__.return_value = mock_msg

        content = parser.parse(msg_file)
        assert "Test Subject" in content
        assert "This is a test message body." in content

def test_mail_parser_eml_fallback_on_decode_error(tmp_path):
    """Testet den Fallback auf latin-1 bei Kodierungsfehlern in EML-Dateien."""
    parser = MailParser()
    eml_file = tmp_path / "test.eml"
    # Create a dummy EML with non-UTF-8 characters (e.g. 0xD0)
    eml_content = b"Subject: Test\nContent-Type: text/plain; charset=utf-8\n\n\xd0 Invalid"
    eml_file.write_bytes(eml_content)

    # This should now handle the UnicodeDecodeError using the latin-1 fallback
    content = parser.parse(eml_file)
    assert content is not None
    assert "Subject: Test" in content
