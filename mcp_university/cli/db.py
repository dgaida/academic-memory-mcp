from pathlib import Path
import yaml
"""Datenbank-Management-Befehle für die CLI."""
from typing import Tuple, List
import typer
from rich.console import Console
from rich.table import Table
from datetime import datetime
from ..config import get_config
from ..metadata.store import MetadataStore
from ..retrieval.index import SearchIndex

db_app = typer.Typer(help="Datenbank-Management-Befehle")
console = Console()

def get_store_and_index() -> Tuple[MetadataStore, SearchIndex]:
    """Initialisiert und gibt den MetadataStore und SearchIndex zurück.

    Nutzt die globale Konfiguration, um die Pfade für die SQLite-Datenbank
    und den Qdrant-Index zu bestimmen.

    Returns:
        Tuple[MetadataStore, SearchIndex]: Ein Tupel bestehend aus dem initialisierten
            Store und dem Suchindex.
    """
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)
    return store, idx

@db_app.command("list-files")
def list_files():
    """Listet alle indexierten Dateien in der Datenbank auf."""
    store, _ = get_store_and_index()
    files = store.get_all_files()

    if not files:
        console.print("[yellow]Keine Dateien in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Dateien in der Datenbank")
    table.add_column("ID", style="cyan")
    table.add_column("Pfad", style="green")
    table.add_column("Typ", style="magenta")
    table.add_column("Zuletzt indexiert", style="blue")

    for f in files:
        last_indexed = datetime.fromtimestamp(f['last_indexed']).strftime('%Y-%m-%d %H:%M:%S') if f.get('last_indexed') else "N/A"
        table.add_row(str(f['id']), f['path'], f['type'], last_indexed)

    console.print(table)

@db_app.command("list-folders")
def list_folders():
    """Listet alle überwachten Ordner auf."""
    store, _ = get_store_and_index()
    folders = store.get_all_folders()

    if not folders:
        console.print("[yellow]Keine Ordner in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Ordner in der Datenbank")
    table.add_column("ID", style="cyan")
    table.add_column("Pfad", style="green")
    table.add_column("Zuletzt zusammengefasst", style="blue")

    for f in folders:
        last_summ = datetime.fromtimestamp(f['last_summarized']).strftime('%Y-%m-%d %H:%M:%S') if f.get('last_summarized') else "N/A"
        table.add_row(str(f['id']), f['path'], last_summ)

    console.print(table)


@db_app.command("sync-students")
def sync_students(yaml_path: str = typer.Option("students.yaml", help="Pfad zur students.yaml")):
    path = Path(yaml_path)
    if not path.exists():
        console.print(f"[red]Datei {yaml_path} nicht gefunden.[/red]")
        return
    with open(path, "r") as f: data = yaml.safe_load(f)
    if not data or "students" not in data:
        console.print("[red]Fehler: students fehlt in YAML[/red]")
        return
    store, _ = get_store_and_index()
    folder_map = {f["path"]: f["id"] for f in store.get_all_folders()}
    count = 0
    for s in data["students"]:
        name = s.get("name")
        if not name: continue
        email = s.get("smail") or s.get("email")
        topic, status = s.get("topic"), s.get("status")
        fid = None
        if s.get("folders") and s["folders"][0].get("path") in folder_map:
            fid = folder_map[s["folders"][0]["path"]]
        store.upsert_student(name, email, topic, status, fid)
        count += 1
    console.print(f"[green]{count} Studenten synchronisiert.[/green]")

@db_app.command("list-students")
def list_students():
    """Listet alle Studenten in der Datenbank auf."""
    store, _ = get_store_and_index()
    students = store.get_all_students()

    if not students:
        console.print("[yellow]Keine Studenten in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Studenten in der Datenbank")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Email", style="magenta")
    table.add_column("Status", style="blue")

    for s in students:
        table.add_row(str(s['id']), s['name'], s.get('email', 'N/A'), s.get('status', 'N/A'))

    console.print(table)

@db_app.command("list-summaries")
def list_summaries():
    """Listet alle Zusammenfassungen in der Datenbank auf."""
    store, _ = get_store_and_index()
    summaries = store.get_all_summaries()

    if not summaries:
        console.print("[yellow]Keine Zusammenfassungen in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Zusammenfassungen in der Datenbank")
    table.add_column("ID", style="cyan")
    table.add_column("Typ", style="magenta")
    table.add_column("Item ID", style="green")
    table.add_column("Inhalt (Vorschau)", style="white")
    table.add_column("Erstellt am", style="blue")

    for s in summaries:
        created_at = datetime.fromtimestamp(s['created_at']).strftime('%Y-%m-%d %H:%M:%S') if s.get('created_at') else "N/A"
        preview = (s['content'][:75] + '...') if len(s['content']) > 75 else s['content']
        table.add_row(str(s['id']), s['item_type'], str(s['item_id']), preview, created_at)

    console.print(table)

