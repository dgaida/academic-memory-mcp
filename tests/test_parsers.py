"""Tests for test_parsers.py."""
"""Tests für die Parser des MCP University Systems."""
from unittest.mock import MagicMock, patch
from mcp_university.parser.pdf_parser import PDFParser
from mcp_university.parser.mail_parser import MailParser

def test_pdf_parser_docling(tmp_path):
    """Tests test_pdf_parser_docling."""
    """Testet den PDFParser mit docling als Fallback."""
    cache_dir = tmp_path / "cache"

    with patch("mcp_university.parser.pdf_parser.DocumentConverter") as mock_converter_class, \
         patch("mcp_university.parser.pdf_parser.LiteParse") as mock_liteparse_class:
        
        # LiteParse schlägt fehl (gibt MagicMock zurück, dessen .text wir auf None setzen)
        mock_lite_parser = mock_liteparse_class.return_value
        mock_lite_result = MagicMock()
        del mock_lite_result.text # Damit hasattr(result, "text") False ist
        mock_lite_result.__str__.return_value = "" # Damit bool("") False ist
        mock_lite_parser.parse.return_value = "" # Direkt String zurückgeben

        mock_converter = mock_converter_class.return_value
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.document.export_to_markdown.return_value = "Parsed docling content"
        mock_converter.convert.return_value = mock_result

        parser = PDFParser(cache_dir)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        content = parser.parse(pdf_file)
        assert content == "Parsed docling content"
        mock_converter.convert.assert_called_once_with(str(pdf_file), max_num_pages=3)

def test_mail_parser_msg_handling(tmp_path):
    """Tests test_mail_parser_msg_handling."""
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
    """Tests test_mail_parser_eml_fallback_on_decode_error."""
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

def test_pdf_parser_priority_liteparse(tmp_path):
    """Tests test_pdf_parser_priority_liteparse."""
    """Testet, dass der PDFParser liteparse bevorzugt."""
    cache_dir = tmp_path / "cache"

    with patch("mcp_university.parser.pdf_parser.DocumentConverter") as mock_docling_class, \
         patch("mcp_university.parser.pdf_parser.LiteParse") as mock_liteparse_class:

        # LiteParse ist erfolgreich
        mock_lite_parser = mock_liteparse_class.return_value
        mock_result = MagicMock()
        mock_result.text = "Parsed liteparse content"
        mock_lite_parser.parse.return_value = mock_result
        
        # Docling (sollte gar nicht erst aufgerufen werden, wenn LiteParse Erfolg hat)
        mock_docling = mock_docling_class.return_value

        parser = PDFParser(cache_dir)
        pdf_file = tmp_path / "test_priority.pdf"
        pdf_file.touch()

        content = parser.parse(pdf_file)
        assert content == "Parsed liteparse content"

        # Verifizieren, dass nur LiteParse aufgerufen wurde
        mock_lite_parser.parse.assert_called_once_with(str(pdf_file))
        mock_docling.convert.assert_not_called()
