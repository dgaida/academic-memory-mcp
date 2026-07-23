"""Tests für die Parser des MCP University Systems."""
import sys
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch
import academic_parser.pdf_parser
from academic_parser.pdf_parser import PDFParser
from academic_parser.mail_parser import MailParser


def test_pdf_parser_docling(tmp_path: Path) -> None:
    """Testet den PDFParser mit docling als Fallback.

    Args:
        tmp_path: Temporärer Pfad für Test-Dateien.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"

    with patch("academic_parser.pdf_parser.DocumentConverter") as mock_converter_class, \
         patch("academic_parser.pdf_parser.LiteParse") as mock_liteparse_class:
        
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

        academic_parser = PDFParser(cache_dir)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        content = academic_parser.parse(pdf_file)
        assert content == "Parsed docling content"
        mock_converter.convert.assert_called_once_with(str(pdf_file), max_num_pages=3)


def test_mail_parser_msg_handling(tmp_path: Path) -> None:
    """Testet die Verarbeitung von .msg Dateien im MailParser.

    Args:
        tmp_path: Temporärer Pfad für Test-Dateien.

    Returns:
        None
    """
    academic_parser = MailParser()
    msg_file = tmp_path / "test.msg"
    msg_file.touch()

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_msg.subject = "Test Subject"
        mock_msg.sender = "sender@example.com"
        mock_msg.date = "Mon, 1 Jan 2024"
        mock_msg.body = "This is a test message body."
        mock_open.return_value.__enter__.return_value = mock_msg

        content = academic_parser.parse(msg_file)
        assert "Test Subject" in content
        assert "This is a test message body." in content


def test_mail_parser_eml_fallback_on_decode_error(tmp_path: Path) -> None:
    """Testet den Fallback auf latin-1 bei Kodierungsfehlern in EML-Dateien.

    Args:
        tmp_path: Temporärer Pfad für Test-Dateien.

    Returns:
        None
    """
    academic_parser = MailParser()
    eml_file = tmp_path / "test.eml"
    # Create a dummy EML with non-UTF-8 characters (e.g. 0xD0)
    eml_content = b"Subject: Test\nContent-Type: text/plain; charset=utf-8\n\n\xd0 Invalid"
    eml_file.write_bytes(eml_content)

    # This should now handle the UnicodeDecodeError using the latin-1 fallback
    content = academic_parser.parse(eml_file)
    assert content is not None
    assert "Subject: Test" in content


def test_pdf_parser_priority_liteparse(tmp_path: Path) -> None:
    """Testet, dass der PDFParser liteparse bevorzugt.

    Args:
        tmp_path: Temporärer Pfad für Test-Dateien.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"

    with patch("academic_parser.pdf_parser.DocumentConverter") as mock_docling_class, \
         patch("academic_parser.pdf_parser.LiteParse") as mock_liteparse_class:

        # LiteParse ist erfolgreich
        mock_lite_parser = mock_liteparse_class.return_value
        mock_result = MagicMock()
        mock_result.text = "Parsed liteparse content"
        mock_lite_parser.parse.return_value = mock_result
        
        # Docling (sollte gar nicht erst aufgerufen werden, wenn LiteParse Erfolg hat)
        mock_docling = mock_docling_class.return_value

        academic_parser = PDFParser(cache_dir)
        pdf_file = tmp_path / "test_priority.pdf"
        pdf_file.touch()

        content = academic_parser.parse(pdf_file)
        assert content == "Parsed liteparse content"

        # Verifizieren, dass nur LiteParse aufgerufen wurde
        mock_lite_parser.parse.assert_called_once_with(str(pdf_file))
        mock_docling.convert.assert_not_called()


def test_pdf_parser_docling_exception(tmp_path: Path) -> None:
    """Testet die Exception-Behandlung bei Docling.

    Args:
        tmp_path: Temporärer Pfad für Test-Dateien.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"
    academic_parser = PDFParser(cache_dir)
    pdf_file = tmp_path / "test_error.pdf"
    pdf_file.touch()

    with patch.object(academic_parser, "converter") as mock_converter, \
         patch.object(academic_parser, "_parse_with_liteparse", return_value=None):
        mock_converter.convert.side_effect = Exception("Docling conversion failed")
        content = academic_parser.parse(pdf_file)
        assert content is None


def test_pdf_parser_liteparse_not_installed(tmp_path: Path) -> None:
    """Testet, dass der PDFParser LiteParse überspringt, wenn es nicht installiert ist.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"
    pdf_file = tmp_path / "test_no_lp.pdf"
    pdf_file.touch()

    with patch("academic_parser.pdf_parser.LiteParse", None), \
         patch("academic_parser.pdf_parser.DocumentConverter") as mock_converter_class:
        mock_converter = mock_converter_class.return_value
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Docling markdown"
        mock_converter.convert.return_value = mock_result

        academic_parser = PDFParser(cache_dir)
        content = academic_parser.parse(pdf_file)
        assert content == "Docling markdown"


