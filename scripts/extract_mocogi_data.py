import sys
import os
from pathlib import Path
import json
import logging
import argparse
from typing import Optional

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from mcp_university.metadata.store import MetadataStore
from mcp_university.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_person_name(name: str) -> str:
    """Normalisiert Personennamen (Titel entfernen, etc)."""
    titles = ["Prof.", "Dr.", "h.c.", "phil.", "rer.", "nat.", "techn.", "ing."]
    for title in titles:
        name = name.replace(title, "")
    return " ".join(name.split()).strip()

def match_person(store: MetadataStore, name: str) -> Optional[int]:
    """Sucht eine Person im Wissensgraphen."""
    normalized_name = normalize_person_name(name)
    nodes = store.get_all_nodes()

    search_words = set(normalized_name.lower().replace(",", " ").split())

    for node in nodes:
        if node["type"] == "Person":
            node_name = normalize_person_name(node["name"])
            node_words = set(node_name.lower().replace(",", " ").split())
            if search_words == node_words:
                return node["id"]
    return None

def main():
    parser = argparse.ArgumentParser(description="Extrahiert Daten aus MOCOGI JSON.")
    parser.add_argument("json_file", type=Path, help="Pfad zur MOCOGI JSON Datei.")
    parser.add_argument("--db", type=Path, help="Pfad zur Datenbank.")
    parser.add_argument("--output", type=Path, default=Path("data/mocogi_modules.md"), help="Pfad zur Markdown-Ausgabe.")
    args = parser.parse_args()

    cfg = get_config()
    db_path = args.db or cfg.sqlite_path
    store = MetadataStore(db_path)

    if not args.json_file.exists():
        logger.error(f"Datei nicht gefunden: {args.json_file}")
        return

    with open(args.json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Verarbeite MOCOGI Daten aus {args.json_file}...")

    os.makedirs(args.output.parent, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as md:
        md.write("# MOCOGI Module und Studiengänge\n\n")

        for sp in data:
            sp_name = sp.get("studiengang", "Unbekannt")
            md.write(f"## Studiengang: {sp_name}\n\n")

            sp_node_id, _ = store.upsert_node(sp_name, "Studiengang")

            for po in sp.get("pruefungsordnungen", []):
                po_name = po.get("name", "Unbekannte PO")
                md.write(f"### Prüfungsordnung: {po_name}\n\n")

                po_node_id, _ = store.upsert_node(po_name, "Prüfungsordnung")
                store.upsert_edge(po_node_id, sp_node_id, "ist Element von")

                md.write("| Modul | Verantwortlich | Rolle |\n")
                md.write("| --- | --- | --- |\n")

                for m in po.get("module", []):
                    m_title = m.get("titel", "Unbekanntes Modul")

                    module_node_id, _ = store.upsert_node(m_title, "Modul")
                    store.upsert_edge(module_node_id, po_node_id, "ist Element von")

                    persons = m.get("personen", [])
                    for p in persons:
                        p_name = p.get("name", "Unbekannt")
                        role_name = p.get("rolle", "Beteiligt")
                        md.write(f"| {m_title} | {p_name} | {role_name} |\n")

                        person_id = match_person(store, p_name)
                        if person_id:
                            store.upsert_edge(person_id, module_node_id, role_name)
                md.write("\n")

    logger.info(f"Extraktion abgeschlossen. Ergebnisse in {args.output} und DB {db_path}")

if __name__ == "__main__":
    main()
