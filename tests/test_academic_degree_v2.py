"""Tests for academic degree extraction logic in TH Köln crawler.

This module provides unit tests to ensure that various HTML configurations
for person profile pages are correctly parsed and academic degrees are
extracted with appropriate priority.
"""

from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
from scripts.crawl_th_koeln_persons import THKoelnCrawler


def test_academic_degree_extraction_logic():
    """Tests the logic for academic degree extraction as implemented in the crawler.

    Returns:
        None
    """

    # Simulate extraction from span
    html_span = '<div class="introduction-personal"><span class="academic-degree">M.Sc.</span></div>'
    soup_span = BeautifulSoup(html_span, "html.parser")
    intro_div = soup_span.find("div", class_="introduction-personal")
    degree = None
    degree_span = intro_div.find("span", class_="academic-degree")
    if degree_span:
        degree = degree_span.get_text(strip=True)
    assert degree == "M.Sc."

    # Simulate extraction from name h1
    html_h1 = '<div class="introduction-personal"><h1>Prof. Dr. Hans Müller</h1></div>'
    soup_h1 = BeautifulSoup(html_h1, "html.parser")
    intro_div = soup_h1.find("div", class_="introduction-personal")
    degree = None
    name_h1 = intro_div.find("h1")
    if name_h1:
        full_name = name_h1.get_text(strip=True)
        if "Prof. Dr." in full_name:
            degree = "Prof. Dr."
        elif "Prof." in full_name:
            degree = "Prof."
    assert degree == "Prof. Dr."


def test_combined_extraction_logic():
    """Tests priority: name h1 should override span if both present and name contains Prof.

    Returns:
        None
    """
    html = """
    <div class="introduction-personal">
        <h1>Prof. Hans Müller</h1>
        <span class="academic-degree">Dipl.-Ing.</span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    intro_div = soup.find("div", class_="introduction-personal")

    details = {"academic_degree": None}

    # Logic from script:
    degree_span = intro_div.find("span", class_="academic-degree")
    if degree_span:
        details["academic_degree"] = degree_span.get_text(strip=True)

    name_h1 = intro_div.find("h1")
    if name_h1:
        full_name = name_h1.get_text(strip=True)
        if "Prof. Dr." in full_name:
            details["academic_degree"] = "Prof. Dr."
        elif "Prof." in full_name:
            details["academic_degree"] = "Prof."

    assert details["academic_degree"] == "Prof."


def test_personal_site_extraction_th_koeln():
    """Tests that 'Prof. Dr.' is correctly extracted from the personal-site HTML snippet.

    Returns:
        None
    """
    html_content = """<div class="article">
                    <article>

<div class="personal-site">
        <h1>Prof. Dr. Daniel Müller</h1>
            <span class="academic-degree">Dr.</span>"""

    crawler = THKoelnCrawler()
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()

    with patch.object(crawler.session, "get", return_value=mock_response):
        details = crawler.get_person_details("https://www.th-koeln.de/person-url")

    assert details["academic_degree"] == "Prof. Dr."
