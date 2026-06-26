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

## E-Mail Management & Klassifizierung

### E-Mail-Ordnerstruktur korrigieren
Migriert E-Mails in die Standardstruktur: `Semester/Nachname/Inbox|SentItems/`. Dies ist besonders wichtig für die korrekte Zuordnung im System.
```bash
python scripts/fix_email_folders.py data/classifier_paths.yaml
```

**Argumente:**
- `--dry-run`: Zeigt nur die erkannten Fehler an, ohne sie zu beheben.
- `--verify`: Prüft rekursiv alle E-Mails in allen Unterordnern auf korrekte Semester-, Namens- und Ordnerzuordnung. Ohne dieses Argument werden nur E-Mails im Basisverzeichnis verarbeitet.

### Klassifikator-Daten umstrukturieren
Strukturiert die Trainings- und Testdaten des Klassifikators um, um sie für das Training vorzubereiten.
```bash
python scripts/restructure_classifier_data.py
```

### Klassen zusammenfassen (Data Augmentation)
Analysiert Trainingsordner und erstellt LLM-Zusammenfassungen für Klassen mit wenigen Daten (<= 50 E-Mails). Diese Zusammenfassungen enthalten Informationen über Themen, Stil und beteiligtes Personal aus der `th_personal.db`.
```bash
python scripts/summarize_classes.py
```

### Synthetische E-Mails generieren
Generiert künstliche E-Mails basierend auf den zuvor erstellten Klassenzusammenfassungen, um den Trainingsdatensatz zu vergrößern.
```bash
python scripts/generate_synthetic_emails.py
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

**Offline-Unterstützung:**
Das Skript ist vollständig offline-fähig, da alle Ressourcen (vis-network) in die HTML-Datei eingebettet werden.

Unterstützt den Parameter `--filter <Name>` (oder `-f` in der CLI), um den Graphen auf einen bestimmten Knoten und seinen Kontext zu beschränken.

### Wissensgraph aufbauen
Baut den Wissensgraphen aus extrahierten E-Mail-Zusammenfassungen und anderen Quellen auf.
```bash
python scripts/build_knowledge_graph.py
```

### TH Köln Personen-Crawler
Crawlt das Personenverzeichnis der TH Köln nach Namen, E-Mails, Fakultäten und Instituten.
```bash
python scripts/crawl_th_koeln_persons.py A B C
```

Unterstützt Filter nach Fakultät oder Einrichtung:
```bash
python scripts/crawl_th_koeln_persons.py --institution "Präsidium"
python scripts/crawl_th_koeln_persons.py --faculty "Informatik und Ingenieurwissenschaften"
```

Mit `--list-institutions` oder `--list-faculties` können alle verfügbaren Optionen angezeigt werden. Für einen vollständigen Crawl aller Bereiche:
```bash
python scripts/crawl_th_koeln_persons.py --crawl-all both
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

## Wissensbasis & Memory

### Memory indexieren
Indexiert Dokumente aus den in der Konfiguration definierten Pfaden in die Vektordatenbank.
```bash
mcp-uni memory update
```
Oder direkt:
```bash
python scripts/index_memory.py
```

## Termine & Kolloquien

### Termin-Verwaltung (GUI)
Öffnet eine Gradio-Oberfläche zur Verwaltung von wöchentlichen Terminen, basierend auf `data/appointments.md`.
```bash
python scripts/appointment_gui.py
```

### Kolloquiums-Konfiguration erstellen
Erstellt JSON-Konfigurationsdateien für den `colloquium-protocol-creator`.
```bash
python scripts/create_colloquium_config.py "Name des Kandidaten" --date "2023-10-27" --time "10:00" --location-type campus --room "R3.14"
```

## Analyse & Visualisierung

### Embeddings visualisieren
Erstellt eine 2D-Visualisierung der E-Mail-Embeddings mittels t-SNE, um die Trennbarkeit der Klassen zu analysieren.
```bash
python scripts/visualize_embeddings.py
```

## Vorlesungen & Lehre

### Vorlesungsskripte zusammenfassen
Sucht nach PDFs in einem Ordner und generiert kompakte Markdown-Zusammenfassungen. Überspringt Dateien, die bereits verarbeitet wurden.
```bash
python scripts/summarize_lectures.py /pfad/zu/vorlesungen
```
