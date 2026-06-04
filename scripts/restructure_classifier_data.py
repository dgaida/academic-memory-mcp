from mcp_university.config import get_config
"""Skript zur Umstrukturierung der Trainings- und Testdaten des Klassifikators."""
import argparse
import shutil
from pathlib import Path
import logging

try:
    import extract_msg
except ImportError:
    print("Bitte installiere extract-msg: pip install extract-msg")
    exit(1)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Warnungen von extract-msg unterdrücken
logging.getLogger("extract_msg").setLevel(logging.ERROR)

def restructure_data(root_dir: Path):
    """Verschiebt E-Mails in Inbox/SentItems Unterordner pro Klasse.

    Args:
        root_dir: Wurzelverzeichnis mit Klassen-Unterordnern.
    """
    if not root_dir.exists():
        logger.error(f"Verzeichnis {root_dir} existiert nicht.")
        return

    for class_dir in root_dir.iterdir():
        if not class_dir.is_dir():
            continue

        logger.info(f"Verarbeite Klasse: {class_dir.name}")

        # Inbox und SentItems Ordner erstellen
        inbox_dir = class_dir / "Inbox"
        sent_dir = class_dir / "SentItems"

        # Wir suchen nur direkt im Klassenordner nach .msg Dateien (nicht rekursiv,
        # da wir sie in Unterordner verschieben wollen und Endlosschleifen/Doppelverarbeitung vermeiden wollen)
        msg_files = list(class_dir.glob("*.msg"))

        if not msg_files:
            logger.info(f"Keine .msg Dateien direkt in {class_dir.name} gefunden.")
            continue

        inbox_dir.mkdir(exist_ok=True)
        sent_dir.mkdir(exist_ok=True)

        for msg_file in msg_files:
            try:
                # Absender extrahieren und Datei danach sofort schließen
                with extract_msg.openMsg(str(msg_file)) as msg:
                    sender = (msg.sender.lower() if msg.sender else "").strip()

                # Datei verschieben (außerhalb des Context-Managers, um Locks zu vermeiden)
                if get_config().user.email in sender:
                    target_path = sent_dir / msg_file.name
                    shutil.move(str(msg_file), str(target_path))
                    logger.info(f"Verschoben nach SentItems: {msg_file.name}")
                else:
                    target_path = inbox_dir / msg_file.name
                    shutil.move(str(msg_file), str(target_path))
                    logger.info(f"Verschoben nach Inbox: {msg_file.name}")
            except Exception as e:
                logger.error(f"Fehler beim Verarbeiten von {msg_file.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Restrukturiert E-Mail-Klassifikationsdaten in Inbox/SentItems.")
    parser.add_argument("data_dir", type=str, help="Verzeichnis mit den Klassen-Unterordnern.")
    args = parser.parse_args()

    restructure_data(Path(args.data_dir))

if __name__ == "__main__":
    main()
