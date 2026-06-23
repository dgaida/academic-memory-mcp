"""Tests für den E-Mail-Klassifikator."""
import pytest
from pathlib import Path
import shutil
import tempfile
from unittest.mock import MagicMock, patch

from mcp_university.classifier.engine import EmailClassifier

@pytest.fixture
def temp_data_dir():
    """Erstellt ein temporäres Verzeichnis mit Testdaten in der neuen Struktur."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    # Erstelle zwei Klassen-Ordner
    bach = root / "BachelorThesis"
    mast = root / "MasterThesis"

    for d in [bach, mast]:
        d.mkdir()
        (d / "Inbox").mkdir()
        (d / "SentItems").mkdir()

    # Erstelle Dummy .msg Dateien in Unterordnern
    (bach / "Inbox" / "test1.msg").write_text("Anmeldung Bachelorarbeit")
    (bach / "SentItems" / "test2.msg").write_text("Frage zu Bachelor")
    (mast / "Inbox" / "test3.msg").write_text("Masterarbeit Thema")
    (mast / "SentItems" / "test4.msg").write_text("Kolloquium Master")

    yield root
    shutil.rmtree(tmpdir)

def test_classifier_train_predict_tfidf(temp_data_dir):
    """Testet das Training und die Vorhersage im TF-IDF Modus mit Unterordnern."""
    classifier = EmailClassifier(mode="tfidf", method="randomforest")

    # Mock MailParser.parse
    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        classifier.train(temp_data_dir)
        assert classifier.is_trained

        # Test Vorhersage
        test_file = temp_data_dir / "BachelorThesis" / "Inbox" / "test1.msg"
        result = classifier.predict(test_file)

        assert "prediction" in result
        assert result["prediction"] in ["BachelorThesis", "MasterThesis"]
        assert "confidence" in result
        assert "probabilities" in result

def test_classifier_save_load(temp_data_dir, tmp_path):
    """Testet Speichern und Laden des Modells."""
    classifier = EmailClassifier(mode="tfidf", method="randomforest")
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

@patch("sentence_transformers.SentenceTransformer")
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
        test_file = temp_data_dir / "BachelorThesis" / "Inbox" / "test1.msg"
        result = classifier.predict(test_file)
        assert result["prediction"] in ["BachelorThesis", "MasterThesis"]

def test_classifier_train_predict_xgboost(temp_data_dir):
    """Testet das Training und die Vorhersage im XGBoost Modus."""
    classifier = EmailClassifier(mode="tfidf", method="xgboost")

    # Mock MailParser.parse
    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        classifier.train(temp_data_dir)
        assert classifier.is_trained
        assert classifier.method == "xgboost"

        # Test Vorhersage
        test_file = temp_data_dir / "BachelorThesis" / "Inbox" / "test1.msg"
        result = classifier.predict(test_file)

        assert "prediction" in result
        assert result["prediction"] in ["BachelorThesis", "MasterThesis"]
        assert "confidence" in result
        assert "probabilities" in result