def test_pdf_parser_liteparse_exception(tmp_path: Path) -> None:
    """Testet die Exception-Behandlung bei LiteParse.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"
    pdf_file = tmp_path / "test_lp_error.pdf"
    pdf_file.touch()

    with patch("academic_parser.pdf_parser.LiteParse") as mock_liteparse_class, \
         patch("academic_parser.pdf_parser.DocumentConverter") as mock_converter_class:
        mock_liteparse = mock_liteparse_class.return_value
        mock_liteparse.parse.side_effect = Exception("LiteParse crashed")

        mock_converter = mock_converter_class.return_value
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Fallback markdown"
        mock_converter.convert.return_value = mock_result

        academic_parser = PDFParser(cache_dir)
        content = academic_parser.parse(pdf_file)
        assert content == "Fallback markdown"


def test_pdf_parser_docx_fallback_success(tmp_path: Path) -> None:
    """Testet den Fallback für DOCX-Dateien bei Erfolg.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"
    docx_file = tmp_path / "test.docx"
    docx_file.touch()

    with patch("docx.Document") as mock_document_cls:
        mock_doc = MagicMock()
        mock_p1 = MagicMock()
        mock_p1.text = "Paragraph 1"
        mock_p2 = MagicMock()
        mock_p2.text = "Paragraph 2"
        mock_doc.paragraphs = [mock_p1, mock_p2]
        mock_document_cls.return_value = mock_doc

        academic_parser = PDFParser(cache_dir)
        content = academic_parser.parse(docx_file)
        assert content == "Paragraph 1\nParagraph 2"


def test_pdf_parser_docx_fallback_exception(tmp_path: Path) -> None:
    """Testet die Exception-Behandlung beim DOCX Fallback.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"
    docx_file = tmp_path / "test_err.docx"
    docx_file.touch()

    with patch("docx.Document") as mock_document_cls:
        mock_document_cls.side_effect = Exception("docx library error")

        academic_parser = PDFParser(cache_dir)
        content = academic_parser.parse(docx_file)
        assert content is None


def test_get_parser_factory(tmp_path: Path) -> None:
    """Testet die get_parser Hilfsfunktion.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"
    p = academic_parser.pdf_parser.get_parser(cache_dir)
    assert isinstance(p, PDFParser)
    assert p.cache_dir == cache_dir


def test_pdf_parser_offline_mode(tmp_path: Path) -> None:
    """Testet den Offline-Modus des PDFParsers.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        None
    """
    cache_dir = tmp_path / "cache"
    with patch("academic_parser.pdf_parser.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.offline = True
        mock_get_config.return_value = mock_config

        academic_parser = PDFParser(cache_dir)
        assert academic_parser.cache_dir == cache_dir


def test_pdf_parser_import_errors(tmp_path: Path) -> None:
    """Testet die Behandlung von ImportErrors bei docling und liteparse.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        None
    """
    real_import = __builtins__["__import__"]

    def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in ("docling.document_converter", "liteparse"):
            raise ImportError(f"Simulated import error for {name}")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=mock_import):
        importlib.reload(academic_parser.pdf_parser)

        assert academic_parser.pdf_parser.DocumentConverter is None
        assert academic_parser.pdf_parser.LiteParse is None

    # Restore normal imports and run academic_parser to trigger coverage on final compiled code
    importlib.reload(academic_parser.pdf_parser)

    # Trigger offline check
    with patch("academic_parser.pdf_parser.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.offline = True
        mock_get_config.return_value = mock_config
        p = academic_parser.pdf_parser.get_parser(tmp_path / "dummy_cache")

    # Trigger docling empty content:
    p.converter = MagicMock()
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = ""
    p.converter.convert.return_value = mock_result
    with patch.object(p, "_parse_with_liteparse", return_value=None):
        content = p.parse(tmp_path / "empty_docling.pdf")
        assert content is None

    # Trigger docling exception (with non-existent file) on the final reloaded module instance
    p.converter = MagicMock()
    p.converter.convert.side_effect = Exception("Docling conversion crashed")
    with patch.object(p, "_parse_with_liteparse", return_value=None):
        content = p.parse(tmp_path / "non_existent_file.pdf")
        assert content is None
