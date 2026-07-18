"""Script to extract generalizable FAQ from email datasets using local LLM."""

import argparse
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml

from mcp_university.config import get_config
from mcp_university.parser.mail_parser import MailParser
from mcp_university.utils.llm_client_wrapper import LLMClientWrapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Loads a YAML file safely.

    Args:
        file_path (Path): Path to the YAML file.

    Returns:
        Dict[str, Any]: The contents of the YAML file, or an empty dict on error.
    """
    if not file_path.exists():
        logger.error(f"Configuration file {file_path} not found.")
        return {}
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            return yaml.safe_load(file) or {}
        except yaml.YAMLError as error:
            logger.error(f"Error loading {file_path}: {error}")
            return {}


def load_memory_paths(memory_config_path: Path, paths_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Loads the config from classifier_memory_paths.yaml or creates a default one.

    Args:
        memory_config_path (Path): Path to classifier_memory_paths.yaml.
        paths_cfg (Dict[str, Any]): The standard class path configuration.

    Returns:
        Dict[str, Any]: The configuration data for memory paths.
    """
    if memory_config_path.exists():
        with open(memory_config_path, "r", encoding="utf-8") as file:
            try:
                config_data = yaml.safe_load(file) or {}
                if "class_paths" in config_data:
                    return config_data
            except Exception as error:
                logger.error(f"Error loading {memory_config_path}: {error}")

    # Generate fallback/default
    logger.info(f"Creating default memory paths configuration under {memory_config_path}...")
    class_paths = paths_cfg.get("class_paths", {})
    memory_paths = {}
    for class_name, path_str in class_paths.items():
        memory_paths[class_name] = f"{path_str}/Memory"

    config_data = {"class_paths": memory_paths}
    memory_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(memory_config_path, "w", encoding="utf-8") as file:
        yaml.dump(config_data, file, default_flow_style=False)

    return config_data


def collect_emails(class_name: str, paths_cfg: Dict[str, Any], folders_cfg: Dict[str, Any]) -> List[Path]:
    """Recursively searches for emails (.msg, .eml) for the given class name.

    Args:
        class_name (str): The name of the email class.
        paths_cfg (Dict[str, Any]): Config from classifier_paths.yaml.
        folders_cfg (Dict[str, Any]): Config from train_test_folders.yaml.

    Returns:
        List[Path]: List of found email file paths.
    """
    email_paths = []
    seen_resolves = set()

    # 1. From classifier_paths.yaml
    class_paths = paths_cfg.get("class_paths", {})
    if class_name in class_paths:
        base_path = Path(class_paths[class_name])
        if base_path.exists():
            for ext in ["*.msg", "*.eml"]:
                for file_path in base_path.rglob(ext):
                    resolved_path = file_path.resolve()
                    if resolved_path not in seen_resolves:
                        email_paths.append(file_path)
                        seen_resolves.add(resolved_path)

    # 2. From train_test_folders.yaml (Train/Test subfolders)
    train_base = folders_cfg.get("train_path")
    test_base = folders_cfg.get("test_path")

    for dataset_base_str in [train_base, test_base]:
        if dataset_base_str:
            dataset_base = Path(dataset_base_str)
            class_dir = dataset_base / class_name
            if class_dir.exists():
                for ext in ["*.msg", "*.eml"]:
                    for file_path in class_dir.rglob(ext):
                        resolved_path = file_path.resolve()
                        if resolved_path not in seen_resolves:
                            email_paths.append(file_path)
                            seen_resolves.add(resolved_path)

    return email_paths


def parse_llm_response(response: str) -> Optional[Tuple[str, str]]:
    """Parses LLM response to extract suitable question and answer.

    Args:
        response (str): The raw response from LLM.

    Returns:
        Optional[Tuple[str, str]]: Tuple of (question, answer) if suitable, else None.
    """
    if not response:
        return None

    lines = [line.strip() for line in response.splitlines() if line.strip()]
    suitable = False
    question = ""
    answer = ""

    for line in lines:
        if line.upper().startswith("GEEIGNET:"):
            val = line.split(":", 1)[1].strip().upper()
            if "JA" in val:
                suitable = True
        elif line.upper().startswith("FRAGE:"):
            question = line.split(":", 1)[1].strip()
        elif line.upper().startswith("ANTWORT:"):
            answer = line.split(":", 1)[1].strip()

    # Fallback parsing with regex
    if not suitable:
        match_suitable = re.search(r"GEEIGNET:\s*(JA|NEIN)", response, re.IGNORECASE)
        if match_suitable and match_suitable.group(1).upper() == "JA":
            suitable = True

    if suitable:
        if not question:
            match_question = re.search(r"FRAGE:\s*(.*?)(?=\s*ANTWORT:|$)", response, re.IGNORECASE | re.DOTALL)
            if match_question:
                question = match_question.group(1).strip()
        if not answer:
            match_answer = re.search(r"ANTWORT:\s*(.*?)(?=\s*FRAGE:|\s*GEEIGNET:|$)", response, re.IGNORECASE | re.DOTALL)
            if match_answer:
                answer = match_answer.group(1).strip()

        if question and answer and question.lower() != "keine" and answer.lower() != "keine":
            return question, answer

    return None


