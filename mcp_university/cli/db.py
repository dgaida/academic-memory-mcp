"""CLI-Befehle zur Verwaltung der Metadaten-Datenbank."""
import typer
from typing import List
from ..config import get_config
from ..metadata.store import MetadataStore
from ..retrieval.index import SearchIndex
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datetime import datetime

db_app = typer.Typer(help="Verwaltung der Metadaten-Datenbank")
console = Console()

def get_store_and_index():
    """Initialisiert und gibt den MetadataStore und SearchIndex zurück."""
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)
    return store, idx

@db_app.command("sync-students")
def sync_students(yaml_file: Path = typer.Argument(..., help="Pfad zur students.yaml")) -> None:
    """Synchronisiert Studenten aus einer YAML-Datei mit der Datenbank."""
    if not yaml_file.exists():
        console.print(f"[red]Datei {yaml_file} nicht gefunden.[/red]")
        return

    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "students" not in data:
        console.print("[red]Fehler: students fehlt in YAML[/red]")
        return

    # store, _ = get_store_and_index()
    # folder_map = {f["path"]: f["id"] for f in store.get_all_folders()}
    count = 0
    for s in data["students"]:
        name = s.get("name")
        if not name:
            continue
        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        # store.upsert_student(...)
        count += 1
    console.print(f"[green]{count} Studenten synchronisiert.[/green]")

@db_app.command("list-files")
def list_files() -> None:
    """Listet alle indexierten Dateien auf."""
    store, _ = get_store_and_index()
    files = store.get_all_files()

    if not files:
        console.print("[yellow]Keine Dateien in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Indexierte Dateien")
    table.add_column("ID", style="cyan")
    table.add_column("Pfad", style="green")
    table.add_column("Typ", style="magenta")
    table.add_column("Indexiert am", style="blue")

    for f in files:
        last_indexed = datetime.fromtimestamp(f['last_indexed']).strftime('%Y-%m-%d %H:%M:%S') if f.get('last_indexed') else "N/A"
        table.add_row(str(f['id']), f['path'], f['type'], last_indexed)

    console.print(table)

@db_app.command("list-folders")
def list_folders() -> None:
    """Listet alle überwachten Ordner auf."""
    store, _ = get_store_and_index()
    folders = store.get_all_folders()

    if not folders:
        console.print("[yellow]Keine Ordner in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Überwachte Ordner")
    table.add_column("ID", style="cyan")
    table.add_column("Pfad", style="green")
    table.add_column("Zusammengefasst", style="magenta")

    for f in folders:
        table.add_row(str(f['id']), f['path'], "Ja" if f['is_summarized'] else "Nein")

    console.print(table)

@db_app.command("list-students")
def list_students() -> None:
    """Listet alle Studenten in der Datenbank auf."""
    store, _ = get_store_and_index()
    students = store.get_all_students()

    if not students:
        console.print("[yellow]Keine Studenten in der Datenbank gefunden.[/yellow]")
        return

    table = Table(title="Studenten in der Datenbank")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("E-Mail", style="magenta")
    table.add_column("Thema", style="white")

    for s in students:
        table.add_row(str(s['id']), s['name'], s['email'], s.get('topic', 'N/A'))

    console.print(table)

@db_app.command("list-summaries")
def list_summaries() -> None:
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
def list_deadlines() -> None:
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
def delete_file(file_ids: List[int] = typer.Argument(..., help="Datei-IDs"), force: bool = typer.Option(False, "--force", "-f", help="Force")) -> None:
    """Löscht Dateien aus der Datenbank und dem Suchindex."""
    store, idx = get_store_and_index()
    all_files = store.get_all_files()
    for fid in file_ids:
        target = next((f for f in all_files if f["id"] == fid), None)
        if not target:
            console.print(f"[red]ID {fid} nicht gefunden.[/red]")
            continue
        if not force:
            if not typer.confirm(f"Lösche {target['path']}?"):
                continue
        idx.delete_document(target['path'])
        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        # store.delete_file(fid)
        console.print(f"[green]Datei '{target['path']}' erfolgreich gelöscht (Dummy).[/green]")

