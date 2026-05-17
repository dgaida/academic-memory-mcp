"""Tests für den E-Mail-Klassifikator."""
import pytest
from pathlib import Path
import shutil
import tempfile
import pickle
from unittest.mock import MagicMock, patch

from mcp_university.classifier.engine import EmailClassifier

@pytest.fixture
def temp_data_dir():
    """Erstellt ein temporäres Verzeichnis mit Testdaten."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    # Erstelle zwei Klassen-Ordner
    (root / "BachelorThesis").mkdir()
    (root / "MasterThesis").mkdir()

    # Erstelle Dummy .msg Dateien
    (root / "BachelorThesis" / "test1.msg").write_text("Anmeldung Bachelorarbeit")
    (root / "BachelorThesis" / "test2.msg").write_text("Frage zu Bachelor")
    (root / "MasterThesis" / "test3.msg").write_text("Masterarbeit Thema")
    (root / "MasterThesis" / "test4.msg").write_text("Kolloquium Master")

    yield root
    shutil.rmtree(tmpdir)

def test_classifier_train_predict_tfidf(temp_data_dir):
    """Testet das Training und die Vorhersage im TF-IDF Modus."""
    classifier = EmailClassifier(mode="tfidf")

    # Mock MailParser.parse
    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        classifier.train(temp_data_dir)
        assert classifier.is_trained

        # Test Vorhersage
        test_file = temp_data_dir / "BachelorThesis" / "test1.msg"
        result = classifier.predict(test_file)

        assert "prediction" in result
        assert result["prediction"] in ["BachelorThesis", "MasterThesis"]
        assert "confidence" in result
        assert "probabilities" in result

def test_classifier_save_load(temp_data_dir, tmp_path):
    """Testet Speichern und Laden des Modells."""
    classifier = EmailClassifier(mode="tfidf")
    model_path = tmp_path / "model.pkl"

    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        classifier.train(temp_data_dir)
        classifier.save(model_path)

        new_classifier = EmailClassifier()
        new_classifier.load(model_path)

        assert new_classifier.is_trained
        assert new_classifier.mode == "tfidf"
        assert len(new_classifier.label_encoder.classes_) == 2

@patch("mcp_university.classifier.engine.SentenceTransformer")
def test_classifier_embedding_mode(mock_st, temp_data_dir):
    """Testet den Embedding-Modus mit Mocks."""
    # Mock SentenceTransformer encode
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1, 0.2, 0.3]] * 4
    mock_st.return_value = mock_model

    classifier = EmailClassifier(mode="embedding")

    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        classifier.train(temp_data_dir)
        assert classifier.is_trained

        # Mock for predict
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        test_file = temp_data_dir / "BachelorThesis" / "test1.msg"
        result = classifier.predict(test_file)
        assert result["prediction"] in ["BachelorThesis", "MasterThesis"]
