"""Skript zum rekursiven Löschen leerer Ordner."""

import argparse
from pathlib import Path


def remove_empty_folders(path: Path) -> int:
    """Löscht rekursiv alle leeren Ordner unterhalb des angegebenen Pfads.

    Args:
        path: Der Startordner für die Suche.

    Returns:
        int: Die Anzahl der gelöschten Ordner.
    """
    deleted_count = 0

    if not path.is_dir():
        return 0

    # Erst die Unterordner bereinigen (Bottom-Up)
    for entry in list(path.iterdir()):
        if entry.is_dir():
            deleted_count += remove_empty_folders(entry)

    # Wenn der Ordner jetzt leer ist, löschen (außer den Startordner selbst)
    # Falls der Startordner auch gelöscht werden soll, wenn er leer ist:
    if not any(path.iterdir()):
        try:
            path.rmdir()
            deleted_count += 1
        except OSError as e:
            print(f"Fehler beim Löschen von {path}: {e}")

    return deleted_count


def main():
    """Haupteinstiegspunkt für das Skript."""
    parser = argparse.ArgumentParser(description="Löscht rekursiv leere Ordner.")
    parser.add_argument("directory", help="Der Startordner für die Bereinigung.")
    args = parser.parse_args()

    start_path = Path(args.directory)
    if not start_path.exists() or not start_path.is_dir():
        print(f"Fehler: '{args.directory}' ist kein gültiges Verzeichnis.")
        return

    print(f"Starte Bereinigung in: {start_path.absolute()}")
    total_deleted = remove_empty_folders(start_path)
    print(f"Fertig. Es wurden {total_deleted} leere Ordner gelöscht.")


if __name__ == "__main__":
    main()
