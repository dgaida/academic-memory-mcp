"""Skript zur Zusammenfassung von E-Mail-Klassen für Data Augmentation."""

import logging
from pathlib import Path
from mcp_university.utils.llm_client_wrapper import LLMClientWrapper
from mcp_university.parser.mail_parser import MailParser
from mcp_university.config import get_config

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Analysiert Trainingsordner und erstellt LLM-Zusammenfassungen für kleine Klassen."""
    llm = LLMClientWrapper()
    parser = MailParser()

    train_path = Path("data/classifier/train")

    if not train_path.exists():
        logger.error(f"Trainingspfad {train_path} existiert nicht.")
        return

    for class_dir in train_path.iterdir():
        if not class_dir.is_dir():
            continue

        class_name = class_dir.name
        logger.info(f"Verarbeite Klasse: {class_name}")

        inbox_mails = list((class_dir / "Inbox").glob("*.msg"))
        sent_mails = list((class_dir / "SentItems").glob("*.msg"))
        total_count = len(inbox_mails) + len(sent_mails)

        logger.info(f"  Emails: {total_count} (Inbox: {len(inbox_mails)}, SentItems: {len(sent_mails)})")

        if total_count <= 50:
            logger.info(f"  Erstelle Zusammenfassung für Klasse '{class_name}' (Data Augmentation)...")

            all_texts = []
            for mail_path in (inbox_mails + sent_mails)[:20]:
                text = parser.parse(mail_path)
                if not text:
                    try:
                        with open(mail_path, "r", encoding="utf-8") as f:
                            text = f.read()
                    except Exception:
                        text = "Konnte Mail nicht lesen."
                all_texts.append(text)

            context = "\n---\n".join(all_texts)

            prompt = f"""
Du bist ein Experte für Datenanalyse und NLP. Deine Aufgabe ist es, eine detaillierte Zusammenfassung der folgenden E-Mails aus der Klasse '{class_name}' zu erstellen.
Diese Zusammenfassung wird später genutzt, um künstliche Trainingsdaten (Data Augmentation) für diese Klasse zu erzeugen.

Achte bei der Zusammenfassung besonders auf:
1. Themen: Worüber wird typischerweise in diesen E-Mails geschrieben?
2. Schreibstil: Wie sind die E-Mails verfasst?
3. Rollen: Wer schreibt an wen?

Hier sind die Beispiel-E-Mails:
{context}

Erstelle die Zusammenfassung auf Deutsch.
"""

            try:
                response = llm.chat([{"role": "user", "content": prompt}])
                summary = response.get("message", {}).get("content", "Fehler bei der Zusammenfassung.")
            except Exception as e:
                logger.warning(f"LLM Call fehlgeschlagen: {e}. Nutze Mock-Zusammenfassung.")
                summary = f"Mock-Zusammenfassung für {class_name}:\n- Themen: Prüfungsanmeldung, Projektfragen.\n- Stil: Formell bis halb-formell.\n- Rollen: Student an Professor."

            summary_path = class_dir / "augmentation_summary.md"
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)

            logger.info(f"  Zusammenfassung gespeichert unter: {summary_path}")
        else:
            logger.info(f"  Klasse '{class_name}' hat genug Daten (> 50). Keine Augmentation nötig.")

if __name__ == "__main__":
    main()
