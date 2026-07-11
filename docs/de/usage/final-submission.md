# Finale Abgabe von Abschlussarbeiten

Dieses System erkennt automatisch die finale Abgabe von Bachelor-, Master- und Projektarbeiten. Wenn eine solche E-Mail eingeht, werden mehrere automatisierte Schritte eingeleitet, um den Korrektur- und Prüfungsprozess zu unterstützen.

## Automatisierte Schritte

1.  **Kalender-Erinnerung:** Es wird automatisch ein Termin in Ihrem Outlook-Kalender erstellt, genau 7 Tage nach Eingang der E-Mail (um 08:00 Uhr), um Sie an das Lesen der Arbeit zu erinnern.  
2.  **Speichern von Anhängen:** Alle Anhänge der E-Mail werden automatisch im entsprechenden Studentenordner gespeichert. Bestehende Dateien werden dabei nicht überschrieben, sondern ggf. mit dem Suffix `_final` versehen.  
3.  **Kolloquium-Konfiguration:** Es wird eine `config.json` Datei im Hauptordner des Studenten erstellt. Diese Datei dient als Konfiguration für den [colloquium-protocol-creator](https://dgaida.github.io/colloquium-protocol-creator/).  

## Integration mit dem Colloquium Protocol Creator

Die erstellte `config.json` enthält bereits den Namen der PDF-Arbeit. Sobald ein Kolloquiumstermin mit dem Studenten vereinbart und bestätigt wird, trägt das System das Datum und die Uhrzeit automatisch in diese Konfigurationsdatei ein.

Dies ermöglicht einen nahtlosen Übergang zur Protokollerstellung und Bewertung des Kolloquiums.

## Beispiel der Konfigurationsdatei

Die erstellte Datei hat folgendes Format:

```json
{
  "task": "colloquium",
  "description": "Kolloquium auf dem Campus Gummersbach mit automatischer Gemini-Bewertung",
  "pdf": {
    "filename": "Bachelorarbeit_Mustermann.pdf"
  },
  "colloquium": {
    "date": "DD.MM.YYYY",
    "time": "hh:mm",
    "location_type": "campus",
    "room": "3.228"
  },
  ...
}
```

## Zuordnung im E-Mail-Workflow

Die automatische Erkennung und Verarbeitung der finalen Abgabe ist direkt an den E-Mail-Workflow gekoppelt. Unter den 6 verfügbaren Aktionen des Systems entspricht dies **Aktion 5: Aufgabe im Kalender anlegen (Finale Abgabe)** (bzw. in der GUI als `5) Aufgabe im Kalender anlegen zum Lesen des Anhangs.` bezeichnet).

Sobald diese E-Mail über die Gradio GUI oder das Hintergrundskript verarbeitet wird, führt das System die oben genannten automatisierten Schritte (Anhänge speichern, `config.json` erstellen, Kalender-Erinnerung in 7 Tagen eintragen) aus.
