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

## 2. Generelle Erkennung von Terminanfragen & Slot-Filterung (Wochentage & Ort/Präsenz)

Wenn ein Studierender nach einem Termin fragt (oder als Alternative nach einem Terminbelegungs-Konflikt):

### A. Wochentags-Filterung (KRITISCH)
- **Extrahiere die im E-Mail-Text genannten Wochentage:** Falls die E-Mail spezifische Wochentage verlangt (z.B. "haben Sie ggf. am Mittwoch oder Freitag Zeit..."), filtere aus den über `get_appointment_slots` geladenen freien Slots **ausschließlich** die Slots heraus und schlage nur diese vor, die auf diese Wochentage fallen (im Beispiel: nur Mittwoche und Freitage).
- Vorgeschlagene Slots außerhalb der angefragten Wochentage dürfen in diesem Fall NICHT in der E-Mail angeboten werden.

### B. Automatisierte Standort- & Präsenzanalyse (Vor Ort vs. Online)
- **Automatische Standortbestimmung via Kalender (`data/appointments.md`):**
  1. Rufe das Tool `read_file` mit `data/appointments.md` auf.
  2. Untersuche die Spalte "Ort" für jeden Tag. Steht dort als Ort z.B. `"TH Köln (Campus Gummersbach)"`, `"TH Köln"`, `"Gummersbach"` oder `"Campus"`, so bist du an diesem Tag **vor Ort (auf dem Campus)**.
  3. Tage, an denen an keinem Termin ein Ort mit diesen Campus-Schlüsselwörtern eingetragen ist, sind **Home-Office- bzw. Online-Tage**.
- **Auswahl der Vorschläge nach Art des Treffens:**
  - **Termin vor Ort / Kolloquium:** Wird nach einem Termin vor Ort gefragt (z.B. ein Kolloquium oder ausdrücklich ein Präsenztreffen), schlage **bevorzugt / ausschließlich** freie Slots an Tagen vor, an denen du **vor Ort** bist.
  - **Online-Termin / Standard-Termin:** Wird nach einem Online-Termin gefragt (oder einem allgemeinen Meeting ohne Prärenzzwang), schlage **bevorzugt** freie Slots an Tagen vor, an denen du **NICHT vor Ort** bist. Ziel ist es, Präsenztage nicht mit unnötigen Online-Terminen zu überladen.

### C. Ablauf
1. Rufe das Tool `read_file` mit `data/appointments.md` auf (zur Standort- & Präsenzanalyse sowie Terminprüfung).
2. Rufe das Tool `get_appointment_slots` auf, um freie Slots aus `data/free_slots.md` zu laden.
3. Wende die Filterung nach Wochentagen (Falls in der Mail eingeschränkt) und nach Präsenz/Online-Eignung an.
4. Liste die herausgefilterten Slots in der Antwortmail übersichtlich als Optionen auf.

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
