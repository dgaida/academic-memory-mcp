import yaml
import logging
import shutil
import re
from pathlib import Path
from typing import Dict  # type: ignore
from mcp_university.classifier.sort_emails import extract_lastname

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_folders(config_path: Path) -> None:
    """Migrates emails from root Inbox/SentItems to student subfolders."""
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

            for folder_name in ["Inbox", "SentItems"]:
                root_folder = semester_dir / folder_name
                if not root_folder.exists():
                    continue

                logger.info(f"Checking root folder {root_folder}")

                # Find all email files in the root Inbox/SentItems
                email_files = list(root_folder.glob("*.msg")) + list(root_folder.glob("*.eml"))

                for email_file in email_files:
                    lastname = "Unknown"
                    import extract_msg
                    try:
                        if email_file.suffix.lower() == ".msg":
                            with extract_msg.openMsg(str(email_file)) as msg:
                                if folder_name == "Inbox":
                                    lastname = extract_lastname(msg.sender)
                                else:
                                    # For SentItems, look at recipients
                                    if msg.recipients:
                                        lastname = extract_lastname(msg.recipients[0].name or msg.recipients[0].email)
                        else:
                            # Minimal .eml parsing for lastname
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
                    target_dir.mkdir(parents=True, exist_ok=True)

                    # Find associated .md and .txt files
                    # Assuming naming convention like 20240520_123456_subject.msg
                    match = re.match(r"(\d{8}_\d{6})", email_file.name)
                    files_to_move = [email_file]
                    if match:
                        prefix = match.group(1)
                        for extra_file in root_folder.glob(f"{prefix}*"):
                            if extra_file != email_file and extra_file.suffix in [".md", ".txt"]:
                                files_to_move.append(extra_file)

                    for f in files_to_move:
                        dest = target_dir / f.name
                        logger.info(f"Moving {f} to {dest}")
                        if dest.exists():
                            logger.warning(f"Destination {dest} already exists, skipping.")
                            continue
                        shutil.move(str(f), str(dest))

                # Check for empty folder and remove
                if root_folder.exists() and not any(root_folder.iterdir()):
                    logger.info(f"Removing empty root folder {root_folder}")
                    root_folder.rmdir()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix email folder structure.")
    parser.add_argument("--config", default="config/classifier_paths.yaml", help="Path to classifier_paths.yaml")
    args = parser.parse_args()
    fix_folders(Path(args.config))
