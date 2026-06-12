# SKILL: Finale Abgabe von Arbeiten (Bachelor, Master, Projektarbeiten)

Dieser Skill wird verwendet, um die finale Abgabe von Abschlussarbeiten oder Projektarbeiten zu verarbeiten.

## 1. Erkennung der finalen Abgabe
Prüfe, ob es sich bei der vorliegenden E-Mail um die **finale Abgabe** einer Arbeit handelt.
Anzeichen dafür sind:  
- Wörter wie "Abgabe", "finale Version", "fertige Arbeit", "letzte Version".  
- Erwähnung von "Bachelorarbeit", "Masterarbeit", "Informatikprojekt", "Praxisprojekt".  
- Vorhandensein von Anhängen (typischerweise die Arbeit als PDF).  

## 2. Verarbeitungsschritte bei finaler Abgabe

### Schritt A: Kalendertermin erstellen
Erstelle einen Termin in genau **einer Woche ab heute** (dem Tag, an dem die Mail eingegangen ist oder heute).  
- **Zeitpunkt:** 08:00 Uhr morgens.  
- **Dauer:** 30 Minuten.  
- **Titel:** "[Typ der Arbeit] von [Hr./Fr. Nachname] lesen"  
  - Beispiel: "Bachelorarbeit von Fr. Müller lesen" oder "Masterarbeit von Hr. Schmidt lesen".  
  - Nutze den korrekten Typ (Bachelorarbeit, Masterarbeit, Projektarbeit, etc.).  
- **Inhalt (Body):** Gib den Pfad zur E-Mail an, idealerweise als Link (falls möglich) oder einfach den Pfad.  
- **Tool-Aufruf:** Rufe `manage_calendar_appointment` auf.  
  - `start_time`: YYYY-MM-DD 08:00 (Datum = Heute + 7 Tage).  
  - `end_time`: YYYY-MM-DD 08:30.  
  - `subject`: Siehe oben.  
  - `body`: Pfad zur E-Mail (z.B. "E-Mail Pfad: [Pfad]").  

### Schritt B: Anhänge speichern
Falls die E-Mail Anhänge enthält:  
- Rufe das Tool `save_email_attachments` auf.  
- Übergib den Pfad zur E-Mail (`email_path`).  
- Dieses Tool speichert die Anhänge automatisch im Elternordner des E-Mail-Verzeichnisses und sorgt dafür, dass keine Dateien überschrieben werden.  

### Schritt C: Antwort formulieren (Empfangsbestätigung)
Prüfe, ob der Studierende nach einer Empfangsbestätigung fragt oder ob eine Bestätigung angebracht ist.  
- Falls ja: Verfasse eine kurze, freundliche Bestätigung des Erhalts.  
- Falls nein (und keine sonstigen Fragen offen sind): Du kannst EXAKT mit `NO_REPLY_NEEDED` antworten, falls die interne Logik das zulässt, aber im Zweifel ist eine kurze Bestätigung immer gut.  

## 3. Signalwort bei Erfolg
Wenn die Tools erfolgreich aufgerufen wurden (Kalender und Anhänge), und du eine Antwort verfasst hast, gib diese im Standardformat zurück.

Falls die E-Mail **KEINE** finale Abgabe ist, antworte mit `NO_FINAL_SUBMISSION_RELEVANCE`.
