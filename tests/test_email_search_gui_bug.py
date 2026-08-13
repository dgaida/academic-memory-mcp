"""Tests für die Fehlerbehebung bei der E-Mail-Such-GUI."""

import pytest
from unittest.mock import MagicMock, patch
import gradio as gr
from typing import Dict, Any

from scripts.email_search_gui import on_select, get_suggestions

def test_on_select() -> None:
    """Testet die on_select Funktion.

    Diese Funktion muss immer True zurückgeben, um anzuzeigen, dass eine Auswahl
    getroffen wurde und die darauffolgende Änderung der Auswahl ignoriert werden soll.

    Returns:
        None
    """
    assert on_select() is True

@patch("scripts.email_search_gui.GUITools")
def test_get_suggestions_when_ignore_is_true(mock_gui_tools: MagicMock) -> None:
    """Testet die get_suggestions-Funktion, wenn das ignore-Flag gesetzt ist.

    Wenn ignore auf True gesetzt ist, darf die Funktion keine Vorschläge
    vom Backend abfragen, sondern soll eine leere Aktualisierung zurückgeben
    und das ignore-Flag auf False zurücksetzen.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.

    Returns:
        None
    """
    # get_suggestions(query, ignore)
    update, ignore_out = get_suggestions("daniel.pfeiffer@hach.com", ignore=True)

    # Es soll keine Backend-Suche stattgefunden haben
    mock_gui_tools.engine.assert_not_called()

    # Gradio-Update soll leer sein (unverändert)
    assert isinstance(update, dict)
    assert "choices" not in update  # Keine Choices aktualisiert

    # ignore_out muss False sein (zurückgesetzt)
    assert ignore_out is False

@patch("scripts.email_search_gui.GUITools")
def test_get_suggestions_when_ignore_is_false(mock_gui_tools: MagicMock) -> None:
    """Testet die get_suggestions-Funktion, wenn das ignore-Flag False ist.

    In diesem Fall sollen Vorschläge von der Suchmaschine abgefragt werden.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.

    Returns:
        None
    """
    mock_engine = MagicMock()
    mock_engine.get_suggestions.return_value = ["daniel.pfeiffer@hach.com", "other@hach.com"]
    mock_gui_tools.engine.return_value = mock_engine

    update, ignore_out = get_suggestions("Hach", ignore=False)

    # Backend-Suche muss aufgerufen worden sein
    mock_engine.get_suggestions.assert_called_with("Hach")

    # Gradio-Update soll die Vorschläge enthalten
    assert isinstance(update, dict)
    assert "choices" in update
    assert update["choices"] == ["daniel.pfeiffer@hach.com", "other@hach.com"]

    # ignore_out muss False bleiben
    assert ignore_out is False

@patch("scripts.email_search_gui.GUITools")
def test_get_suggestions_short_query(mock_gui_tools: MagicMock) -> None:
    """Testet die get_suggestions-Funktion, wenn die Query zu kurz ist.

    Wenn die Query weniger als 2 Zeichen lang ist, sollen die choices geleert werden.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.

    Returns:
        None
    """
    update, ignore_out = get_suggestions("H", ignore=False)

    # Keine Suche im Backend
    mock_gui_tools.engine.assert_not_called()

    # choices sollen geleert werden
    assert isinstance(update, dict)
    assert "choices" in update
    assert update["choices"] == []

    # ignore_out ist False
    assert ignore_out is False
