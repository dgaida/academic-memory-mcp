"""Skript zum rekursiven Verschieben aller Dateien in den Startordner."""
import argparse
import shutil
from pathlib import Path


def flatten_directory(base_path: Path) -> int:
    """Verschiebt alle Dateien aus Unterordnern rekursiv in den Basisordner.

    Args:
        base_path: Der Startordner, in den alle Dateien verschoben werden sollen.

    Returns:
        int: Die Anzahl der verschobenen Dateien.
    """
    moved_count = 0

    if not base_path.is_dir():
        return 0

    # Liste aller Dateien in Unterordnern (rekursiv)
    # Wir nutzen list(), um die Iteration stabil zu halten, während wir Dateien verschieben
    for file_path in list(base_path.rglob("*")):
        if file_path.is_file() and file_path.parent != base_path:
            target_name = file_path.name
            target_path = base_path / target_name

            # Namenskollisionen behandeln
            counter = 1
            while target_path.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                target_path = base_path / f"{stem}_{counter}{suffix}"
                counter += 1

            try:
                shutil.move(str(file_path), str(target_path))
                print(f"Verschoben: {file_path} -> {target_path}")
                moved_count += 1
            except OSError as e:
                print(f"Fehler beim Verschieben von {file_path}: {e}")

    return moved_count


def main() -> None:
    """Haupteinstiegspunkt für das Skript."""
    parser = argparse.ArgumentParser(
        description="Verschiebt alle Dateien aus Unterordnern rekursiv in den Startordner."
    )
    parser.add_argument("directory", help="Der Startordner für die Bereinigung.")
    args = parser.parse_args()

    start_path = Path(args.directory)
    if not start_path.exists() or not start_path.is_dir():
        print(f"Fehler: '{args.directory}' ist kein gültiges Verzeichnis.")
        return

    print(f"Starte Flattening in: {start_path.absolute()}")
    total_moved = flatten_directory(start_path)
    print(f"Fertig. Es wurden {total_moved} Dateien in den Basisordner verschoben.")


if __name__ == "__main__":
    main()
