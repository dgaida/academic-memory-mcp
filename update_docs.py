import os

def update_file(path, search_text, add_text):
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if add_text in content: return
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.replace(search_text, search_text + add_text))

# German
search_de = "### E-Mail Sortierung (Studenten-Ordner)\nDas leistungsfähigste Skript sortiert E-Mails nicht nur nach Klasse, sondern auch nach Semester und Student (Nachname):"
add_de = """

```bash
python3 process_sorted_emails.py /pfad/zu/daten
```

#### Terminverwaltung (Workflows)
Das Skript erkennt automatisch Terminanfragen und -bestätigungen.
- **Terminbestätigungen:** Erkennt das System eine Bestätigung, wird automatisch ein Kalendertermin in Outlook angelegt (Zeitzone: Europe/Berlin). Standardmäßig beträgt die Dauer **30 Minuten**.
- **Speicherort:** Termine werden als Entwurf im Ordner **"Work in Progress"** oder direkt im Kalender des Kontos `daniel.gaida@th-koeln.de` angelegt.
- **Wichtig:** Auch wenn der Termin in "Work in Progress" nicht sofort sichtbar ist, wird er im Outlook-Kalender angelegt. Dort kann er geöffnet, geprüft und final abgesendet werden.

#### Bedeutung von "ANHANG: JA"
In den Logs oder Ausgaben des Agenten erscheint oft die Zeile `ANHANG: JA`.
- Dies ist ein **Steuerungssignal** für das Skript. Es bedeutet, dass das LLM empfiehlt, eine zusätzliche Informationsdatei (z.B. ein PDF mit PO-Wechsel-Informationen) an den E-Mail-Entwurf anzuhängen.
- Es bedeutet **nicht**, dass dem Kalendereintrag selbst eine Datei angehängt wurde.
"""
update_file('docs/de/usage/index.md', search_de, add_de)

# English
search_en = "### Email Sorting (Student Folders)\nThe most powerful script sorts emails not only by class but also by semester and student (last name):"
add_en = """

```bash
python3 process_sorted_emails.py /path/to/data
```

#### Appointment Management (Workflows)
The script automatically detects appointment requests and confirmations.
- **Appointment Confirmations:** If the system detects a confirmation, an Outlook calendar appointment is automatically created (Timezone: Europe/Berlin). The default duration is **30 minutes**.
- **Storage Location:** Appointments are created as drafts in the **"Work in Progress"** folder or directly in the calendar of the account `daniel.gaida@th-koeln.de`.
- **Important:** Even if the appointment is not immediately visible in "Work in Progress", it is created in the Outlook calendar. There, it can be opened, reviewed, and finally sent.

#### Meaning of "ANHANG: JA" (ATTACHMENT: YES)
The line `ANHANG: JA` often appears in the agent's logs or outputs.
- This is a **control signal** for the script. It means that the LLM recommends attaching an additional information file (e.g., a PDF with PO change information) to the email draft.
- It does **not** mean that a file has been attached to the calendar entry itself.
"""
update_file('docs/en/usage/index.md', search_en, add_en)
