import yaml
import logging
import shutil
import re
from pathlib import Path
from mcp_university.classifier.sort_emails import extract_lastname

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

    for email_class, base_path_str in config.items():
        base_path = Path(base_path_str)
        if not base_path.exists():
            continue

        logger.info(f"Processing class {email_class} in {base_path}")

        # Iterate over semester folders
        for semester_dir in base_path.iterdir():
            if not semester_dir.is_dir():
                continue

            logger.info(f"Processing semester {semester_dir.name}")

            # Find all email files recursively in the semester folder
            email_files = list(semester_dir.rglob("*.msg")) + list(semester_dir.rglob("*.eml"))

            for email_file in email_files:
                # Determine current folder (Inbox or SentItems)
                # Look for "Inbox" or "SentItems" in the path relative to semester_dir
                rel_path = email_file.relative_to(semester_dir)
                folder_name = "Inbox" # Default
                for part in rel_path.parts:
                    if part in ["Inbox", "SentItems"]:
                        folder_name = part
                        break

                lastname = "Unknown"
                import extract_msg
                try:
                    if email_file.suffix.lower() == ".msg":
                        with extract_msg.openMsg(str(email_file)) as msg:
                            if folder_name == "Inbox":
                                lastname = extract_lastname(msg.sender)
                            else:
                                if msg.recipients:
                                    lastname = extract_lastname(msg.recipients[0].name or msg.recipients[0].email)
                    else:
                        import email
                        from email import policy
                        with open(email_file, 'rb') as f:
                            msg = email.message_from_binary_file(f, policy=policy.default)
                            if folder_name == "Inbox":
                                lastname = extract_lastname(msg.get('From', ''))
                            else:
                                lastname = extract_lastname(msg.get('To', ''))
                except Exception as e:
                    logger.error(f"Error parsing {email_file}: {e}")
                    continue

                target_dir = semester_dir / lastname / folder_name
                target_path = target_dir / email_file.name

                if email_file == target_path:
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
                    if dest.exists() and dest != f:
                        logger.warning(f"Destination {dest} already exists, skipping move of {f}.")
                        continue
                    if dest != f:
                        logger.info(f"Moving {f} to {dest}")
                        shutil.move(str(f), str(dest))

        # Cleanup: Remove empty directories (bottom-up)
        for semester_dir in base_path.iterdir():
            if not semester_dir.is_dir():
                continue
            for root, dirs, files in walk_bottom_up(semester_dir):
                curr_path = Path(root)
                # Don't remove the semester_dir itself, but its children if empty
                if curr_path == semester_dir:
                    continue
                if not any(curr_path.iterdir()):
                    logger.info(f"Removing empty directory {curr_path}")
                    curr_path.rmdir()

def walk_bottom_up(path: Path):
    import os
    for root, dirs, files in os.walk(path, topdown=False):
        yield root, dirs, files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix email folder structure.")
    parser.add_argument("--config", default="config/classifier_paths.yaml", help="Path to classifier_paths.yaml")
    args = parser.parse_args()
    fix_folders(Path(args.config))
