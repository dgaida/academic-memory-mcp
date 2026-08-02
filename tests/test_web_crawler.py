"""Tests for the WebCrawlerManager class and automated crawling logic."""

from typing import Generator
import pytest
from unittest.mock import MagicMock, patch
import json
import numpy as np
from pathlib import Path

from mcp_university.crawler.web_crawler import WebCrawlerManager


@pytest.fixture
def temp_config_and_cache(tmp_path: Path) -> Generator[tuple[Path, Path], None, None]:
    """Fixture, die temporäre Pfade für Konfiguration und Cache bereitstellt.

    Args:
        tmp_path (Path): Temporäres Verzeichnis von pytest.

    Yields:
        tuple[Path, Path]: Pfad zur Konfigurationsdatei und Basis-Cache-Verzeichnis.
    """
    config_path = tmp_path / "web_sources.yaml"
    config_content = """
BA_DL_ML_KI:
  url: "https://dgaida.github.io/wpf_dlml_th_public/"
  name: "WPF Deep Learning, Machine Learning und Künstliche Intelligenz"
"""
    config_path.write_text(config_content, encoding="utf-8")
    cache_base_dir = tmp_path / "cache"
    yield config_path, cache_base_dir


def test_initialization_and_configuration(temp_config_and_cache: tuple[Path, Path]) -> None:
    """Testet die korrekte Initialisierung und das Laden der Konfiguration.

    Args:
        temp_config_and_cache (tuple[Path, Path]): Temporäre Pfade.
    """
    config_path, cache_base_dir = temp_config_and_cache
    manager = WebCrawlerManager(config_path=str(config_path), cache_base_dir=cache_base_dir)

    assert manager.is_configured("BA_DL_ML_KI")
    assert not manager.is_configured("Unknown_Class")
    assert manager.get_url("BA_DL_ML_KI") == "https://dgaida.github.io/wpf_dlml_th_public/"


def test_cache_loading_and_saving(temp_config_and_cache: tuple[Path, Path]) -> None:
    """Testet das Speichern und Laden des Cache.

    Args:
        temp_config_and_cache (tuple[Path, Path]): Temporäre Pfade.
    """
    config_path, cache_base_dir = temp_config_and_cache
    manager = WebCrawlerManager(config_path=str(config_path), cache_base_dir=cache_base_dir)

    class_name = "BA_DL_ML_KI"
    test_data = {
        "class_name": class_name,
        "root_url": "https://example.com",
        "pages": [{"url": "https://example.com", "title": "Home", "content": "Hello World"}],
        "pdfs": []
    }

    assert not manager.has_cache(class_name)
    assert manager.load_cache(class_name) is None

    manager.save_cache(class_name, test_data)
    assert manager.has_cache(class_name)

    loaded_data = manager.load_cache(class_name)
    assert loaded_data is not None
    assert loaded_data["class_name"] == class_name
    assert loaded_data["pages"][0]["content"] == "Hello World"


@patch("mcp_university.crawler.web_crawler.requests.get")
def test_fallback_crawler(mock_get: MagicMock, temp_config_and_cache: tuple[Path, Path]) -> None:
    """Testet den Fallback-Crawler mit requests und BeautifulSoup.

    Args:
        mock_get (MagicMock): Mock für requests.get.
        temp_config_and_cache (tuple[Path, Path]): Temporäre Pfade.
    """
    config_path, cache_base_dir = temp_config_and_cache
    manager = WebCrawlerManager(config_path=str(config_path), cache_base_dir=cache_base_dir)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.text = "<html><body><p>Some actual test paragraph text</p></body></html>"
    mock_get.return_value = mock_response

    text = manager._crawl_url_fallback("https://dgaida.github.io/wpf_dlml_th_public/")
    assert "Some actual test paragraph text" in text


