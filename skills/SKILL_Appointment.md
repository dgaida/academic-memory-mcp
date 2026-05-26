# SKILL: Terminverwaltung (Terminanfragen und -bestätigungen)

Dieser Skill wird verwendet, um Terminanfragen von Studierenden zu bearbeiten oder Terminbestätigungen in den Kalender einzutragen.

## 1. Erkennung von Terminanfragen
Wenn ein Studierender nach einem Termin fragt (z.B. für eine Besprechung, Sprechstunde, Thesis-Thema):
1. Rufe das Tool `get_appointment_slots` auf, um die aktuell verfügbaren freien Slots zu erhalten.
2. Liste diese Slots in der Antwortmail als Optionen für einen Zoom-Termin auf.
3. Formatiere die Liste übersichtlich.

## 2. Erkennung von Terminbestätigungen
Wenn ein Studierender einen konkreten Termin bestätigt (z.B. "Ich nehme den Termin am Montag um 14:00 Uhr"):
1. Extrahiere das Datum und die Uhrzeit aus der Mail.
2. Berechne die Endzeit (Standarddauer: 30 Minuten, sofern nicht anders angegeben).
3. **PFLICHT:** Rufe das Tool `manage_calendar_appointment` auf. Dies ist der wichtigste Schritt!
   - `start_time`: Format 'YYYY-MM-DD HH:MM'
   - `end_time`: Format 'YYYY-MM-DD HH:MM'
   - `subject`: Generiere einen passenden Betreff (z.B. "Besprechung [Name des Studierenden] - [Thema]").
   - `student_email`: Die E-Mail-Adresse des Studierenden (aus dem Kontext).
4. **ERST NACH ERFOLGREICHEM TOOL-AUFRUF:** Wenn das Tool eine Nachricht mit "ERFOLG" zurückgibt:
   - Antworte EXAKT mit dem Signalwort: **APPOINTMENT_BOOKED**
   - Behaupte NIEMALS, dass ein Termin gebucht wurde, wenn das Tool nicht aufgerufen wurde oder einen Fehler gemeldet hat.
   - Sende keine weitere E-Mail an den Studierenden (die Einladung erfolgt automatisch über Outlook).
5. Wenn das Tool einen Fehler meldet (z.B. Slot belegt):
   - Informiere den Studierenden in der Antwortmail darüber und schlage erneut freie Slots vor (siehe Punkt 1).

## 3. Priorität
Dieser Skill hat höchste Priorität. Wenn eine Mail eine Terminanfrage oder -bestätigung enthält, befolge diese Anweisungen. Wenn beides nicht zutrifft, fahre mit dem normalen Prozess (andere Skills/Zusammenfassung) fort.
