"""CLI-Modul für das Datenbank-Management."""
import typer
from typing import List, Tuple
from rich.console import Console
from rich.table import Table
from ..config import get_config
from ..metadata.store import MetadataStore
from ..metadata.kg_store import KnowledgeGraphStore
from ..retrieval.index import SearchIndex

db_app = typer.Typer(help="Datenbank-Management-Befehle")
console = Console()

def get_metadata_store() -> MetadataStore:
    """Gibt den MetadataStore zurück."""
    return MetadataStore(get_config().metadata_db_path)

def get_kg_store() -> KnowledgeGraphStore:
    """Gibt den KnowledgeGraphStore zurück."""
    return KnowledgeGraphStore(get_config().kg_db_path)

def get_store_and_index() -> Tuple[MetadataStore, SearchIndex]:
    """Gibt den Store und den Index zurück."""
    cfg = get_config()
    store = get_metadata_store()
    return store, SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)

@db_app.command("list-files")
def list_files() -> None:
    """Listet indexierte Dateien auf."""
    store, _ = get_store_and_index()
    files = store.get_all_files()
    if not files:
        console.print("Keine Dateien")
        return
    table = Table(title="Dateien")
    table.add_column("Pfad")
    for f in files:
        table.add_row(f['path'])
    console.print(table)

@db_app.command("delete-file")
def delete_file(file_ids: List[int] = typer.Argument(..., help="IDs"), force: bool = typer.Option(False, "--force", "-f")) -> None:
    """Löscht Dateien."""
    store, idx = get_store_and_index()
    for fid in file_ids:
        f = next((x for x in store.get_all_files() if x['id'] == fid), None)
        if f:
            idx.delete_document(f['path'])
        store.delete_file(fid)
    console.print("erfolgreich gelöscht")

@db_app.command("delete-folder")
def delete_folder(folder_id: int, force: bool = typer.Option(False, "--force", "-f")) -> None:
    """Löscht einen Ordner."""
    store, idx = get_store_and_index()
    for f in store.get_folder_files(folder_id):
        idx.delete_document(f[1])
    store.delete_folder(folder_id)
    console.print("erfolgreich gelöscht")

@db_app.command("list-nodes")
def list_nodes(graph_type: str = typer.Option("th_koeln")) -> None:
    """Listet Knoten auf."""
    if graph_type == "th_koeln":
        store = get_kg_store()
    else:
        store, _ = get_store_and_index()
    nodes = store.get_all_nodes()
    table = Table(title="Knoten")
    table.add_column("Name")
    for n in nodes:
        table.add_row(n['name'])
    console.print(table)
