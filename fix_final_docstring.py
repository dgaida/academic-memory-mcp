from pathlib import Path

path = Path("mcp_university/classifier/controller.py")
content = path.read_text(encoding="utf-8")

# Docstring of generate_reply
old_docs = """        Args:
            mail_path (Path): Pfad zur E-Mail-Datei.
            summary_content (str): Zusammenfassung des bisherigen Schriftverkehrs.
            skill_path (Path): Pfad zur Skill-Datei.
            conversation_content (str): Inhalt des bisherigen Schriftverkehrs.
            persona_path (Path): Pfad zur Persona-Datei.
            additional_context (str): Zusätzlicher Kontext für das LLM.
            appointment_skill_path (Path): Pfad zur Terminverwaltungs-Skill-Datei.
            sender_name (str): Name des Absenders.
            sender_email (str): E-Mail-Adresse des Absenders.
            action_idx (int): Index der gewählten Aktion.
            email_class (str): E-Mail-Klasse.
            detected_language (str): Die erkannte Sprache der E-Mail.
            honorific (str): Die bevorzugte Anrede ('Du' oder 'Sie')."""

# Wait, let me check the actual current docstring in the file.
