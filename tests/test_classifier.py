"""Tests für das E-Mail-Klassifizierer-Engine."""
import pytest
from unittest.mock import patch
from mcp_university.classifier.engine import EmailClassifier

@pytest.fixture
def temp_data_dir(tmp_path):
    """Erstellt ein temporäres Verzeichnis mit Testdaten.

    Args:
        tmp_path: Temporärer Pfad.

    Returns:
        Path: Pfad zum Datenverzeichnis.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Erstelle Unterordner für Klassen
    for cls in ["BachelorThesis", "MasterThesis", "Other"]:
        cls_dir = data_dir / cls
        cls_dir.mkdir()
        # Erstelle ein paar Testdateien
        for i in range(3):
            (cls_dir / f"mail_{i}.msg").write_text(f"Inhalt von Mail {i} für {cls}")

    return data_dir

def test_classifier_initialization():
    """Testet die Initialisierung des Klassifizierers."""
    classifier = EmailClassifier(mode="tfidf", method="randomforest")
    assert classifier.mode == "tfidf"
    assert classifier.method == "randomforest"
    assert classifier.classifier is not None

def test_classifier_train(temp_data_dir):
    """Testet das Training des Klassifizierers.

    Args:
        temp_data_dir: Pfad zum Testdatenverzeichnis.
    """
    classifier = EmailClassifier(mode="tfidf", method="randomforest")

    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        classifier.train(temp_data_dir)

        assert classifier.classifier is not None
        assert classifier.tfidf_vectorizer is not None
        assert classifier.label_encoder is not None
        assert len(classifier.label_encoder.classes_) == 3

def test_classifier_predict(temp_data_dir):
    """Testet die Vorhersage.

    Args:
        temp_data_dir: Pfad zum Testdatenverzeichnis.
    """
    classifier = EmailClassifier(mode="tfidf", method="randomforest")

    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()
        classifier.train(temp_data_dir)

        test_file = temp_data_dir / "BachelorThesis" / "mail_0.msg"
        prediction = classifier.predict(test_file)

        assert "prediction" in prediction
        assert "confidence" in prediction
        assert prediction["prediction"] in ["BachelorThesis", "MasterThesis", "Other"]

def test_classifier_save_load(temp_data_dir, tmp_path):
    """Testet Speichern und Laden des Modells.

    Args:
        temp_data_dir: Pfad zum Testdatenverzeichnis.
        tmp_path: Temporärer Pfad.
    """
    classifier = EmailClassifier(mode="tfidf", method="randomforest")
    model_path = tmp_path / "model.pt"

    with patch("mcp_university.classifier.engine.MailParser.parse") as mock_parse:
        mock_parse.side_effect = lambda p: p.read_text()

        classifier.train(temp_data_dir)
        classifier.save(model_path)

        assert model_path.exists()

        new_classifier = EmailClassifier()
        new_classifier.load(model_path)

        assert new_classifier.mode == "tfidf"
        assert new_classifier.method == "randomforest"
        assert new_classifier.classifier is not None
