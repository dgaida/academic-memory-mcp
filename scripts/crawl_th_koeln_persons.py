"""Script to crawl persons from TH Köln website and extract their details.

This script fetches a list of persons from the TH Köln personnel page,
extracts their names and email addresses, and then visits their individual
profile pages to extract their faculty and institute information.
The results are saved in Markdown files (one per faculty/institution)
and in the university metadata database.
"""

import argparse
import html
import os
import random
import re
import string
import sys
import time
import glob
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

from mcp_university.metadata.store import MetadataStore
from mcp_university.config import get_config

# Try to reconfigure stdout/stdin for UTF-8 (mainly for Windows)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stdin, 'reconfigure'):
    try:
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

class THKoelnCrawler:
    """Crawler for TH Köln personnel pages."""

    BASE_URL = "https://www.th-koeln.de"
    PERSONS_LIST_URL = f"{BASE_URL}/hochschule/personen_3850.php?"

    def __init__(self, delay_range: tuple = (1, 3)) -> None:
        """Initializes the crawler with a session and user-agent.

        Args:
            delay_range: A tuple containing min and max delay in seconds between requests.
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        self.delay_range = delay_range

    def _wait(self) -> None:
        """Wait for a random duration to avoid being blocked."""
        time.sleep(random.uniform(*self.delay_range))

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Fetches available faculties and institutions from the website.

        Returns:
            A dictionary with 'faculties' and 'institutions' lists.
        """
        response = self.session.get(self.PERSONS_LIST_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        options = {"faculties": [], "institutions": []}

        # Faculties (faculty_de[])
        fac_inputs = soup.find_all("input", {"name": "faculty_de[]"})
        for inp in fac_inputs:
            val = inp.get("value")
            if val:
                options["faculties"].append(val)

        # Institutions (other_institution_de[])
        inst_inputs = soup.find_all("input", {"name": "other_institution_de[]"})
        for inp in inst_inputs:
            val = inp.get("value")
            if val:
                options["institutions"].append(val)

        return options

    def get_persons(self, char: Optional[str] = None, faculty: Optional[str] = None, institution: Optional[str] = None) -> List[Dict[str, str]]:
        """Fetches persons based on character, faculty or institution.

        Args:
            char: The first character of the surname.
            faculty: The faculty name.
            institution: The institution name.

        Returns:
            A list of dictionaries containing name, email, and profile_url.
        """
        params = {}
        if char:
            params["pse_surname_first_char[]"] = char
        if faculty:
            params["faculty_de[]"] = faculty
        if institution:
            params["other_institution_de[]"] = institution

        response = self.session.get(self.PERSONS_LIST_URL, params=params)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        persons = []

        # The persons are in <tr> elements
        table_rows = soup.find_all("tr")
        for row in table_rows:
            # Check if this row contains a person link and an email span
            name_link = row.find("a", href=True)
            email_span = row.find("span", class_="email")

            if name_link and email_span:
                name = name_link.get_text(strip=True)
                profile_url = name_link["href"]
                if not profile_url.startswith("http"):
                    profile_url = self.BASE_URL + profile_url

                # Email is often encoded as HTML entities
                email_raw = email_span.get_text(strip=True)
                email = html.unescape(email_raw)

                persons.append({
                    "name": name,
                    "email": email,
                    "profile_url": profile_url
                })

        return persons

    def get_person_details(self, profile_url: str) -> Dict[str, Any]:
        """Fetches additional details for a person from their profile page.

        Args:
            profile_url: The URL of the person's profile.

        Returns:
            A dictionary containing faculty and institute.
        """
        response = self.session.get(profile_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        details = {
            "academic_degree": None,
            "faculty": None,
            "institute": None,
            "is_pa_vorsitz": False,
            "is_dekan": False,
            "is_senat": False,
            "is_institutsdirektor": False,
            "is_praesidium": False,
            "studiengangsleitung": None
        }

        intro_div = soup.find("div", class_="introduction-personal")
        if not intro_div:
            intro_div = soup.find("div", class_="personal-site")
        if intro_div:
            # Extract academic degree
            degree_span = intro_div.find("span", class_="academic-degree")
            if degree_span:
                details["academic_degree"] = degree_span.get_text(strip=True)

            # Check name for Prof. / Prof. Dr.
            name_h1 = intro_div.find("h1")
            if name_h1:
                full_name = name_h1.get_text(strip=True)
                if "Prof. Dr." in full_name:
                    details["academic_degree"] = "Prof. Dr."
                elif "Prof." in full_name:
                    details["academic_degree"] = "Prof."
            # Faculty is usually in a link with class 'link internal'
            faculty_link = intro_div.find("a", class_="link internal")
            if faculty_link:
                details["faculty"] = faculty_link.get_text(strip=True)

            # Institute is usually in a <p> tag
            p_tags = intro_div.find_all("p")
            for p in p_tags:
                text = p.get_text(strip=True)
                if text and "Institut" in text:
                    details["institute"] = text
                    break

        # Extract functions
        functions_header = soup.find("h2", string=lambda t: t and "Funktionen" in t)
        if functions_header:
            functions_div = functions_header.find_next_sibling("div", class_="richtext-personal")
            if functions_div:
                function_items = functions_div.find_all("span")
                for item in function_items:
                    text = item.get_text(strip=True)
                    if "Prüfungsausschussvorsitzende/r" in text:
                        details["is_pa_vorsitz"] = True
                    if "DekanIn" in text:
                        details["is_dekan"] = True
                    if "Senatsmitglied" in text:
                        details["is_senat"] = True
                    if "InstitutsdirektorIn" in text:
                        details["is_institutsdirektor"] = True
                    if any(term in text for term in ["Vizepräsident", "Vizepräsidentin", "Präsident", "Präsidentin"]) and "Ehemalig" not in text:
                        details["is_praesidium"] = True
                    if "Studiengangsleitung" in text:
                        details["studiengangsleitung"] = "ja" if text.strip() == "Studiengangsleitung" else text.strip()
        return details
    def crawl(self, chars: List[str], faculty: Optional[str] = None, institution: Optional[str] = None) -> List[Dict[str, Any]]:
        """Crawls persons for a list of characters and/or faculty/institution.

            institution: Optional institution to filter by.

        Returns:
            A list of dictionaries with full person details.
        """
        all_data = []

        if not chars and (faculty or institution):
            items_to_process = [(None, faculty, institution)]
        else:
            items_to_process = [(char.strip().upper(), faculty, institution) for char in chars if char.strip()]

        for char, fac, inst in items_to_process:
            if char:
                print(f"Crawling character: {char}" + (f" (Faculty: {fac})" if fac else "") + (f" (Institution: {inst})" if inst else ""))
            else:
                print("Crawling" + (f" Faculty: {fac}" if fac else "") + (f" Institution: {inst}" if inst else ""))

            try:
                persons = self.get_persons(char=char, faculty=fac, institution=inst)
                for person in persons:
                    print(f"  Fetching details for: {person['name']}")
                    try:
                        details = self.get_person_details(person["profile_url"])
                        person.update(details)
                        all_data.append(person)
                    except Exception as e:
                        print(f"    Error fetching details for {person['name']}: {e}")
                self._wait()
            except Exception as e:
                print(f"  Error crawling: {e}")

        return all_data


def save_to_markdown(data: List[Dict[str, Any]], filename: str) -> None:
    """Saves the crawled data to a Markdown file.

    Args:
        data: The list of person dictionaries.
        filename: The output filename.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Personen TH Köln\n\n")

        f.write("| Name | Akademischer Grad | E-Mail | Fakultät oder Einrichtung | Institut | PA-Vorsitz | DekanIn | Senat | InstitutsdirektorIn | Präsidiumsmitglied | Studiengangsleitung |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for person in data:
            name = person.get("name") or ""
            degree = person.get("academic_degree") or ""
            email = person.get("email") or ""
            faculty = person.get("faculty") or ""
            institute = person.get("institute") or ""
            pa = "X" if person.get("is_pa_vorsitz") else ""
            dekan = "X" if person.get("is_dekan") else ""
            senat = "X" if person.get("is_senat") else ""
            inst_dir = "X" if person.get("is_institutsdirektor") else ""
            praesidium = "X" if person.get("is_praesidium") else ""
            studiengangsleitung = person.get("studiengangsleitung") or ""
            f.write(f"| {name} | {degree} | {email} | {faculty} | {institute} | {pa} | {dekan} | {senat} | {inst_dir} | {praesidium} | {studiengangsleitung} |\n")


def parse_markdown_files(directory: Path) -> List[Dict[str, Any]]:
    """Parses Markdown files in the directory to extract person data.

    Args:
        directory: Path to the directory containing Markdown files.

    Returns:
        A list of person dictionaries.
    """
    all_persons = []
    md_files = glob.glob(str(directory / "*.md"))

    for md_file in md_files:
        with open(md_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            if line.startswith("| ") and "Name" not in line and "---" not in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 10:
                    person = {
                        "name": parts[1],
                        "academic_degree": parts[2] if parts[2] != "None" and parts[2] != "" else None,
                        "email": parts[3],
                        "faculty": parts[4] if parts[4] != "None" and parts[4] != "" else None,
                        "institute": parts[5] if parts[5] != "None" and parts[5] != "" else None,
                        "is_pa_vorsitz": parts[6] == "X",
                        "is_dekan": parts[7] == "X",
                        "is_senat": parts[8] == "X",
                        "is_institutsdirektor": parts[9] == "X",
                        "is_praesidium": parts[10] == "X",
                        "studiengangsleitung": parts[11] if len(parts) > 11 and parts[11] != "" else None
                    }
                    all_persons.append(person)
    return all_persons


def save_to_database(data: List[Dict[str, Any]], db_path: Path) -> None:
    """Saves the crawled data to the metadata database.

    Args:
        data: The list of person dictionaries.
        db_path: Path to the SQLite database.
    """
    os.makedirs(db_path.parent, exist_ok=True)
    store = MetadataStore(db_path)

    for person in data:
        name = person.get("name")
        email = person.get("email")
        faculty = person.get("faculty")
        institute = person.get("institute")

        if not name:
            continue

        # Properties for person node
        properties = {
            "email": email,
            "is_pa_vorsitz": person.get("is_pa_vorsitz", False),
            "academic_degree": person.get("academic_degree"),
            "is_dekan": person.get("is_dekan", False),
            "is_senat": person.get("is_senat", False),
            "is_institutsdirektor": person.get("is_institutsdirektor", False),
            "is_praesidium": person.get("is_praesidium", False),
            "studiengangsleitung": person.get("studiengangsleitung")
        }

        # Create person node
        person_id, _ = store.upsert_node(name, "Person", properties)

        # Create role nodes and edges
        if person.get("is_dekan"):
            role_id, _ = store.upsert_node("DekanIn", "DekanIn")
            store.upsert_edge(person_id, role_id, "hat Funktion")
            # Link to Dekanat if it exists
            dekanat_id, _ = store.upsert_node("Dekanat", "Dekanat")
            store.upsert_edge(role_id, dekanat_id, "ist Element von")

        if person.get("is_pa_vorsitz"):
            role_id, _ = store.upsert_node("Prüfungsausschussvorsitz", "Prüfungsausschussvorsitz")
            store.upsert_edge(person_id, role_id, "hat Funktion")

        if person.get("is_institutsdirektor"):
            role_id, _ = store.upsert_node("InstitutsdirektorIn", "InstitutsdirektorIn")
            store.upsert_edge(person_id, role_id, "hat Funktion")

        if person.get("is_senat"):
            role_id, _ = store.upsert_node("Senat", "Senat")
            store.upsert_edge(person_id, role_id, "ist Element von")

        if person.get("is_praesidium"):
            role_id, _ = store.upsert_node("Präsidium", "Präsidium")
            store.upsert_edge(person_id, role_id, "ist Element von")

        if faculty:
            # Create faculty/einrichtung node
            fac_node_type = "Fakultät" if "Fakultät" in faculty else "Einrichtung"
            fac_id, _ = store.upsert_node(faculty, fac_node_type)

            # Special logic for F10
            is_f10 = "Fakultät für Informatik und Ingenieurwissenschaften" in faculty

            if is_f10 and institute:
                # Create institute node
                inst_id, _ = store.upsert_node(institute, "Institut")

                # Edge: Institute -> Faculty
                store.upsert_edge(inst_id, fac_id, "ist Element von")

                # Edge: Person -> Institute
                store.upsert_edge(person_id, inst_id, "ist Element von")
            else:
                # Edge: Person -> Faculty/Einrichtung
                store.upsert_edge(person_id, fac_id, "ist Element von")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Crawl person data from TH Köln website.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/crawl_th_koeln_persons.py A
  python scripts/crawl_th_koeln_persons.py --faculty "Informatik und Ingenieurwissenschaften"
  python scripts/crawl_th_koeln_persons.py --institution "Campus IT"
  python scripts/crawl_th_koeln_persons.py --crawl-all both
  python scripts/crawl_th_koeln_persons.py --rebuild
        """
    )
    parser.add_argument(
        "chars",
        nargs="*",
        help="Characters to crawl (e.g. A B or 'A, B'). If multiple characters are provided in one string separated by commas, they will be split."
    )
    parser.add_argument(
        "--faculty",
        type=str,
        help="Faculty to crawl (e.g. 'Informatik und Ingenieurwissenschaften')."
    )
    parser.add_argument(
        "--institution",
        type=str,
        help="Institution to crawl (e.g. 'Campus IT')."
    )
    parser.add_argument(
        "--crawl-all",
        choices=["faculties", "institutions", "both"],
        help="Crawl all persons for all faculties, institutions or both."
    )
    parser.add_argument(
        "--list-faculties",
        action="store_true",
        help="List all available faculties and exit."
    )
    parser.add_argument(
        "--list-institutions",
        action="store_true",
        help="List all available institutions and exit."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the database from existing Markdown files in data/th_koeln/."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=get_config().th_personal_path,
        help=f"Path to the university metadata database (default: {get_config().th_personal_path})."
    )

    args = parser.parse_args()

    if args.rebuild:
        md_dir = Path("data/th_koeln")
        if not md_dir.exists():
            print(f"Error: Directory {md_dir} does not exist.")
            return

        print(f"Rebuilding database from Markdown files in {md_dir}...")
        all_data = parse_markdown_files(md_dir)
        if not all_data:
            print("No person data found in Markdown files.")
            return

        save_to_database(all_data, args.db)
        print(f"Successfully rebuilt database with {len(all_data)} persons.")
        return

    crawler = THKoelnCrawler()

    if args.list_faculties or args.list_institutions:
        options = crawler.get_filter_options()
        if args.list_faculties:
            print("Available Faculties:")
            for fac in options["faculties"]:
                print(f"  - {fac}")
        if args.list_institutions:
            print("Available Institutions:")
            for inst in options["institutions"]:
                print(f"  - {inst}")
        return

    all_data = []
    az_chars = list(string.ascii_uppercase)

    if args.crawl_all:
        options = crawler.get_filter_options()
        categories = []
        if args.crawl_all in ["faculties", "both"]:
            for f in options["faculties"]:
                categories.append({"faculty": f})
        if args.crawl_all in ["institutions", "both"]:
            for i in options["institutions"]:
                categories.append({"institution": i})

        for cat in categories:
            faculty = cat.get("faculty")
            institution = cat.get("institution")
            data = crawler.crawl(az_chars, faculty=faculty, institution=institution)
            all_data.extend(data)
    else:
        # Process characters: handle space-separated args and comma-separated strings
        chars_to_crawl = []
        for arg in args.chars:
            if "," in arg:
                chars_to_crawl.extend([c.strip() for c in arg.split(",")])
            else:
                chars_to_crawl.append(arg.strip())

        if not chars_to_crawl and (args.faculty or args.institution):
            print("Filter specified, crawling A-Z for this filter.")
            chars_to_crawl = az_chars
        elif not chars_to_crawl:
            print("No filters specified, crawling entire TH (A-Z).")
            chars_to_crawl = az_chars

        all_data = crawler.crawl(chars_to_crawl, faculty=args.faculty, institution=args.institution)

    if not all_data:
        print("No persons found.")
        return

    # Save separate files by faculty/institution
    by_faculty = {}
    for person in all_data:
        fac = person.get("faculty") or "Unbekannt"
        if fac not in by_faculty:
            by_faculty[fac] = []

        # Avoid duplicates in the same file if person found multiple times
        if person not in by_faculty[fac]:
            by_faculty[fac].append(person)

    for fac, fac_data in by_faculty.items():
        # Sanitize filename
        safe_fac = re.sub(r'[^a-zA-Z0-9]', '_', fac)
        fac_filename = f"data/th_koeln/persons_{safe_fac}.md"
        save_to_markdown(fac_data, fac_filename)
        print(f"Saved {len(fac_data)} persons for {fac} to {fac_filename}")

    # Save to Database
    save_to_database(all_data, args.db)
    print(f"Updated database at {args.db}")


if __name__ == "__main__":
    main()
