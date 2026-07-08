"""Tests for test_classifier_analysis_extended.py."""
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import numpy as np
from email_classifier.scripts.xai_analysis import run_xai_analysis
from email_classifier.scripts.plot_data_distribution import count_emails, plot_distribution

@patch("email_classifier.scripts.xai_analysis.EmailClassifier")
@patch("email_classifier.scripts.xai_analysis.shap.TreeExplainer")
def test_run_xai_analysis(mock_shap, mock_classifier_cls):
    """Test function docstring."""
    mock_classifier = mock_classifier_cls.return_value
    mock_classifier.mode = "tfidf"
    mock_classifier.label_encoder.classes_ = ["Class1"]
    mock_classifier.tfidf_vectorizer.get_feature_names_out.return_value = ["word1"]
    mock_shap.return_value.shap_values.return_value = [np.array([[0.1]])]
    model_path, test_dir = MagicMock(spec=Path), MagicMock(spec=Path)
    model_path.exists.return_value = True
    test_dir.exists.return_value = True
    with patch("email_classifier.scripts.xai_analysis.open", mock_open()):
        run_xai_analysis(model_path, test_dir)
        assert mock_classifier.load.called

def test_plot_dist(tmp_path):
    """Test function docstring."""
    d = tmp_path / "C1"
    d.mkdir()
    (d / "Inbox").mkdir()
    (d / "Inbox" / "m.msg").touch()
    df = count_emails(str(tmp_path))
    assert len(df) == 1
    with patch("email_classifier.scripts.plot_data_distribution.plt.savefig"), patch("email_classifier.scripts.plot_data_distribution.plt.show"), patch("email_classifier.scripts.plot_data_distribution.plt.close"):
        plot_distribution(df, "T", tmp_path / "out.png")
