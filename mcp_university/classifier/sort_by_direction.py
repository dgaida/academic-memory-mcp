"""Skript zum Sortieren von E-Mails in Inbox/SentItems basierend auf der Nutzer-Email."""
import argparse
import logging
import shutil
from pathlib import Path
from typing import Dict, List

import extract_msg
from mcp_university.config import get_config

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def sort_emails_by_direction(source_dir: Path, user_emails: List[str]) -> Dict[str, int]:
    """Sortiert .msg Dateien in Inbox oder SentItems.

    Args:
        source_dir: Quellverzeichnis mit .msg Dateien.
        user_emails: Liste der E-Mail-Adressen des Nutzers.

    Returns:
        Dict[str, int]: Statistik der verschobenen Dateien.
    """
    stats = {"Inbox": 0, "SentItems": 0, "Error": 0}
    user_emails = [e.lower() for e in user_emails]

    if not source_dir.exists():
        logger.error(f"Verzeichnis {source_dir} existiert nicht.")
        return stats

    for msg_file in source_dir.glob("*.msg"):
        try:
            target_folder = "Inbox" # Default
            with extract_msg.openMsg(str(msg_file)) as msg:
                sender = (msg.sender.lower() if msg.sender else "").strip()

                # Prüfe ob der Nutzer der Absender ist
                if any(u_email in sender for u_email in user_emails):
                    target_folder = "SentItems"
                else:
                    # Standardmäßig Inbox
                    target_folder = "Inbox"

            if target_folder:
                target_dir = source_dir / target_folder
                target_dir.mkdir(exist_ok=True)

                target_path = target_dir / msg_file.name

                # Falls Datei am Ziel schon existiert, Name anpassen
                if target_path.exists():
                    target_path = target_dir / f"{msg_file.stem}_{stats[target_folder]}{msg_file.suffix}"

                shutil.move(str(msg_file), str(target_path))
                stats[target_folder] += 1
                logger.info(f"Verschoben: {msg_file.name} -> {target_folder}/")

        except Exception as e:
            logger.error(f"Fehler bei {msg_file.name}: {e}")
            stats["Error"] += 1

    return stats

def main() -> None:
    """Main entry point for sorting emails by direction."""
    parser = argparse.ArgumentParser(description="Sortiert E-Mails in Inbox/SentItems.")
    parser.add_argument("source_dir", type=str, help="Ordner mit .msg Dateien.")

    args = parser.parse_args()
    source_path = Path(args.source_dir)

    cfg = get_config()
    user_emails = cfg.user.emails

    logger.info(f"Starte Sortierung in {source_path} für {user_emails}...")
    stats = sort_emails_by_direction(source_path, user_emails)

    logger.info(f"Fertig! Inbox: {stats['Inbox']}, SentItems: {stats['SentItems']}, Fehler: {stats['Error']}")

if __name__ == "__main__":
    main()
