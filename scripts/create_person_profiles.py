"""Skript zur manuellen Erstellung von Personen-Steckbriefen aus E-Mails."""
import argparse
import logging
from pathlib import Path
from mcp_university.summarizer.profiler import PersonProfiler

def main() -> None:
    """Haupteinstiegspunkt für das CLI-Tool zur Erstellung von Personen-Steckbriefen."""
    parser = argparse.ArgumentParser(description="Erstellt Steckbriefe für Personen aus E-Mails.")
    parser.add_argument("--email", type=str, required=True, help="E-Mail-Adresse der Person.")
    parser.add_argument("--storage", type=str, default="D:\\Steckbriefe", help="Speicherpfad für Steckbriefe.")
    parser.add_argument("--force", action="store_true", help="Aktualisierung erzwingen.")
    parser.add_argument("--debug", action="store_true", help="Debug-Logging aktivieren.")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    profiler = PersonProfiler(storage_path=Path(args.storage))

    print(f"Suche E-Mails für {args.email}...")
    profile = profiler.generate_profile(args.email, force_update=args.force)

    if profile:
        print("\n--- Steckbrief erstellt ---\n")
        print(profile)
        print(f"\nGespeichert in: {Path(args.storage) / f'{args.email}.md'}")
    else:
        print(f"Fehler: Es konnte kein Steckbrief für {args.email} erstellt werden.")

if __name__ == "__main__":
    main()
