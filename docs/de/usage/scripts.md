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

## Wissensgraph

### Wissensgraph visualisieren
Generiert eine interaktive HTML-Visualisierung des Wissensgraphen.
```bash
python scripts/visualize_knowledge_graph.py
```
Die Ausgabe erfolgt in `knowledge_graph.html`.

## Vorlesungen & Lehre

### Vorlesungsskripte zusammenfassen
Sucht nach PDFs in einem Ordner und generiert kompakte Markdown-Zusammenfassungen. Überspringt Dateien, die bereits verarbeitet wurden.
```bash
python scripts/summarize_lectures.py /pfad/zu/vorlesungen
```
