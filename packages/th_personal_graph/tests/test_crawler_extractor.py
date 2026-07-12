"""Tests für den TH Köln Personal-Crawler und den MOCOGI Extraktor."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from th_personal_graph.scripts.crawl_th_koeln_persons import THKoelnCrawler, save_to_database
from th_personal_graph.scripts.extract_mocogi_data import PersonResolver, match_person

def test_crawler_filter_options() -> None:
    """Testet, ob Filteroptionen korrekt aus dem HTML extrahiert werden."""
    crawler = THKoelnCrawler()

    html_mock = """
    <html>
        <body>
            <input name="faculty_de[]" value="Informatik und Ingenieurwissenschaften">
            <input name="other_institution_de[]" value="Campus IT">
        </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.text = html_mock

    with patch.object(crawler.session, 'get', return_value=mock_response):
        options = crawler.get_filter_options()

    assert "Informatik und Ingenieurwissenschaften" in options["faculties"]
    assert "Campus IT" in options["institutions"]

def test_crawler_get_persons() -> None:
    """Testet das Parsen von Personen aus der TH Köln Personenliste."""
    crawler = THKoelnCrawler()

    html_mock = """
    <table>
        <tr>
            <td><a href="/personen/max_mustermann">Max Mustermann</a></td>
            <td><span class="email">max.mustermann&#64;th-koeln.de</span></td>
        </tr>
    </table>
    """

    mock_response = MagicMock()
    mock_response.text = html_mock

    with patch.object(crawler.session, 'get', return_value=mock_response):
        persons = crawler.get_persons(char="M")

    assert len(persons) == 1
    assert persons[0]["name"] == "Max Mustermann"
    assert persons[0]["email"] == "max.mustermann@th-koeln.de"
    assert "max_mustermann" in persons[0]["profile_url"]

def test_person_resolver_strip_titles() -> None:
    """Testet die Entfernung akademischer Grade aus den Namen."""
    resolver = PersonResolver(base_url="https://mock-api")

    name_with_titles = "Prof. Dr. Max Mustermann, Dr. rer. nat. Erika Musterfrau"
    cleaned = resolver.strip_titles(name_with_titles)

    assert "Max Mustermann" in cleaned
    assert "Erika Musterfrau" in cleaned
    assert "Prof" not in cleaned
    assert "Dr" not in cleaned

def test_match_person() -> None:
    """Testet den Fuzzy-Namensabgleich gegen die SQLite-Datenbank."""
    mock_store = MagicMock()
    mock_store.get_all_nodes.return_value = [
        {"id": 42, "name": "Max Mustermann", "type": "Person"},
        {"id": 43, "name": "Erika Musterfrau", "type": "Person"}
    ]

    # Exact Match
    match_id = match_person(mock_store, "Max Mustermann")
    assert match_id == 42

    # Order changed (Lastname, Firstname)
    match_id_reverse = match_person(mock_store, "Mustermann, Max")
    assert match_id_reverse == 42

    # No match
    no_match = match_person(mock_store, "John Doe")
    assert no_match is None
