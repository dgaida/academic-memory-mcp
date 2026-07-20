# Terminverwaltung (Appointment GUI)

Der Appointment Manager dient zur Vorbereitung von Terminen mit Studierenden. Er verknüpft die Termine aus Ihrem Kalender mit den im System vorhandenen Informationen über den jeweiligen Studierenden.

## Starten der GUI

Führen Sie das folgende Skript aus:

```bash
python scripts/appointment_gui.py
```

## Funktionen

*   **Wochenübersicht:** Zeigt alle Termine der aktuellen Woche an, die aus `data/appointments.md` eingelesen werden.  
*   **Studenten-Kontext:** Bei Auswahl eines Termins sucht das System automatisch nach dem passenden Studenten-Ordner.  
    *   **Wie findet er den Ordner?**  
        Das System extrahiert zunächst den Teilnehmernamen (bzw. Nachnamen) und die E-Mail-Adresse aus den Teilnehmerinformationen des Termins. Anschließend wird anhand der E-Mail-Klasse und des Nachnamens der entsprechende Pfad gesucht:  
        1. **Namensextraktion:** Der Nachname wird über reguläre Ausdrücke und Textmuster aus dem Teilnehmer-String gefiltert (z. B. "Mustermann" aus `max.mustermann@th-koeln.de` oder "Mustermann" aus `Mustermann Max <... >`).  
        2. **Klassenpfad-Mapping:** Jede E-Mail-Klasse (z. B. *Bachelor Thesis*, *Projekt*) hat in der Konfiguration `classifier_paths.yaml` einen definierten Basispfad. Das System bestimmt die Klasse des Termins (siehe unten) und schaut zuerst im entsprechenden Basispfad nach einem Ordner, der den Nachnamen des Studenten enthält.  
        3. **Fallback-Suche:** Wird im spezifischen Klassenpfad kein Ordner gefunden (z. B. weil die Klasse des Termins nicht übereinstimmt oder der Ordner an einer anderen Stelle liegt), durchsucht das System alle anderen konfigurierten Basispfade nach einem passenden Ordner für diesen Nachnamen.  
    *   **Woher kennt das Tool das Thema des Termins bzw. bestimmt die E-Mail-Klasse?**  
        Die Bestimmung erfolgt über den Betreff (Titel) des Kalendertermins:  
        *   Das System liest die konfigurierten E-Mail-Klassen und deren Pfade aus der Datei `classifier_paths.yaml` ein.  
        *   Es gleicht den Betreff des Termins mit den Klassennamen ab (Groß-/Kleinschreibung wird ignoriert). Wenn der Name einer Klasse (z. B. "Bachelor Thesis" oder "Projekt") im Betreff vorkommt, wird dem Termin diese E-Mail-Klasse zugewiesen.  
        *   Wird keine Übereinstimmung im Betreff gefunden, dann soll der Betreff an das Emailclassifier Modell übergeben werden und dieses entscheidet über die Klasse. Wenn in dem vorhergesagten Klassenordner keine Mails von dem Teilnehmer des Termins gefunden werden, dann fällt das System auf die Standardklasse `"Other"` zurück.  
*   **Zusammenfassungen:** Zeigt die KI-generierte Konversationszusammenfassung (`.emails_summary.md`) des gefundenen studentischen Hauptordners an.  
    *   **Erstellt die GUI die Zusammenfassung, falls es noch keine gibt?**  
        Ja! Wenn für den gefundenen Studentenordner noch keine Zusammenfassung existiert oder diese veraltet ist (d h. wenn das Dateidatum von `.emails_summary.md` älter ist als die neueste E-Mail-Datei `.msg` / `.eml` im Ordner), generiert bzw. aktualisiert die GUI die Zusammenfassung automatisch im Hintergrund. Dazu liest sie die gesamte E-Mail-Historie des Studenten ein und lässt über das lokale LLM eine aktuelle, strukturierte Zusammenfassung generieren, die als `.emails_summary.md` im Studentenordner gespeichert wird.  