def extract_existing_questions(faq_path: Path) -> List[str]:
    """Extracts existing questions from an FAQ.md file.

    Args:
        faq_path (Path): Path to FAQ.md.

    Returns:
        List[str]: List of normalized existing questions.
    """
    if not faq_path.exists():
        return []

    questions = []
    try:
        content = faq_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("###"):
                question_text = line.replace("###", "").strip()
                question_text = re.sub(r"^\d+\.\s*", "", question_text)
                if question_text:
                    questions.append(question_text.lower().strip())
    except Exception as error:
        logger.error(f"Error reading existing FAQ: {error}")
    return questions


def save_faq(faq_path: Path, new_qa_pairs: List[Tuple[str, str]], class_name: str) -> None:
    """Saves or updates FAQ pairs in FAQ.md.

    Args:
        faq_path (Path): The destination path for FAQ.md.
        new_qa_pairs (List[Tuple[str, str]]): List of new (question, answer) tuples.
        class_name (str): The name of the email class.

    Returns:
        None
    """
    existing_pairs = []

    if faq_path.exists():
        try:
            content = faq_path.read_text(encoding="utf-8")
            sections = content.split("###")
            for section in sections[1:]:
                lines = [line.strip() for line in section.splitlines() if line.strip()]
                if not lines:
                    continue
                q_line = lines[0]
                q_text = re.sub(r"^\d+\.\s*", "", q_line).strip()

                a_text_lines = []
                found_answer_header = False
                for line in lines[1:]:
                    if line.startswith("**Antwort:**") or line.startswith("Antwort:"):
                        found_answer_header = True
                        header_val = re.sub(r"^\*\*Antwort:\*\*\s*", "", line)
                        header_val = re.sub(r"^Antwort:\s*", "", header_val).strip()
                        if header_val:
                            a_text_lines.append(header_val)
                        continue
                    if found_answer_header:
                        if line == "---" or line.startswith("###"):
                            break
                        a_text_lines.append(line)

                a_text = "\n".join(a_text_lines).strip()
                if q_text and a_text:
                    existing_pairs.append((q_text, a_text))
        except Exception as error:
            logger.error(f"Error parsing existing FAQ pairs: {error}")

    # Merge while keeping duplicates out
    all_pairs = list(existing_pairs)
    existing_questions_normalized = [q.lower().strip().rstrip("?.!") for q, _ in existing_pairs]

    for q, a in new_qa_pairs:
        norm_q = q.lower().strip().rstrip("?.!")
        if norm_q not in existing_questions_normalized:
            all_pairs.append((q, a))
            existing_questions_normalized.append(norm_q)

    faq_path.parent.mkdir(parents=True, exist_ok=True)
    with open(faq_path, "w", encoding="utf-8") as file:
        file.write(f"# FAQ - {class_name}\n\n")
        file.write("Dieses Dokument enthält eine Liste von allgemeingültigen Fragen und Antworten, ")
        file.write(f"die aus dem E-Mail-Schriftverkehr der Klasse `{class_name}` extrahiert wurden.\n\n")
        file.write("## Fragen & Antworten\n\n")

        for index, (question, answer) in enumerate(all_pairs, 1):
            file.write(f"### {index}. {question}\n")
            file.write(f"**Antwort:**\n{answer}\n\n")
            if index < len(all_pairs):
                file.write("---\n\n")

    logger.info(f"FAQ successfully saved to {faq_path}. Total pairs: {len(all_pairs)}")


