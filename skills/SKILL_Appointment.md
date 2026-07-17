# SKILL: Terminverwaltung (Terminanfragen und -bestätigungen)

Dieser Skill wird verwendet, um Terminanfragen von Studierenden zu bearbeiten oder Terminbestätigungen in den Kalender einzutragen.

## 1. Erkennung von Terminanfragen
Wenn ein Studierender nach einem Termin fragt (z.B. für eine Besprechung, Sprechstunde, Thesis-Thema):  
1. Rufe das Tool `get_appointment_slots` auf, um die aktuell verfügbaren freien Slots zu erhalten.  
2. Liste diese Slots in der Antwortmail als Optionen für einen Zoom-Termin auf.  
3. Formatiere die Liste übersichtlich.  

## 2. Erkennung von Terminbestätigungen (WICHTIG & KRITISCH)
Wenn ein Studierender einen konkreten Termin bestätigt (z.B. "Dienstag 14:00 passt bei mir" oder "Ich nehme den Termin am Montag um 14:00 Uhr"):
Du musst ein explizites **Chain-of-Thought Prompting (Schritt-für-Schritt-Denken)** anwenden, um den Termin präzise zu ermitteln. Verwende dabei folgendes strukturierte Vorgehen, bevor du ein Tool aufrufst oder antwortest:

### Schritt-für-Schritt-Denkprozess (Chain of Thought / CoT):
1. **Referenzzeitpunkt bestimmen:** Lies das heutige Datum und die aktuelle Uhrzeit aus dem Feld "HEUTE IST:" (z.B. Freitag, 17.07.2026).
2. **Gesendete Mail-Header identifizieren:** Finde alle Datumsangaben im E-Mail-Header der zitierten Konversation (z.B. "On Thu, 16 Jul 2026, 16:12...").
   - **WARNUNG:** Dieses Sendedatum liegt typischerweise in der Vergangenheit (z.B. 16.07.2026) und ist **NIEMALS** das Datum des neuen Termins! Ignoriere dieses Datum komplett für die Terminbuchung.
3. **Angebotene Terminslots auflisten:** Scanne die E-Mail-Historie nach einer Liste von Terminvorschlägen, die zuvor an den Studierenden gesendet wurden (z.B. "Terminmöglichkeiten per Zoom: • Mo, 2026-07-20 13:30-14:00 ... • Di, 2026-07-21 14:00-14:30").
4. **Bestätigung des Studierenden analysieren:** Extrahiere den vom Studierenden genannten Wochentag, das Datum und/oder die Uhrzeit (z.B. "Dienstag 14:00").
5. **Abgleich durchführen:** Gleiche die Bestätigung des Studierenden ("Dienstag 14:00") mit der Liste der angebotenen Slots ab.
   - Welches Datum gehört zu dem vom Studierenden gewählten Wochentag und der Uhrzeit? (z.B. "Dienstag" in Kombination mit "14:00" passt exakt zum angebotenen Slot "Di, 2026-07-21 14:00-14:30").
   - Das korrekte Datum ist also der **2026-07-21** (nicht der 16.07.2026 aus dem Header!).
6. **Zukunfts- & Plausibilitätsprüfung:** Überprüfe, ob der ermittelte Termin (21.07.2026) in der Zukunft bezüglich des Referenzzeitpunkts (17.07.2026) liegt.
   - Ein Termin in der Vergangenheit (z.B. 16.07.2026) darf **NIEMALS** gebucht werden!

### JSON-Repräsentation deines Denkprozesses:
Bevor du das Tool aufrufst, erstelle in deinem Gedanken/Text diese JSON-Struktur:
```json
{
  "heutiges_datum": "2026-07-17",
  "mail_header_datum": "2026-07-16",
  "angebotene_slots": [
    "2026-07-20 13:30-14:00",
    "2026-07-20 14:00-14:30",
    "2026-07-20 14:30-15:00",
    "2026-07-21 14:00-14:30"
  ],
  "student_bestaetigung": "Dienstag 14:00",
  "abgeglichenes_datum": "2026-07-21",
  "abgeglichene_uhrzeit": "14:00",
  "termin_ist_in_zukunft": true,
  "start_time": "2026-07-21 14:00",
  "end_time": "2026-07-21 14:30"
}
```

### 3. DAUER & TOOL-AUFRUF
- **DAUER:**
  - Die Standarddauer eines Termins beträgt **30 Minuten**.
  - **AUSNAHME:** Termine für ein **Kolloquium** dauern IMMER **60 Minuten**.
- **PFLICHT:** Rufe das Tool `manage_calendar_appointment` auf. Dies ist der wichtigste Schritt!
  - `start_time`: Format 'YYYY-MM-DD HH:MM' (Zeitzone: Europe/Berlin). Achte auf das korrekte Jahr!
  - `end_time`: Format 'YYYY-MM-DD HH:MM'. Muss bei Kolloquien 60 Min nach start_time liegen, sonst 30 Min.
  - `subject`: Generiere einen passenden Betreff (z.B. "Kolloquium Max Mustermann" oder "Besprechung [Name] - [Thema]").
  - `student_email`: Die E-Mail-Adresse des Studierenden (aus dem Kontext).
  - `original_mail_date`: Das Datum der E-Mail des Studierenden im Format DD.MM.YY.
- **UPDATE KOLLOQUIUM-KONFIGURATION:** Falls der Termin ein **Kolloquium** ist:
  - Rufe zusätzlich das Tool `update_colloquium_config` auf.
  - `student_email`: Die E-Mail-Adresse des Studierenden.
  - `date`: Das bestätigte Datum (DD.MM.YYYY).
  - `time`: Die bestätigte Uhrzeit (HH:MM).
- **ERST NACH ERFOLGREICHEM TOOL-AUFRUF:** Wenn das Tool `manage_calendar_appointment` eine Nachricht mit "ERFOLG" zurückgibt:
  - Antworte EXAKT mit dem Signalwort: **APPOINTMENT_BOOKED**
  - Behaupte NIEMALS, dass ein Termin gebucht wurde, wenn das Tool nicht aufgerufen wurde oder einen Fehler gemeldet hat.
  - Sende keine weitere E-Mail an den Studierenden (die Einladung erfolgt automatisch über Outlook).
- Wenn das Tool einen Fehler meldet (z.B. Slot belegt oder terminliche Überschneidung):
  - Korrigiere den Tool-Aufruf, falls möglich.
  - Falls der Slot belegt ist, informiere den Studierenden in der Antwortmail darüber und schlage erneut freie Slots vor (siehe Punkt 1).

## 4. Priorität
Dieser Skill hat höchste Priorität. Wenn eine Mail eine Terminanfrage oder -bestätigung enthält, befolge diese Anweisungen. Wenn beides nicht zutrifft, fahre mit dem normalen Prozess (andere Skills/Zusammenfassung) fort.
