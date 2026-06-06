"""Tests für das evaluate.py CLI."""
import subprocess
import sys
import pytest

def test_evaluate_cli_help():
    """Testet, ob die Hilfe angezeigt wird."""
    result = subprocess.run(
        [sys.executable, "-m", "mcp_university.classifier.evaluate", "--help"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    assert result.returncode == 0
    assert "--mode" in result.stdout
    assert "--method" in result.stdout
    assert "{tfidf,embedding,combined}" in result.stdout

def test_evaluate_cli_mode_suffix():
    """Testet, ob der Suffix korrekt an den Modellpfad angehängt wird."""
    # Wir führen das Skript mit einem fiktiven Verzeichnis aus und prüfen die Fehlermeldung.

    for method in ["xgboost", "randomforest"]:
        for mode in ["tfidf", "embedding", "combined"]:
            result = subprocess.run(
                [sys.executable, "-m", "mcp_university.classifier.evaluate", "non_existent_dir", "--method", method, "--mode", mode],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "."}
            )
            # Standardmodell ist data/email_classifier.pkl
            # suffix = _{method}_{mode}
            expected_path = f"data/email_classifier_{method}_{mode}.pkl"
            assert f"Modell {expected_path} wurde nicht gefunden" in result.stderr

def test_evaluate_cli_transformer_suffix():
    """Testet den Transformer-Suffix."""
    result = subprocess.run(
        [sys.executable, "-m", "mcp_university.classifier.evaluate", "non_existent_dir", "--method", "transformer"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    # suffix = _transformer
    expected_path = "data/email_classifier_transformer.pkl"
    assert f"Modell {expected_path} wurde nicht gefunden" in result.stderr

def test_evaluate_cli_custom_model_path_suffix():
    """Testet den Suffix bei eigenem Modellpfad."""
    result = subprocess.run(
        [sys.executable, "-m", "mcp_university.classifier.evaluate", "non_existent_dir", "--model-path", "custom/model.pkl", "--method", "xgboost", "--mode", "tfidf"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    assert "Modell custom/model_xgboost_tfidf.pkl wurde nicht gefunden" in result.stderr

if __name__ == "__main__":
    pytest.main([__file__])
