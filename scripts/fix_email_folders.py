"""Modul zum Korrigieren der E-Mail-Ordnerstruktur."""
import yaml
import logging
import shutil
import re
from pathlib import Path
from mcp_university.classifier.sort_emails import extract_lastname, get_semester
from mcp_university.config import get_config
from mcp_university.parser.mail_parser import MailParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_folders(config_path: Path) -> None:
    """Migrates emails to the standard structure: Semester/Lastname/Inbox|SentItems/."""
    if not config_path.exists():
        logger.error(f"Config file {config_path} not found.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if "class_paths" in config:
        config = config["class_paths"]

    parser = MailParser()
    user_email = get_config().user.email

    for email_class, base_path_str in config.items():
        base_path = Path(base_path_str)
        if not base_path.exists():
            continue

        logger.info(f"Processing class {email_class} in {base_path}")

        # Find all email files recursively in the base_path
        email_files = list(base_path.rglob("*.msg")) + list(base_path.rglob("*.eml"))

        for email_file in email_files:
            try:
                details = parser.get_email_details(email_file)
                if not details or not details.get("date"):
                    logger.warning(f"Could not get details for {email_file}, skipping.")
                    continue

                semester = get_semester(details["date"])

                # Determine folder (Inbox or SentItems) and lastname
                # Logic from sort_emails.py
                sender = details.get("from_email", "").lower()
                lastname = "Unknown"
                folder_name = "Inbox"

                if user_email in sender:
                    folder_name = "SentItems"
                    # Try to find student in recipients
                    recipients = details.get("to", []) + details.get("cc", [])
                    found_student = False
                    for rec in recipients:
                        rec_email = rec.get("email", "").lower()
                        if "@smail.th-koeln.de" in rec_email or "@smail.fh-koeln.de" in rec_email:
                            lastname = extract_lastname(rec.get("name") or rec.get("email"))
                            found_student = True
                            break
                    if not found_student and recipients:
                        lastname = extract_lastname(recipients[0].get("name") or recipients[0].get("email"))
                elif "@smail.th-koeln.de" in sender or "@smail.fh-koeln.de" in sender:
                    folder_name = "Inbox"
                    lastname = extract_lastname(details.get("from_name") or details.get("from_email"))
                else:
                    # Fallback
                    recipients = details.get("to", []) + details.get("cc", [])
                    found_student = False
                    for rec in recipients:
                        rec_email = rec.get("email", "").lower()
                        if "@smail.th-koeln.de" in rec_email or "@smail.fh-koeln.de" in rec_email:
                            folder_name = "SentItems"
                            lastname = extract_lastname(rec.get("name") or rec.get("email"))
                            found_student = True
                            break
                    if not found_student:
                        folder_name = "Inbox"
                        lastname = extract_lastname(details.get("from_name") or details.get("from_email"))

                target_dir = base_path / semester / lastname / folder_name
                target_path = target_dir / email_file.name

                if email_file.resolve() == target_path.resolve():
                    continue

                target_dir.mkdir(parents=True, exist_ok=True)

                # Find associated .md and .txt files in the SAME directory as the email
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
                        logger.warning(f"Destination {dest} already exists, skipping move of {f}.")
                        continue
                    if dest.resolve() != f.resolve():
                        logger.info(f"Moving {f} to {dest}")
                        shutil.move(str(f), str(dest))

            except Exception as e:
                logger.error(f"Error processing {email_file}: {e}")
                continue

        # Cleanup: Remove empty directories (bottom-up)
        for root, dirs, files in walk_bottom_up(base_path):
            curr_path = Path(root)
            if curr_path == base_path:
                continue
            if not any(curr_path.iterdir()):
                logger.info(f"Removing empty directory {curr_path}")
                curr_path.rmdir()

def walk_bottom_up(path: Path):
    """Reziproke Iteration über Ordner von unten nach oben."""
    import os
    for root, dirs, files in os.walk(path, topdown=False):
        yield root, dirs, files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix email folder structure.")
    parser.add_argument("--config", default="config/classifier_paths.yaml", help="Path to classifier_paths.yaml")
    args = parser.parse_args()
    fix_folders(Path(args.config))