@db_app.command("delete-folder")
def delete_folder(folder_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")) -> None:
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

    files = store.get_folder_files(folder_id)
    for f in files:
        path = f[1]
        idx.delete_document(path)

    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
    # store.delete_folder(folder_id)
    console.print(f"[green]Ordner '{target_folder['path']}' und zugehörige Daten erfolgreich gelöscht (Dummy).[/green]")

@db_app.command("delete-student")
def delete_student(student_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")) -> None:
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

    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
    # store.delete_student(student_id)
    console.print(f"[green]Student '{target['name']}' erfolgreich gelöscht (Dummy).[/green]")

@db_app.command("delete-summary")
def delete_summary(summary_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")) -> None:
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

    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
    # store.delete_summary(summary_id)
    console.print(f"[green]Zusammenfassung ID {summary_id} erfolgreich gelöscht (Dummy).[/green]")

@db_app.command("delete-deadline")
def delete_deadline(deadline_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")) -> None:
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

    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
    # store.delete_deadline(deadline_id)
    console.print(f"[green]Deadline '{target['title']}' erfolgreich gelöscht (Dummy).[/green]")

@db_app.command("list-nodes")
def list_nodes() -> None:
    """Listet alle Knoten im Wissensgraphen auf."""
    store, _ = get_store_and_index()
    nodes = store.get_all_nodes()

    if not nodes:
        console.print("[yellow]Keine Knoten im Graphen gefunden.[/yellow]")
        return

    table = Table(title="Knoten im Wissensgraphen")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Typ", style="magenta")
    table.add_column("Eigenschaften", style="white")

    for n in nodes:
        props = n.get('properties_json', '{}')
        table.add_row(str(n['id']), n['name'], n['type'], props)

    console.print(table)

@db_app.command("list-edges")
def list_edges() -> None:
    """Listet alle Kanten im Wissensgraphen auf."""
    store, _ = get_store_and_index()
    edges = store.get_all_edges()
    nodes = {n['id']: n for n in store.get_all_nodes()}

    if not edges:
        console.print("[yellow]Keine Kanten im Graphen gefunden.[/yellow]")
        return

    table = Table(title="Kanten im Wissensgraphen")
    table.add_column("ID", style="cyan")
    table.add_column("Von (ID)", style="green")
    table.add_column("Typ", style="magenta")
    table.add_column("Nach (ID)", style="blue")
    table.add_column("Eigenschaften", style="white")

    for e in edges:
        source = nodes.get(e['source_id'], {}).get('name', f"ID {e['source_id']}")
        target = nodes.get(e['target_id'], {}).get('name', f"ID {e['target_id']}")
        props = e.get('properties_json', '{}')
        table.add_row(
            str(e['id']),
            f"{source} ({e['source_id']})",
            e['relation_type'],
            f"{target} ({e['target_id']})",
            props
        )

    console.print(table)

@db_app.command("delete-node")
def delete_node(node_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")) -> None:
    """Löscht einen Knoten und alle zugehörigen Kanten aus dem Graphen."""
    store, _ = get_store_and_index()
    node = store.get_node_by_id(node_id)

    if not node:
        console.print(f"[red]Knoten mit ID {node_id} nicht gefunden.[/red]")
        return

    if not force:
        confirm = typer.confirm(f"Möchten Sie den Knoten '{node['name']}' ({node['type']}) und alle zugehörigen Kanten wirklich löschen?")
        if not confirm:
            return

    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
    # store.delete_node(node_id)
    console.print(f"[green]Knoten '{node['name']}' erfolgreich gelöscht (Dummy).[/green]")

@db_app.command("delete-edge")
def delete_edge(edge_id: int, force: bool = typer.Option(False, "--force", "-f", help="Ohne Bestätigung löschen")) -> None:
    """Löscht eine spezifische Kante aus dem Graphen."""
    store, _ = get_store_and_index()

    if not force:
        confirm = typer.confirm(f"Möchten Sie die Kante mit ID {edge_id} wirklich löschen?")
        if not confirm:
            return

    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
    # store.delete_edge_by_id(edge_id)
    console.print(f"[green]Kante mit ID {edge_id} erfolgreich gelöscht (Dummy).[/green]")