@patch("mcp_university.crawler.web_crawler.extract_pdf_text")
@patch("mcp_university.crawler.web_crawler.requests.get")
def test_extract_text_from_pdf(mock_get: MagicMock, mock_extract_pdf_text: MagicMock, temp_config_and_cache: tuple[Path, Path]) -> None:
    """Testet das Herunterladen und Extrahieren von Texten aus PDFs.

    Args:
        mock_get (MagicMock): Mock für requests.get.
        mock_extract_pdf_text (MagicMock): Mock für extract_pdf_text.
        temp_config_and_cache (tuple[Path, Path]): Temporäre Pfade.
    """
    config_path, cache_base_dir = temp_config_and_cache
    manager = WebCrawlerManager(config_path=str(config_path), cache_base_dir=cache_base_dir)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"%PDF-1.4 mock content"
    mock_get.return_value = mock_response

    mock_extract_pdf_text.return_value = "Extracted PDF exam instructions text content."

    text = manager._extract_text_from_pdf("https://example.com/exam_info.pdf", "BA_DL_ML_KI")
    assert text == "Extracted PDF exam instructions text content."
    mock_extract_pdf_text.assert_called_once()


def test_get_relevant_context_bm25(temp_config_and_cache: tuple[Path, Path]) -> None:
    """Testet die BM25-basierte Such- und Relevanzbewertung auf Basis des Cache.

    Bypasst die globale BM25-Mockierung aus conftest.py.

    Args:
        temp_config_and_cache (tuple[Path, Path]): Temporäre Pfade.
    """
    config_path, cache_base_dir = temp_config_and_cache
    manager = WebCrawlerManager(config_path=str(config_path), cache_base_dir=cache_base_dir)

    class_name = "BA_DL_ML_KI"
    cache_data = {
        "class_name": class_name,
        "root_url": "https://dgaida.github.io/wpf_dlml_th_public/",
        "pages": [
            {
                "url": "https://dgaida.github.io/wpf_dlml_th_public/",
                "title": "Hauptseite",
                "content": "Willkommen im WPF Modul für Deep Learning und Künstliche Intelligenz."
            },
            {
                "url": "https://dgaida.github.io/wpf_dlml_th_public/pruefungsleistung/",
                "title": "Prüfungsleistung",
                "content": "Als Hilfsmittel zur Klausur sind ein beidseitig handbeschriebenes DIN-A4-Blatt und ein nicht-programmierbarer Taschenrechner zugelassen."
            }
        ],
        "pdfs": [
            {
                "url": "https://dgaida.github.io/wpf_dlml_th_public/assets/tasks/DLML_Aufgabensammlung.pdf",
                "filename": "DLML_Aufgabensammlung.pdf",
                "content": "Diese Aufgabensammlung enthält Übungsaufgaben zu neuronalen Netzen, Backpropagation und Deep Learning."
            }
        ]
    }

    manager.save_cache(class_name, cache_data)

    # BM25Okapi patchen, um echte Scores für den Test zurückzugeben
    with patch("mcp_university.crawler.web_crawler.BM25Okapi") as mock_bm25_cls:
        mock_bm25 = mock_bm25_cls.return_value
        # 1. Aufruf: Hilfsmittel-Suche -> Favorisiere "Prüfungsleistung" (Index 1) und "Hauptseite" (Index 0)
        # 2. Aufruf: Übungsaufgaben-Suche -> Favorisiere "Aufgabensammlung.pdf" (Index 2)
        mock_bm25.get_scores.side_effect = [
            np.array([0.5, 1.5, 0.0]),
            np.array([0.0, 0.0, 2.0])
        ]

        # 1. Suche nach Klausur-Hilfsmitteln
        email_content = "Guten Tag, welche Hilfsmittel sind für die Klausur in DLML zugelassen?"
        context = manager.get_relevant_context(class_name, email_content)

        assert "Hilfsmittel zur Klausur" in context
        assert "beidseitig handbeschriebenes" in context
        assert "Taschenrechner" in context
        assert "OFFLINE WEB-QUELLE" in context

        # 2. Suche nach Aufgabensammlung / Übungen
        email_content_tasks = "Gibt es Übungsaufgaben oder eine Aufgabensammlung?"
        context_tasks = manager.get_relevant_context(class_name, email_content_tasks)
        assert "Aufgabensammlung.pdf" in context_tasks
        assert "Übungsaufgaben" in context_tasks
