from pathlib import Path

path = Path("packages/email_classifier/src/email_classifier/controller.py")
content = path.read_text(encoding="utf-8")

# 1. Update Step 1 (Appointment) Prompt
content = content.replace(
    '            elif force_colloquium:\n                forced_instr = "\\nERZWUNGENE AKTION: Diese E-Mail bestätigt ein Kolloquium (60 Min). Du MUSST ZWINGEND manage_calendar_appointment aufrufen."',
    '            elif force_colloquium:\n                forced_instr = "\\nERZWUNGENE AKTION: Diese E-Mail bestätigt ein Kolloquium. Du MUSST ZWINGEND manage_calendar_appointment mit is_colloquium=True aufrufen."'
)

content = content.replace(
    '- Wenn eine Terminbestätigung vorliegt: Rufe SOFORT das Tool \'manage_calendar_appointment\' auf. Gib KEINE textuelle Analyse oder Erklärung ab. Antworte EXAKT mit \'APPOINTMENT_BOOKED\' erst NACHDEM das Tool \'ERFOLG\' gemeldet hat.',
    '- Wenn eine Terminbestätigung vorliegt: Rufe SOFORT das Tool \'manage_calendar_appointment\' auf. Falls es ein Kolloquium ist, setze is_colloquium=True. Gib KEINE textuelle Analyse oder Erklärung ab. Antworte EXAKT mit \'APPOINTMENT_BOOKED\' erst NACHDEM das Tool \'ERFOLG\' gemeldet hat.'
)

# 2. Update Step 1.2 (Final Submission) Prompt
content = content.replace(
    '            if force_final_submission:\n                forced_instr = "\\nERZWUNGENE AKTION: Dies ist eine finale Abgabe. Du MUSST ZWINGEND manage_calendar_appointment und save_email_attachments aufrufen."',
    '            if force_final_submission:\n                forced_instr = "\\nERZWUNGENE AKTION: Dies ist eine finale Abgabe. Du MUSST ZWINGEND manage_calendar_appointment, save_email_attachments und create_colloquium_config aufrufen."'
)

content = content.replace(
    '1. Falls es eine finale Abgabe ist: Rufe ZUERST die Tools `manage_calendar_appointment` und `save_email_attachments` auf.',
    '1. Falls es eine finale Abgabe ist: Rufe ZUERST die Tools `manage_calendar_appointment`, `save_email_attachments` und `create_colloquium_config` (mit dem Dateinamen der PDF aus dem Anhang) auf.'
)

path.write_text(content, encoding="utf-8")