*   **Steckbriefe:** Zeigt den aktuellen Steckbrief des Studierenden (Interessen, bisherige Themen, bevorzugte Anrede etc.) an.  
    *   **Wird dieser durch die GUI auch erstellt, wenn es noch keinen gibt?**  
        Ja! Wenn beim Auswählen des Termins die E-Mail-Adresse des Teilnehmers bekannt ist, ruft das System den `PersonProfiler` auf. Dieser prüft, ob bereits ein Steckbrief unter `D:\Steckbriefe\<email>.md` (oder alternativ im lokalen Ordner `Steckbriefe/`) existiert. Gibt es noch keinen Steckbrief, sucht der Profiler nach allen E-Mails dieser Person (bis zu 100 der neuesten E-Mails aus allen Archiv-Pfaden), bezieht Informationen aus dem Wissensgraphen (z. B. Rollen, Zugehörigkeiten) ein, bestimmt die bevorzugte Anrede ("Du" oder "Sie") durch LLM-Analyse der letzten Direkt-E-Mails und erstellt vollautomatisch einen neuen, detaillierten Steckbrief in Markdown. Sollte bereits ein Steckbrief existieren, wird dieser bei neuen E-Mails ebenfalls automatisch aktualisiert.  
*   **Datei-Explorer:** Ermöglicht den direkten Zugriff auf alle Dateien im Ordner des Studierenden (z.B. Exposés, Entwürfe).  

## Intelligente Terminbuchung & Konfliktprüfung

Wenn das System eine E-Mail beantwortet (Aktion 1: "Antwort schreiben"), prüft es automatisch im Hintergrund auf Terminvorschläge oder Terminbestätigungen (Zusagen) seitens des Absenders.

### Funktionsweise

1. **Erkennung:** Das LLM analysiert die eingehende Mail auf konkrete Terminvorschläge (z. B. "Passt es am Dienstag um 14:00?") oder Zusagen (z. B. "Ich nehme den Termin am Montag um 15:30 Uhr").  
2. **Intelligenter Kalenderabgleich:**  
   * Das System liest die bestehenden Termine aus der Datei `data/appointments.md`.  
   * Es prüft intelligent, ob zu dem vorgeschlagenen oder bestätigten Zeitpunkt bereits ein Termin oder ein Blocker existiert:  
     * **Frei:** Wenn kein Termin oder nur ein Blocker speziell für diesen Termin/Studenten eingetragen ist, ist das System frei. Der Termin wird über das Tool `manage_calendar_appointment` direkt im Kalender gebucht und die Person wird eingeladen. Das System antwortet mit dem Signalwort `APPOINTMENT_BOOKED`.  
     * **Belegt (Konflikt):** Wenn ein ganz anderer Termin oder ein generischer Blocker (z. B. eine andere Besprechung, privat, etc.) im Weg steht, erkennt das System dies als Konflikt.  
3. **Alternativenvorschlag bei Konflikten:**  
   * Falls ein Konflikt erkannt wird, liest das System automatisch die freien Terminslots aus `data/free_slots.md` (über das Tool `get_appointment_slots`) ein.  
   * Es schlägt diese freien Termine als Alternativen in der Antwort-E-Mail vor und bittet den Absender um eine neue Auswahl.  

### Vereinheitlichung der Aktionen (Aktion 1 & Aktion 3)

Da die reguläre Antwort-Generierung (Aktion 1: "Antwort schreiben") diese intelligente Termin- und Konfliktprüfung nun standardmäßig durchführt, ist eine separate Aktion für "Termin im Kalender anlegen und Person dazu einladen" (ehemals Aktion 3) hinfällig geworden und wurde aus dem System entfernt. Aktion 1 deckt beide Fälle nahtlos ab.

## Datenquelle

Die Termine werden üblicherweise über das Outlook-VBA-Makro `AppointmentExport.bas` exportiert. Das System liest diese exportierten Daten ein und reichert sie mit dem Wissen aus der lokalen Wissensbasis an.
