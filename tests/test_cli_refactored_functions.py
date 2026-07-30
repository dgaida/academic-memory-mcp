"""Tests for the refactored CLI helper functions."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from typing import Any

from mcp_university.knowledge_graph.engine import build_knowledge_graph
from mcp_university.retrieval.index import perform_search
from mcp_university.crawler.crawler import run_index_or_profile

@patch("pathlib.Path")
def test_build_knowledge_graph_success(mock_path_cls):
    """Test building knowledge graph from config and processing summaries."""
    mock_cfg = MagicMock()
    mock_store = MagicMock()
    mock_store.upsert_node.return_value = (1, True)

    mock_summarizer = MagicMock()
    mock_graph_engine = MagicMock()
    mock_graph_engine.process_summary.return_value = {
        "new_nodes": ["Node A"],
        "new_edges": ["Edge A"],
        "updated_nodes": [],
        "updated_edges": []
    }

    # Mock yaml data
    yaml_data = {
        "class_paths": {
            "KlasseA": "test_paths/KlasseA"
        }
    }

    # Setup Path mocks
    mock_paths_file = MagicMock()
    mock_paths_file.exists.return_value = True

    # cfg.config_dir / "classifier_paths.yaml"
    mock_cfg.config_dir.__truediv__.return_value = mock_paths_file

    mock_base_path = MagicMock()
    mock_base_path.exists.return_value = True

    # We want mock_path_cls(...) to return mock_base_path when called
    mock_path_cls.return_value = mock_base_path

    # Setup rglob for base_path
    summary_file_emails = MagicMock()
    summary_file_emails.name = ".emails_summary.md"
    summary_file_emails.read_text.return_value = "Emails content"

    summary_file_other = MagicMock()
    summary_file_other.name = ".other_summary.md"
    summary_file_other.read_text.return_value = "Other content"

    def rglob_side_effect(pattern):
        if pattern == ".emails_summary.md":
            return [summary_file_emails]
        elif pattern == ".*_summary.md":
            return [summary_file_other]
        return []

    mock_base_path.rglob.side_effect = rglob_side_effect

    with patch("yaml.safe_load", return_value=yaml_data), \
         patch("builtins.open", mock_open()):

        # Run the function
        build_knowledge_graph(mock_cfg, mock_store, mock_summarizer, mock_graph_engine)

    # Assertions
    mock_store.upsert_node.assert_called_with(mock_cfg.user.name, "Person", {"email": mock_cfg.user.email, "role": ["User"]})
    mock_graph_engine.process_summary.assert_any_call("Emails content", 1)
    mock_graph_engine.process_summary.assert_any_call("Other content", 1)


@patch("pathlib.Path")
def test_build_knowledge_graph_missing_config(mock_path_cls):
    """Test build_knowledge_graph handles missing config file gracefully."""
    mock_cfg = MagicMock()
    mock_store = MagicMock()
    mock_store.upsert_node.return_value = (1, True)

    mock_summarizer = MagicMock()
    mock_graph_engine = MagicMock()

    # Paths do not exist
    mock_paths_file = MagicMock()
    mock_paths_file.exists.return_value = False
    mock_cfg.config_dir.__truediv__.return_value = mock_paths_file

    build_knowledge_graph(mock_cfg, mock_store, mock_summarizer, mock_graph_engine)
    mock_graph_engine.process_summary.assert_not_called()


def test_perform_search_with_results():
    """Test perform_search prints results and queries the summarizer."""
    mock_cfg = MagicMock()
    mock_cfg.llm.model = "test-model"
    mock_cfg.llm.base_url = "test-url"

    mock_store = MagicMock()
    mock_idx = MagicMock()
    mock_idx.search.return_value = [
        {"score": 0.95, "filename": "doc1.txt", "path": "path/to/doc1.txt", "content": "Document 1 content"}
    ]

    with patch("mcp_university.summarizer.engine.Summarizer") as mock_summarizer_cls:
        mock_summarizer = mock_summarizer_cls.return_value
        mock_summarizer.answer_question.return_value = "This is the generated answer."

        perform_search("test query", mock_cfg, mock_store, mock_idx)

        mock_idx.search.assert_called_once_with("test query")
        mock_summarizer.answer_question.assert_called_once_with(
            "test query",
            "Quelle: doc1.txt\nInhalt: Document 1 content"
        )


def test_perform_search_no_results():
    """Test perform_search when no results are found."""
    mock_cfg = MagicMock()
    mock_store = MagicMock()
    mock_idx = MagicMock()
    mock_idx.search.return_value = []

    with patch("mcp_university.summarizer.engine.Summarizer") as mock_summarizer_cls:
        perform_search("test query", mock_cfg, mock_store, mock_idx)
        mock_summarizer_cls.assert_not_called()


@patch("mcp_university.summarizer.profiler.PersonProfiler")
def test_run_index_or_profile_profile_provided_success(mock_profiler_cls):
    """Test run_index_or_profile when email profile is specified."""
    mock_cfg = MagicMock()
    mock_profiler = mock_profiler_cls.return_value
    mock_profiler.generate_profile.return_value = "Profile Content"
    mock_profiler.storage_path = MagicMock()

    run_index_or_profile("test@test.de", mock_cfg)

    mock_profiler.generate_profile.assert_called_once_with("test@test.de")


@patch("mcp_university.summarizer.profiler.PersonProfiler")
def test_run_index_or_profile_profile_provided_failure(mock_profiler_cls):
    """Test run_index_or_profile when email profile fails to generate."""
    mock_cfg = MagicMock()
    mock_profiler = mock_profiler_cls.return_value
    mock_profiler.generate_profile.return_value = None

    run_index_or_profile("test@test.de", mock_cfg)

    mock_profiler.generate_profile.assert_called_once_with("test@test.de")


@patch("mcp_university.crawler.crawler.Crawler")
@patch("mcp_university.retrieval.index.SearchIndex")
@patch("mcp_university.summarizer.engine.Summarizer")
@patch("academic_parser.factory.ParserFactory")
@patch("mcp_university.metadata.store.MetadataStore")
def test_run_index_or_profile_index_success(mock_store_cls, mock_parser_cls, mock_summarizer_cls, mock_idx_cls, mock_crawler_cls):
    """Test run_index_or_profile when no profile is specified runs the crawler."""
    mock_cfg = MagicMock()
    mock_cfg.sqlite_path = "sqlite.db"
    mock_cfg.data_dir = MagicMock()
    mock_cfg.llm.model = "test-model"
    mock_cfg.llm.base_url = "test-url"
    mock_cfg.qdrant_path = "qdrant"
    mock_cfg.embeddings.model = "embeddings-model"

    mock_crawler = mock_crawler_cls.return_value

    run_index_or_profile(None, mock_cfg)

    mock_store_cls.assert_called_once_with("sqlite.db")
    mock_parser_cls.assert_called_once_with(mock_cfg.data_dir / "cache")
    mock_summarizer_cls.assert_called_once_with("test-model", "test-url")
    mock_idx_cls.assert_called_once_with("qdrant", "embeddings-model", store=mock_store_cls.return_value)
    mock_crawler_cls.assert_called_once()
    mock_crawler.crawl.assert_called_once()