@db_app.command("list-deadlines")
def list_deadlines():
    """Listet alle Deadlines in der Datenbank auf."""
    store, _ = get_store_and_index()
    deadlines = store.get_all_deadlines()

    if not deadlines:
        console.print("[yellow]Keine Deadlines in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Deadlines in der Datenbank")
    table.add_column("ID", style="cyan")
    table.add_column("Titel", style="green")
    table.add_column("Fällig am", style="magenta")
    table.add_column("Typ", style="blue")

    for d in deadlines:
        due_date = datetime.fromtimestamp(d['due_date']).strftime('%Y-%m-%d %H:%M:%S') if d.get('due_date') else "N/A"
        table.add_row(str(d['id']), d['title'], due_date, d.get('item_type', 'N/A'))

    console.print(table)

@db_app.command("delete-file")
def delete_file(file_ids: List[int] = typer.Argument(..., help="Datei-IDs"), force: bool = typer.Option(False, "--force", "-f", help="Force")):
    store, idx = get_store_and_index()
    all_files = store.get_all_files()
    for fid in file_ids:
        target = next((f for f in all_files if f["id"] == fid), None)
        if not target:
            console.print(f"[red]ID {fid} nicht gefunden.[/red]")
            continue
        if not force:
            if not typer.confirm(f"Lösche {target[path]}?"): continue
        idx.delete_document(target["path"])
        store.delete_file(fid)
        console.print(f"Gelöscht: {target[path]}")

@db_app.command("delete-folder")
def delete_folder(folder_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")):
    """Löscht einen Ordner und alle zugehörigen Dateien aus der Datenbank und dem Index."""
    store, idx = get_store_and_index()

    all_folders = store.get_all_folders()
    target_folder = next((f for f in all_folders if f['id'] == folder_id), None)

    if not target_folder:
        console.print(f"[red]Ordner mit ID {folder_id} nicht gefunden.[/red]")
        return

    if not force:
        confirm = typer.confirm(f"Möchten Sie den Ordner '{target_folder['path']}' und alle darin enthaltenen Dateien wirklich löschen?")
        if not confirm:
            return

    # Find all files in this folder to remove them from search index
    files = store.get_folder_files(folder_id)
    for f in files:
        # f is a tuple: (id, path, hash, mtime, type, last_indexed, folder_id)
        path = f[1]
        idx.delete_document(path)

    # Delete from Database (handles files and summaries too)
    store.delete_folder(folder_id)
    console.print(f"[green]Ordner '{target_folder['path']}' und zugehörige Daten erfolgreich gelöscht.[/green]")

@db_app.command("delete-student")
def delete_student(student_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")):
    """Löscht einen Studenten aus der Datenbank."""
    store, _ = get_store_and_index()

    students = store.get_all_students()
    target = next((s for s in students if s['id'] == student_id), None)

    if not target:
        console.print(f"[red]Student mit ID {student_id} nicht gefunden.[/red]")
        return

    if not force:
        confirm = typer.confirm(f"Möchten Sie den Studenten '{target['name']}' wirklich löschen?")
        if not confirm:
            return

    store.delete_student(student_id)
    console.print(f"[green]Student '{target['name']}' erfolgreich gelöscht.[/green]")

@db_app.command("delete-summary")
def delete_summary(summary_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")):
    """Löscht eine Zusammenfassung aus der Datenbank."""
    store, _ = get_store_and_index()

    summaries = store.get_all_summaries()
    target = next((s for s in summaries if s['id'] == summary_id), None)

    if not target:
        console.print(f"[red]Zusammenfassung mit ID {summary_id} nicht gefunden.[/red]")
        return

    if not force:
        confirm = typer.confirm(f"Möchten Sie die Zusammenfassung ID {summary_id} wirklich löschen?")
        if not confirm:
            return

    store.delete_summary(summary_id)
    console.print(f"[green]Zusammenfassung ID {summary_id} erfolgreich gelöscht.[/green]")

@db_app.command("delete-deadline")
def delete_deadline(deadline_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")):
    """Löscht eine Deadline aus der Datenbank."""
    store, _ = get_store_and_index()

    deadlines = store.get_all_deadlines()
    target = next((d for d in deadlines if d['id'] == deadline_id), None)

    if not target:
        console.print(f"[red]Deadline mit ID {deadline_id} nicht gefunden.[/red]")
        return

    if not force:
        confirm = typer.confirm(f"Möchten Sie die Deadline '{target['title']}' wirklich löschen?")
        if not confirm:
            return

    store.delete_deadline(deadline_id)
    console.print(f"[green]Deadline '{target['title']}' erfolgreich gelöscht.[/green]")
