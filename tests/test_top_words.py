"""Tests for test_top_words.py."""
from unittest.mock import patch, MagicMock
from mcp_university.classifier.top_words import get_top_words_per_class
import numpy as np

def test_get_top_words(tmp_path):
    """Tests test_get_top_words."""
    """Testet die Extraktion der Top-Wörter mit Mocks."""
    with patch("mcp_university.classifier.top_words.EmailClassifier") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.preprocess_data.return_value = (["text1", "text2"], ["ClassA", "ClassA"])

        with patch("mcp_university.classifier.top_words.TfidfVectorizer") as mock_tfidf,              patch("mcp_university.classifier.top_words.CountVectorizer") as mock_cv:

            mock_tfidf_instance = mock_tfidf.return_value
            mock_tfidf_instance.get_feature_names_out.return_value = np.array(["word1", "word2"])

            # Mock TF-IDF matrix
            mock_tfidf_matrix = MagicMock()
            mock_row = MagicMock()
            mock_row.toarray.return_value = np.array([[0.5, 0.5]])
            mock_tfidf_matrix.__getitem__.return_value = mock_row

            mock_tfidf_instance.fit_transform.return_value = mock_tfidf_matrix

            mock_tfidf_instance.idf_ = np.array([1.0, 1.0])
            mock_tfidf_instance.vocabulary_ = {"word1": 0, "word2": 1}

            # Mock Count matrix
            mock_cv_instance = mock_cv.return_value
            mock_cv_instance.get_feature_names_out.return_value = np.array(["word1", "word2"])

            mock_cv_matrix = MagicMock()
            # For global TF
            mock_cv_matrix.sum.return_value = np.array([[1, 1]])
            # For class TF
            mock_class_row = MagicMock()
            mock_class_row.toarray.return_value = np.array([[1, 1]])
            mock_cv_matrix.__getitem__.return_value = mock_class_row

            mock_cv_instance.fit_transform.return_value = mock_cv_matrix

            results = get_top_words_per_class(tmp_path, top_n=2)
            assert "ClassA" in results
            assert "word1" in results["ClassA"]

def test_get_top_words_empty(tmp_path):
    """Tests test_get_top_words_empty."""
    """Testet das Verhalten bei leerem Verzeichnis."""
    with patch("mcp_university.classifier.top_words.EmailClassifier") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.preprocess_data.return_value = ([], [])
        results = get_top_words_per_class(tmp_path)
        assert results == {}
