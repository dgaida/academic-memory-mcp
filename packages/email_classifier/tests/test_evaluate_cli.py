"""Tests für das evaluate.py CLI."""
import subprocess
import sys
import pytest

def test_evaluate_cli_help():
    """Testet, ob die Hilfe angezeigt wird."""
    result = subprocess.run(
        [sys.executable, "-m", "email_classifier.scripts.evaluate", "--help"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "packages/email_classifier/src:/app"}
    )
    assert result.returncode == 0
    assert "--mode" in result.stdout
    assert "{tfidf,embedding,combined}" in result.stdout

def test_evaluate_cli_mode_suffix():
    """Testet, ob der Modus-Suffix korrekt an den Modellpfad angehängt wird."""
    # Wir führen das Skript mit einem fiktiven Verzeichnis aus und prüfen die Fehlermeldung.
    # Da das Modell nicht existiert, sollte eine Fehlermeldung mit dem erwarteten Pfad kommen.

    modes = ["tfidf", "embedding", "combined"]
    for mode in modes:
        result = subprocess.run(
            [sys.executable, "-m", "email_classifier.scripts.evaluate", "non_existent_dir", "--mode", mode],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "packages/email_classifier/src:/app"}
        )
        # Erwarteter Fehler: ERROR: Modell data/email_classifier_<mode>.pkl wurde nicht gefunden.
        expected_path = "data/email_classifier_transformer.pkl"
        assert f"Modell {expected_path} wurde nicht gefunden" in result.stderr

def test_evaluate_cli_custom_model_path_suffix():
    """Testet den Suffix bei eigenem Modellpfad."""
    result = subprocess.run(
        [sys.executable, "-m", "email_classifier.scripts.evaluate", "non_existent_dir", "--model-path", "custom/model.pkl", "--mode", "tfidf"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "packages/email_classifier/src:/app"}
    )
    assert "Modell custom/model_transformer.pkl wurde nicht gefunden" in result.stderr

if __name__ == "__main__":
    pytest.main([__file__])
