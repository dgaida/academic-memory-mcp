"""Modul zum Korrigieren der E-Mail-Ordnerstruktur."""
import yaml
import logging
import shutil
import re
from pathlib import Path
from typing import List, Tuple, Iterator
from mcp_university.classifier.sort_emails import extract_lastname, get_semester, find_student_folder
from mcp_university.config import get_config
from mcp_university.parser.mail_parser import MailParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_folders(config_path: Path, dry_run: bool = False, full_verify: bool = False) -> None:
    """Migriert E-Mails in die Standardstruktur: Semester/Nachname/Inbox|SentItems/.

    Args:
        config_path (Path): Pfad zur YAML-Konfigurationsdatei mit Klassenpfaden.
        dry_run (bool): Falls True, werden Fehler nur gemeldet, aber nicht behoben.
        full_verify (bool): Falls True, werden alle E-Mails in Unterverzeichnissen geprüft.
    """
    if not config_path.exists():
        logger.error(f"Konfigurationsdatei {config_path} nicht gefunden.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    config = config_data.get("class_paths", config_data)

    parser = MailParser()
    user_emails = [e.lower() for e in get_config().user.emails]

    for email_class, base_path_str in config.items():
        base_path = Path(base_path_str)
        if not base_path.exists():
            continue

        logger.info(f"Verarbeite Klasse {email_class} in {base_path} (Full Verify: {full_verify}, Dry Run: {dry_run})")

        # E-Mail-Dateien finden
        if full_verify:
            email_files = list(base_path.rglob("*.msg")) + list(base_path.rglob("*.eml"))
        else:
            email_files = list(base_path.glob("*.msg")) + list(base_path.glob("*.eml"))

        for email_file in email_files:
            try:
                details = parser.get_email_details(email_file)
                if not details or not details.get("date"):
                    logger.warning(f"Konnte Details für {email_file} nicht laden, überspringe.")
                    continue

                semester = get_semester(details["date"])

                # Ordner und Nachnamen bestimmen
                sender = details.get("from_email", "").lower()
                lastname = "Unknown"
                folder_name = "Inbox"

                is_sent_by_user = any(u_email in sender for u_email in user_emails)

                if is_sent_by_user:
                    folder_name = "SentItems"
                    # Rule: Bevorzuge direkte Empfänger (To) für die Ordnerbenennung, ignoriere CC
                    # Rule: Nimm den ersten "To"-Empfänger, Fallback auf den zweiten
                    to_recipients = details.get("to", [])
                    if to_recipients:
                        recipient_name = to_recipients[0].get("name")
                        recipient_email = to_recipients[0].get("email")
                        if recipient_name and recipient_email:
                            lastname = extract_lastname(f"{recipient_name} <{recipient_email}>")
                        else:
                            lastname = extract_lastname(recipient_name or recipient_email)

                        if (lastname == "Unknown" or not lastname) and len(to_recipients) > 1:
                            r2_name = to_recipients[1].get("name")
                            r2_email = to_recipients[1].get("email")
                            if r2_name and r2_email:
                                lastname = extract_lastname(f"{r2_name} <{r2_email}>")
                            else:
                                lastname = extract_lastname(r2_name or r2_email)
                    else:
                        recipients = details.get("to", []) + details.get("cc", [])
                        if recipients:
                            lastname = extract_lastname(recipients[0].get("name") or recipients[0].get("email"))
                        else:
                            lastname = "Unknown"
                else:
                    folder_name = "Inbox"
                    # Rule: Der Ordnername sollte der Nachname des Absenders sein
                    from_name = details.get("from_name")
                    from_email = details.get("from_email")
                    if from_name and from_email:
                        lastname = extract_lastname(f"{from_name} <{from_email}>")
                    else:
                        lastname = extract_lastname(from_name or from_email)

                # Ziel-Pfad bestimmen
                student_dir = find_student_folder(base_path, lastname)
                if not student_dir:
                    student_dir = base_path / semester / lastname

                target_dir = student_dir / folder_name
                target_path = target_dir / email_file.name

                if email_file.resolve() == target_path.resolve():
                    continue

                if dry_run:
                    logger.info(f"[DRY RUN] Würde {email_file} nach {target_path} verschieben")
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)

                # Zugehörige .md und .txt Dateien finden
                parent_dir = email_file.parent
                match = re.match(r"(\d{8}_\d{6})", email_file.name)
                files_to_move = [email_file]
                if match:
                    prefix = match.group(1)
                    for extra_file in parent_dir.glob(f"{prefix}*"):
                        if extra_file != email_file and extra_file.suffix in [".md", ".txt"]:
                            files_to_move.append(extra_file)

                for f in files_to_move:
                    dest = target_dir / f.name
                    if dest.exists() and dest.resolve() != f.resolve():
                        logger.warning(f"Ziel {dest} existiert bereits, überspringe Verschieben von {f}.")
                        continue
                    if dest.resolve() != f.resolve():
                        if dry_run:
                            if f != email_file:
                                logger.info(f"[DRY RUN] Würde zugehörige Datei {f} nach {target_dir / f.name} verschieben")
                        else:
                            logger.info(f"Verschiebe {f} nach {dest}")
                            shutil.move(str(f), str(dest))

            except Exception as e:
                logger.error(f"Fehler beim Verarbeiten von {email_file}: {e}")
                continue

        if not dry_run:
            # Leere Verzeichnisse aufräumen
            for root, dirs, files in walk_bottom_up(base_path):
                curr_path = Path(root)
                if curr_path == base_path:
                    continue
                if not any(curr_path.iterdir()):
                    logger.info(f"Entferne leeres Verzeichnis {curr_path}")
                    curr_path.rmdir()

def walk_bottom_up(path: Path) -> Iterator[Tuple[str, List[str], List[str]]]:
    """Reziproke Iteration über Ordner von unten nach oben.

    Args:
        path (Path): Das Startverzeichnis.

    Yields:
        Root, Verzeichnisse und Dateien (wie os.walk).
    """
    import os
    for root, dirs, files in os.walk(path, topdown=False):
        yield root, dirs, files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="E-Mail-Ordnerstruktur korrigieren.")
    parser.add_argument("--config", default="config/classifier_paths.yaml", help="Pfad zu classifier_paths.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Nur Fehler anzeigen, nichts verschieben.")
    parser.add_argument("--verify", action="store_true", help="Alle E-Mails in allen Unterordnern prüfen.")
    args = parser.parse_args()
    fix_folders(Path(args.config), dry_run=args.dry_run, full_verify=args.verify)
