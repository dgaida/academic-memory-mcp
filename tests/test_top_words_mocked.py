import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from mcp_university.classifier.top_words import get_top_words_per_class

def test_get_top_words_mocked(tmp_path):
    with patch("mcp_university.classifier.top_words.EmailClassifier") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.preprocess_data.return_value = (["text1", "text2"], ["ClassA", "ClassA"])

        # We need to mock TfidfVectorizer and CountVectorizer too if we want to be fully isolated
        with patch("mcp_university.classifier.top_words.TfidfVectorizer") as mock_tfidf,              patch("mcp_university.classifier.top_words.CountVectorizer") as mock_cv:

            mock_tfidf_instance = mock_tfidf.return_value
            mock_tfidf_instance.get_feature_names_out.return_value = ["word1", "word2"]
            mock_tfidf_instance.fit_transform.return_value = MagicMock()
            mock_tfidf_instance.fit_transform.return_value.toarray.return_value = [[0.5, 0.5]]
            mock_tfidf_instance.idf_ = [1.0, 1.0]
            mock_tfidf_instance.vocabulary_ = {"word1": 0, "word2": 1}

            mock_cv_instance = mock_cv.return_value
            mock_cv_instance.get_feature_names_out.return_value = ["word1", "word2"]
            mock_cv_instance.fit_transform.return_value = MagicMock()
            mock_cv_instance.fit_transform.return_value.sum.return_value = [[1, 1]]
            mock_cv_instance.fit_transform.return_value.toarray.return_value = [[1, 1]]

            results = get_top_words_per_class(tmp_path, top_n=2)
            assert "ClassA" in results
