"""Tests for extended folder detection in EmailSearchEngine."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.utils.email_search import EmailSearchEngine

@pytest.fixture
def mock_config(tmp_path: Path) -> MagicMock:
    """Erstellt eine gemockte Konfiguration.

    Args:
        tmp_path (Path): Temporärer Pfad für Tests.

    Returns:
        MagicMock: Die gemockte Konfiguration.
    """
    config = MagicMock()
    config.data_dir = tmp_path / "data"
    config.config_dir = tmp_path / "config"
    config.data_dir.mkdir()
    config.config_dir.mkdir()
    (config.data_dir / "cache").mkdir()
    return config

def test_sent_items_detection_various_names(mock_config: MagicMock, tmp_path: Path) -> None:
    """Testet die Erkennung verschiedener Namen für gesendete Elemente.

    Args:
        mock_config (MagicMock): Die gemockte Konfiguration.
        tmp_path (Path): Temporärer Pfad für Tests.
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    folder_names = ["SentItems", "Sent Items", "Gesendete Elemente", "Gesendete Objekte", "Sent"]
    search_paths = []

    for idx, folder_name in enumerate(folder_names):
        folder_path = tmp_path / folder_name
        folder_path.mkdir()
        file = folder_path / f"test_{idx}.eml"
        file.write_text(f"From: me@example.com\nSubject: Mail in {folder_name}\n\nBody")
        search_paths.append(folder_path)

    inbox_path = tmp_path / "Inbox"
    inbox_path.mkdir()
    inbox_file = inbox_path / "test_inbox.eml"
    inbox_file.write_text("From: someone@example.com\nSubject: Inbox Mail\n\nBody")
    search_paths.append(inbox_path)

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config),          patch.object(EmailSearchEngine, "get_search_paths", return_value=search_paths):

        engine = EmailSearchEngine(cache_file=cache_file)
        engine.update_index()

        sent_results = [item for item in engine.index if item["folder"] == "SentItems"]
        inbox_results = [item for item in engine.index if item["folder"] == "Inbox"]

        assert len(sent_results) == len(folder_names)
        assert len(inbox_results) == 1

        for folder_name in folder_names:
            assert any(item["subject"] == f"Mail in {folder_name}" for item in sent_results)

if __name__ == "__main__":
    pytest.main([__file__])
