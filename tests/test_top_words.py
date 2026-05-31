import pytest
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
from mcp_university.classifier.top_words import get_top_words_per_class

@pytest.fixture
def temp_mail_data():
    """Erstellt ein temporäres Verzeichnis mit Test-E-Mails."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    # Erstelle Klassen
    exam = root / "Pruefungsamt"
    exam.mkdir()
    (exam / "Inbox").mkdir()

    thesis = root / "Thesis"
    thesis.mkdir()
    (thesis / "Inbox").mkdir()

    # Erstelle E-Mails mit spezifischen Wörtern
    (exam / "Inbox" / "mail1.msg").write_text("Anmeldung zur Prüfung im Prüfungsamt")
    (exam / "Inbox" / "mail2.msg").write_text("Notenspiegel und Prüfung")

    (thesis / "Inbox" / "mail3.msg").write_text("Bachelorarbeit Thema für die Thesis")
    (thesis / "Inbox" / "mail4.msg").write_text("Kolloquium Thesis Bachelorarbeit")

    yield root
    shutil.rmtree(tmpdir)

def test_get_top_words(temp_mail_data):
    """Testet die Extraktion der Top-Wörter."""
    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        results = get_top_words_per_class(temp_mail_data, top_n=2)

        assert "Pruefungsamt" in results
        assert "Thesis" in results

        # Prüfung ob relevante Wörter enthalten sind (TF-IDF sollte diese hoch ranken)
        # Beachte: TfidfVectorizer normalisiert und tokenisiert
        pa_words = [w.lower() for w in results["Pruefungsamt"]]
        thesis_words = [w.lower() for w in results["Thesis"]]

        assert "prüfung" in pa_words or "prüfungsamt" in pa_words
        assert "thesis" in thesis_words or "bachelorarbeit" in thesis_words

def test_get_top_words_empty(tmp_path):
    """Testet das Verhalten bei leerem Verzeichnis."""
    results = get_top_words_per_class(tmp_path)
    assert results == {}
