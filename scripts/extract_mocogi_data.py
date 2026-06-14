"""Script to extract all modules and their examiners from the MOCOGI API.

This script iterates through all study programs and their examination regulations (POs),
fetches all modules for each PO, and extracts the module coordinator,
first examiner, and second examiner. The results are saved in a Markdown file.
Abbreviations are resolved to full names using the /identities endpoint.
"""

import json
import logging
import os
import pathlib
import sys
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("mocogi_extractor")

class PersonResolver:
    """Resolves person IDs or abbreviations to full names."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.identity_map: Dict[str, str] = {}
        self.loaded = False

    def load_identities(self) -> None:
        """Fetches all identities and builds a mapping."""
        if self.loaded:
            return

        logger.info("Lade Personen-Mapping von /identities...")
        try:
            identities = api_call(f"{self.base_url}/identities")
            if not isinstance(identities, list):
                logger.warning("Unerwartetes Format für /identities")
                return

            for item in identities:
                item_id = item.get("id")
                if not item_id:
                    continue

                if item.get("kind") == "person":
                    first_name = item.get("firstname") or ""
                    last_name = item.get("lastname") or ""
                    title = item.get("title") or ""
                    parts = [p for p in [title, first_name, last_name] if p]
                    full_name = " ".join(parts).strip()
                    self.identity_map[item_id] = full_name
                elif item.get("kind") == "group":
                    self.identity_map[item_id] = item.get("label") or item_id

            self.loaded = True
            logger.info(f"{len(self.identity_map)} Identitäten geladen.")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Identitäten: {e}")

    def resolve(self, person_id: Any) -> str:
        """Resolves a person ID or a list of IDs to a name string."""
        if not person_id:
            return "-"

        if isinstance(person_id, list):
            items = [self.resolve(p) for p in person_id if p]
            return ", ".join([i for i in items if i != "-"]) or "-"

        if isinstance(person_id, str):
            # Check if it's already a resolved object from details (legacy fallback)
            return self.identity_map.get(person_id, person_id)

        if isinstance(person_id, dict):
            # Handle cases where the API might already return an object
            first_name = person_id.get("firstName") or person_id.get("firstname") or ""
            last_name = person_id.get("lastName") or person_id.get("lastname") or ""
            title = person_id.get("title") or ""
            parts = [p for p in [title, first_name, last_name] if p]
            return " ".join(parts).strip() or "-"

        return str(person_id)

def load_env_manual() -> None:
    """Lädt Umgebungsvariablen aus .env oder secrets.env manuell."""
    possible_paths = [
        pathlib.Path.cwd() / "secrets.env",
        pathlib.Path.cwd() / ".env",
        pathlib.Path(__file__).resolve().parent.parent / "secrets.env",
        pathlib.Path(__file__).resolve().parent.parent / ".env",
        pathlib.Path(__file__).resolve().parent.parent / "config" / "secrets.env",
    ]

    found = False
    for path in possible_paths:
        if path.exists():
            logger.info(f"Lade Umgebungsvariablen aus {path}")
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            key, value = parts
                            key = key.strip()
                            if key.lower().startswith("export "):
                                key = key[7:].strip()
                            value = value.strip().strip("'").strip('"')
                            os.environ[key] = value
            found = True
            break

    if not found:
        logger.warning("Keine .env oder secrets.env Datei gefunden.")

    if not os.getenv("MOCOGI_API_TOKEN") and os.getenv("MOCOGI_API_KEY"):
        os.environ["MOCOGI_API_TOKEN"] = os.environ["MOCOGI_API_KEY"]

def api_call(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    extra_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Führt einen API-Call mit urllib aus."""
    headers = {"User-Agent": "Mocogi-Extractor-Script/1.0"}
    token = os.getenv("MOCOGI_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if extra_headers:
        headers.update(extra_headers)

    payload = None
    if data:
        payload = json.dumps(data).encode("utf-8")
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=payload, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            if body:
                return json.loads(body)
            return {}
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Fehler: {e.code} - {e.reason} bei {url}")
        raise
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim API-Call: {e}")
        raise

def extract_data() -> None:
    """Extrahiert alle Studiengänge, POs und Module."""
    load_env_manual()
    base_url = "https://module.gm.th-koeln.de/api"
    output_file = "mocogi_modules.md"

    resolver = PersonResolver(base_url)
    resolver.load_identities()

    logger.info("Starte Datenextraktion...")

    try:
        # 1. Hole Studiengänge
        study_programs_list = api_call(f"{base_url}/studyPrograms?filter=not-expired")
        logger.info(f"{len(study_programs_list)} Studiengänge gefunden.")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# MOCOGI Modulübersicht\n\n")

            for sp_summary in study_programs_list:
                sp_id = sp_summary.get("id")
                sp_name = sp_summary.get("deLabel") or sp_summary.get("name") or sp_id

                logger.info(f"Verarbeite Studiengang: {sp_name} ({sp_id})")

                pos = []
                if "pos" in sp_summary:
                    pos = sp_summary["pos"]
                elif "po" in sp_summary:
                    pos = [sp_summary["po"]]

                if not pos:
                    try:
                        sp_details = api_call(f"{base_url}/studyPrograms/{sp_id}")
                        pos = sp_details.get("pos") or []
                        if not pos and "po" in sp_details:
                            pos = [sp_details["po"]]
                    except Exception as e:
                        logger.warning(f"Konnte Details für {sp_id} nicht laden: {e}")

                if not pos:
                    continue

                f.write(f"## {sp_name}\n\n")

                for po in pos:
                    po_id = po.get("id")
                    po_version = po.get("version")
                    po_name = f"PO {po_version}" if po_version else po_id

                    logger.info(f"  Lade Module für PO: {po_name} ({po_id})")
                    f.write(f"### {po_name}\n\n")
                    f.write("| Modulname | Modulverantwortlich | Erstprüfer | Zweitprüfer |\n")
                    f.write("| :--- | :--- | :--- | :--- |\n")

                    # 2. Hole Module für PO
                    modules_url = f"{base_url}/modules?po={po_id}&active=true&select=metadata"
                    modules_list = api_call(modules_url)

                    modules = modules_list if isinstance(modules_list, list) else modules_list.get('module', [])

                    if not modules:
                        f.write("| - | - | - | - |\n\n")
                        continue

                    for m_item in modules:
                        m_basic = m_item.get('module') if isinstance(m_item, dict) and 'module' in m_item else m_item
                        m_meta = m_basic.get('metadata') if isinstance(m_basic, dict) and 'metadata' in m_basic else m_basic

                        m_title = m_meta.get('title', 'Unbekannt')

                        # Extrahiere Verantwortliche und Prüfer
                        manager = resolver.resolve(m_meta.get("moduleManagement") or m_meta.get("management"))

                        examiner = m_meta.get("examiner") or {}
                        first_examiner = resolver.resolve(examiner.get("first"))
                        second_examiner = resolver.resolve(examiner.get("second"))

                        f.write(f"| {m_title} | {manager} | {first_examiner} | {second_examiner} |\n")

                    f.write("\n")

        logger.info(f"Extraktion abgeschlossen. Ergebnisse in {output_file}")

    except Exception as e:
        logger.error(f"Kritischer Fehler bei der Extraktion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    extract_data()
