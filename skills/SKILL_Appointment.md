# SKILL: Terminverwaltung (Terminanfragen und -bestätigungen)

Dieser Skill wird verwendet, um Terminanfragen von Studierenden zu bearbeiten oder Terminbestätigungen in den Kalender einzutragen.

## 1. Erkennung von Terminanfragen und Terminbestätigungen (WICHTIG & KRITISCH)

Du musst die empfangene E-Mail stets prüfen, ob ein **Terminvorschlag** oder eine **Zusage** (Terminbestätigung) seitens des Studierenden gemacht wurde (z.B. "Passt es am Dienstag um 14:00 Uhr?" oder "Ich bestätige den Termin am Dienstag um 14:00 Uhr").

Falls ein Terminvorschlag oder eine Zusage vorliegt, befolge zwingend diese intelligenten Prüfschritte:

### Schritt-für-Schritt-Denkprozess (Chain of Thought / CoT):
1. **Referenzzeitpunkt bestimmen:** Lies das heutige Datum und die aktuelle Uhrzeit aus dem Feld "HEUTE IST:" (z.B. Freitag, 17.07.2026).
2. **Gesendete Mail-Header identifizieren:** Finde alle Datumsangaben im E-Mail-Header der zitierten Konversation (z.B. "On Thu, 16 Jul 2026, 16:12...").
   - **WARNUNG:** Dieses Sendedatum liegt typischerweise in der Vergangenheit und ist **NIEMALS** das Datum des neuen Termins! Ignoriere dieses Datum komplett für die Terminbuchung.
3. **Erfassen des Wunschtermins:** Extrahiere den vom Studierenden vorgeschlagenen oder bestätigten Wochentag, das Datum und/oder die Uhrzeit (z.B. "Dienstag 14:00").
4. **Abgleich mit Kalender (Intelligente Prüfung):**
   - Rufe das Tool `read_file` mit dem Pfad `data/appointments.md` auf, um die bestehenden Termine und Blocker zu lesen.
   - Prüfe intelligent, was du zur angefragten Uhrzeit hast:
     - **Kein Termin vorhanden:** Du bist frei!
     - **Ein Blocker speziell für diese Anfrage/diesen Studenten/diesen Termin vorhanden** (z. B. "Blocker", "Blocker Besprechung" oder "Blocker [Studenten-Name]"): Dies zählt als frei bzw. für diesen Termin vorgesehen!
     - **Ein ganz anderer Termin / anderer Blocker vorhanden** (z. B. ein Meeting mit einem anderen Studenten, eine private Verabredung oder ein allgemeiner ganztägiger Blocker, der nicht für diese Besprechung bestimmt ist): Dies steht der Terminanfrage im Wege ("ein ganz anderer Termin, der der Terminanfrage im Wege steht"). Du bist belegt!

5. **Entscheidung & Aktion:**
   - **Falls belegt (Konflikt):**
     - Nutze das Tool `get_appointment_slots` (liest `data/free_slots.md`), um freie Terminslots als Alternativen zu laden.
     - Schlage diese freien Alternativen in deiner E-Mail-Antwort vor und teile dem Studierenden freundlich mit, dass der angefragte Termin leider belegt ist.
   - **Falls frei:**
     - Lege den Termin im Kalender an! Rufe das Tool `manage_calendar_appointment` auf, um den Termin zu buchen und die Empfänger der Mail (den Studierenden) automatisch einzuladen.
     - **UPDATE KOLLOQUIUM-KONFIGURATION:** Falls der Termin ein **Kolloquium** ist, rufe zusätzlich das Tool `update_colloquium_config` auf.
     - **ERST NACH ERFOLGREICHEM TOOL-AUFRUF:** Wenn das Tool `manage_calendar_appointment` eine Nachricht mit "ERFOLG" zurückgibt, antworte EXAKT mit dem Signalwort: **APPOINTMENT_BOOKED** (behauptet dies niemals, wenn das Tool fehlgeschlagen ist).

### JSON-Repräsentation deines Denkprozesses:
Bevor du das Tool aufrufst, erstelle in deinem Gedanken/Text diese JSON-Struktur:
```json
{
  "heutiges_datum": "2026-07-17",
  "mail_header_datum": "2026-07-16",
  "angebotene_slots": [
    "2026-07-20 13:30-14:00",
    "2026-07-21 14:00-14:30"
  ],
  "student_bestaetigung_oder_vorschlag": "Dienstag 14:00",
  "bestehende_termine_zu_der_zeit": "Keine oder nur passender Blocker",
  "abgeglichenes_datum": "2026-07-21",
  "abgeglichene_uhrzeit": "14:00",
  "termin_ist_in_zukunft": true,
  "start_time": "2026-07-21 14:00",
  "end_time": "2026-07-21 14:30"
}
```

## 2. Generelle Erkennung von reinen Terminanfragen (ohne konkrete Vorschläge)
Wenn ein Studierender allgemein nach einem Termin fragt, ohne selbst einen konkreten Termin oder Wochentag vorzuschlagen:
1. Rufe das Tool `get_appointment_slots` auf, um die aktuell verfügbaren freien Slots (aus `data/free_slots.md`) zu erhalten.
2. Liste diese Slots in der Antwortmail übersichtlich als Optionen auf.

## 3. DAUER & TOOL-AUFRUF
- **DAUER:**
  - Die Standarddauer eines Termins beträgt **30 Minuten**.
  - **AUSNAHME:** Termine für ein **Kolloquium** dauern IMMER **60 Minuten**.
- **PROMPT FÜR manage_calendar_appointment:**
  - `start_time`: Format 'YYYY-MM-DD HH:MM' (Zeitzone: Europe/Berlin).
  - `end_time`: Format 'YYYY-MM-DD HH:MM'. Standardmäßig 30 Min später (bei Kolloquien 60 Min).
  - `subject`: Passender Betreff (z.B. "Besprechung [Name]" oder "Kolloquium [Name]").
  - `student_email`: Die E-Mail-Adresse des Studierenden.
  - `original_mail_date`: Das Datum der studentischen Mail im Format DD.MM.YY.

## 4. Priorität
Dieser Skill hat höchste Priorität bei jeglicher E-Mail-Beantwortung. Wenn eine Mail einen Terminvorschlag, eine Zusage oder eine Terminanfrage enthält, befolge diese Anweisungen. Wenn beides nicht zutrifft, antworte mit `NO_APPOINTMENT_RELEVANCE` (oder fahre mit dem normalen Beantwortungsprozess fort).