def main() -> None:
    """Main entry point for FAQ extraction script."""
    parser = argparse.ArgumentParser(description="Extract generalizable FAQ from email datasets.")
    parser.add_argument("--class-name", type=str, default="BachelorThesis", help="Name of the email class.")
    parser.add_argument("-n", type=int, default=10, help="Maximum number of emails to process (default: 10).")
    parser.add_argument("--paths-config", type=str, default="config/classifier_paths.yaml", help="Path to classifier_paths.yaml.")
    parser.add_argument("--folders-config", type=str, default="config/train_test_folders.yaml", help="Path to train_test_folders.yaml.")
    parser.add_argument("--memory-config", type=str, default="config/classifier_memory_paths.yaml", help="Path to classifier_memory_paths.yaml.")
    parser.add_argument("--user-config", type=str, default="config/user.yaml", help="Path to user.yaml.")

    args = parser.parse_args()

    # Load configurations
    paths_cfg = load_yaml(Path(args.paths_config))
    folders_cfg = load_yaml(Path(args.folders_config))
    user_cfg = load_yaml(Path(args.user_config))
    memory_cfg = load_memory_paths(Path(args.memory_config), paths_cfg)

    user_name = user_cfg.get("name", "Daniel Gaida")
    logger.info(f"Using Tool-User: {user_name}")

    # Determine class target folder in memory
    memory_paths = memory_cfg.get("class_paths", {})
    if args.class_name not in memory_paths:
        logger.error(f"Class '{args.class_name}' not defined in memory configuration.")
        return

    memory_folder = Path(memory_paths[args.class_name])
    faq_path = memory_folder / "FAQ.md"

    # Collect emails
    emails = collect_emails(args.class_name, paths_cfg, folders_cfg)
    logger.info(f"Found {len(emails)} emails for class '{args.class_name}'.")

    if not emails:
        logger.warning(f"No emails to process for class '{args.class_name}'.")
        return

    # Process up to N emails
    emails_to_process = emails[:args.n]
    logger.info(f"Processing up to {len(emails_to_process)} emails...")

    # Initialize components
    global_config = get_config()
    llm_client = LLMClientWrapper(model=global_config.llm.model, base_url=global_config.llm.base_url)
    mail_parser = MailParser()

    new_qa_pairs = []

    for index, email_path in enumerate(emails_to_process, 1):
        logger.info(f"Processing email {index}/{len(emails_to_process)}: {email_path.name}")
        try:
            content = mail_parser.parse(email_path)
            if not content:
                logger.warning(f"Could not parse email {email_path.name}. Skipping.")
                continue

            system_prompt = (
                "Du bist ein intelligenter Assistent für Universitäts-Wissensmanagement. "
                "Deine Aufgabe ist es, E-Mail-Inhalte zu analysieren und ein Frage-Antwort-Paar "
                "zu extrahieren, falls die E-Mail eine allgemeingültige Frage an den Tool-Nutzer "
                "und die entsprechende Antwort des Tool-Nutzers enthält."
            )

            user_prompt = f"""Analysiere die folgende E-Mail. Der Tool-Nutzer ist {user_name}.

Prüfe, ob:
1. In der E-Mail eine allgemeingültige, themenspezifische Frage an {user_name} gestellt wird.
   - Allgemeingültige Fragen betreffen Richtlinien, Prozesse, Anforderungen, Fristen, Vorlagen oder allgemeine fachliche Themen (z. B. Anmeldung von Arbeiten, Formatierungsvorgaben).
   - NICHT allgemeingültig sind Fragen zu individuellen Terminen, Treffen, Noten, Krankmeldungen, persönlichen Absprachen oder Korrekturen an konkreten Arbeiten eines einzelnen Studierenden.
2. Die E-Mail auch die Antwort von {user_name} auf genau diese Frage enthält.

Antworte im folgenden Format:
GEEIGNET: [JA oder NEIN]
FRAGE: [Die verallgemeinerte Frage auf Deutsch, falls geeignet]
ANTWORT: [Die verallgemeinerte Antwort auf Deutsch, falls geeignet]

WICHTIG: Antworte AUSSCHLIESSLICH in diesem Format. Wenn das Kriterium nicht erfüllt ist, setze GEEIGNET auf NEIN und lasse FRAGE und ANTWORT leer oder schreibe 'Keine'.

E-MAIL INHALT:
{content[:8000]}
"""
            messages = [{"role": "user", "content": user_prompt}]
            response_data = llm_client.chat(messages=messages, system_prompt=system_prompt)
            response = response_data.get("message", {}).get("content", "")

            parsed = parse_llm_response(response)
            if parsed:
                question, answer = parsed
                logger.info(f"Extracted generalizable FAQ pair:\nQ: {question}\nA: {answer}")
                new_qa_pairs.append((question, answer))
            else:
                logger.info(f"Email {email_path.name} is not suitable or has no generalizable Q&A.")

        except Exception as error:
            logger.error(f"Error processing email {email_path.name}: {error}")

    if new_qa_pairs:
        logger.info(f"Saving {len(new_qa_pairs)} new FAQ pairs to {faq_path}...")
        save_faq(faq_path, new_qa_pairs, args.class_name)
    else:
        logger.warning("No new suitable FAQ pairs extracted.")


if __name__ == "__main__":
    main()
