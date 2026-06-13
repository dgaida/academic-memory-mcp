"""Script to crawl persons from TH Köln website and extract their details.

This script fetches a list of persons from the TH Köln personnel page,
extracts their names and email addresses, and then visits their individual
profile pages to extract their faculty and institute information.
The results are saved in a Markdown table and in the university metadata database.
"""

import argparse
import html
import random
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from mcp_university.metadata.store import MetadataStore


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

    def get_persons_from_char(self, char: str) -> List[Dict[str, str]]:
        """Fetches persons starting with a specific character.

        Args:
            char: The first character of the surname.

        Returns:
            A list of dictionaries containing name, email, and profile_url.
        """
        params = {"pse_surname_first_char[]": char}
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

    def get_person_details(self, profile_url: str) -> Dict[str, Optional[str]]:
        """Fetches faculty and institute from a person's profile page.

        Args:
            profile_url: The URL of the person's profile page.

        Returns:
            A dictionary containing 'faculty' and 'institute'.
        """
        self._wait()
        response = self.session.get(profile_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        details = {"faculty": None, "institute": None}

        intro_div = soup.find("div", class_="introduction-personal")
        if intro_div:
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

        return details

    def crawl(self, chars: List[str]) -> List[Dict[str, str]]:
        """Crawls persons for a list of characters.

        Args:
            chars: List of characters to crawl.

        Returns:
            A list of dictionaries with full person details.
        """
        all_data = []
        for char in chars:
            char = char.strip().upper()
            if not char:
                continue
            print(f"Crawling character: {char}")
            persons = self.get_persons_from_char(char)
            for person in persons:
                print(f"  Fetching details for: {person['name']}")
                try:
                    details = self.get_person_details(person["profile_url"])
                    person.update(details)
                    all_data.append(person)
                except Exception as e:
                    print(f"    Error fetching details for {person['name']}: {e}")
            self._wait()
        return all_data


def save_to_markdown(data: List[Dict[str, str]], filename: str) -> None:
    """Saves the crawled data to a Markdown file.

    Args:
        data: The list of person dictionaries.
        filename: The output filename.
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Personen TH Köln\n\n")
        f.write("| Name | E-Mail | Fakultät oder Einrichtung | Institut |\n")
        f.write("| --- | --- | --- | --- |\n")
        for person in data:
            name = person.get("name") or ""
            email = person.get("email") or ""
            faculty = person.get("faculty") or ""
            institute = person.get("institute") or ""
            f.write(f"| {name} | {email} | {faculty} | {institute} |\n")


def save_to_database(data: List[Dict[str, str]], db_path: Path) -> None:
    """Saves the crawled data to the metadata database.

    Args:
        data: The list of person dictionaries.
        db_path: Path to the SQLite database.
    """
    store = MetadataStore(db_path)

    for person in data:
        name = person.get("name")
        email = person.get("email")
        faculty = person.get("faculty")
        institute = person.get("institute")

        if not name:
            continue

        # Create person node
        person_id, _ = store.upsert_node(name, "Person", {"email": email})

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
  python scripts/crawl_th_koeln_persons.py "A, B"
  python scripts/crawl_th_koeln_persons.py A B C
        """
    )
    parser.add_argument(
        "chars",
        nargs="*",
        help="Characters to crawl (e.g. A B or 'A, B'). If multiple characters are provided in one string separated by commas, they will be split."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/metadata/university.db"),
        help="Path to the university metadata database (default: data/metadata/university.db)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="th_koeln_persons.md",
        help="Path to the output Markdown file (default: th_koeln_persons.md)."
    )

    args = parser.parse_args()

    # Process characters: handle space-separated args and comma-separated strings
    chars_to_crawl = []
    for arg in args.chars:
        if "," in arg:
            chars_to_crawl.extend([c.strip() for c in arg.split(",")])
        else:
            chars_to_crawl.append(arg.strip())

    if not chars_to_crawl:
        # Default to A for demonstration if no args
        print("No characters specified, defaulting to 'A'.")
        chars_to_crawl = ["A"]

    crawler = THKoelnCrawler()
    data = crawler.crawl(chars_to_crawl)

    # Save to Markdown
    save_to_markdown(data, args.output)
    print(f"Saved {len(data)} persons to {args.output}")

    # Save to Database
    save_to_database(data, args.db)
    print(f"Updated database at {args.db}")


if __name__ == "__main__":
    main()
