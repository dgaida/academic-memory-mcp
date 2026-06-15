# Hilfsskripte

Das System enthält verschiedene nützliche Skripte im Ordner `scripts/` zur Vorbereitung und Verwaltung Ihrer Daten.

## Verzeichnisbereinigung

### Leere Ordner entfernen
Löscht rekursiv alle leeren Ordner in einem Verzeichnis.
```bash
python scripts/remove_empty_folders.py /pfad/zu/daten
```

### Verzeichnis flachklopfen (Flatten)
Flacht eine Ordnerstruktur ab, indem alle Dateien in das Wurzelverzeichnis verschoben werden (inkl. automatischer Namenskollisionsprüfung).
```bash
python scripts/flatten_directory.py /pfad/zu/daten
```

## Wissensgraph & Personen

### Wissensgraph visualisieren
Generiert eine interaktive HTML-Visualisierung des Wissensgraphen.
```bash
mcp-uni graph visualize
```
Alternativ kann das Skript direkt aufgerufen werden:
```bash
python scripts/visualize_knowledge_graph.py
```
Die Ausgabe erfolgt in `knowledge_graph.html`.

Unterstützt den Parameter `--filter <Name>` (oder `-f` in der CLI), um den Graphen auf einen bestimmten Knoten und seinen Kontext zu beschränken. Dabei werden alle "Eltern-Strukturen" (eingehende Kanten, z.B. Institut oder Fakultät einer Person) sowie alle von diesen Strukturen ausgehenden Teilgraphen (ausgehende Kanten, z.B. alle Mitglieder des Instituts oder Module einer Person) einbezogen.

### TH Köln Personen-Crawler
Crawlt das Personenverzeichnis der TH Köln nach Namen, E-Mails, Fakultäten und Instituten.
```bash
python scripts/crawl_th_koeln_persons.py A B C
```
Unterstützt mehrere Anfangsbuchstaben als Argumente.

### Personen-Steckbriefe erstellen
Erstellt manuell einen Steckbrief für eine bestimmte E-Mail-Adresse basierend auf vorhandenen E-Mails.
```bash
python scripts/create_person_profiles.py student@smail.th-koeln.de
```

### MOCOGI Datenextraktion
Extrahiert Modulinformationen (Verantwortliche, Prüfer) aus der MOCOGI-API und verknüpft diese im Wissensgraphen.
```bash
python scripts/extract_mocogi_data.py
```

## Vorlesungen & Lehre

### Vorlesungsskripte zusammenfassen
Sucht nach PDFs in einem Ordner und generiert kompakte Markdown-Zusammenfassungen. Überspringt Dateien, die bereits verarbeitet wurden (Mtime-Check).
```bash
python scripts/summarize_lectures.py /pfad/zu/vorlesungen
```
Nutzt primär `liteparse` und einen LLM-Fallback bei Fehlern.
