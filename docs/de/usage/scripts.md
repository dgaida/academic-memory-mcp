# Hilfsskripte (Helper Scripts)

Das System enthält verschiedene nützliche Hilfsskripte zur Vorbereitung, Migration und Verwaltung Ihrer Daten.

---

## Verzeichnisbereinigung & Dateisystem

### Leere Ordner entfernen
Löscht rekursiv alle leeren Ordner in einem Zielverzeichnis.
```bash
python scripts/remove_empty_folders.py /pfad/zu/daten
```

### Verzeichnis flachklopfen (Flatten)
Flacht eine Ordnerstruktur ab, indem alle Dateien in das Wurzelverzeichnis verschoben werden (inkl. automatischer Namenskollisionsprüfung).
```bash
python scripts/flatten_directory.py /pfad/zu/daten
```

---

## E-Mail-Management & Klassifizierung

### E-Mail-Ordnerstruktur korrigieren
Migriert E-Mails in die Standardstruktur: `Semester/Nachname/Inbox|SentItems/`. Dies ist besonders wichtig für die korrekte Zuordnung im System.
```bash
python scripts/fix_email_folders.py data/classifier_paths.yaml
```

**Optionen:**
- `--dry-run`: Zeigt nur die erkannten Fehler an, ohne sie zu beheben.  
- `--verify`: Prüft rekursiv alle E-Mails in allen Unterordnern auf korrekte Semester-, Namens- und Ordnerzuordnung.

### Klassifikator-Daten umstrukturieren
Strukturiert die Trainings- und Testdaten des Klassifikators um, um sie für das Training vorzubereiten.
```bash
python scripts/restructure_classifier_data.py
```

### Trainingsdaten auffüllen (Replenish Datasets)
Füllt Trainings- und Testdaten mit alten E-Mails aus den Originalverzeichnissen auf, wenn ein Mindestbestand unterschritten wird.
```bash
python scripts/replenish_datasets.py -n 100
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

---

## Wissensgraph & Personaldatenbank

Diese Skripte wurden in das eigenständige Package `th_personal_graph` ausgelagert und werden als ausführbare Module aufgerufen.

- **TH Personal Crawler (`python -m th_personal_graph.scripts.crawl_th_koeln_persons`):**
  Crawlt das Personenverzeichnis der TH Köln nach Kontaktdaten, Fakultäten und Instituten.
- **MOCOGI Datenextraktion (`python -m th_personal_graph.scripts.extract_mocogi_data`):**
  Extrahiert Modulinformationen (Verantwortliche, Prüfer) aus der MOCOGI-API und verknüpft diese im Wissensgraphen.
- **Wissensgraph visualisieren (`python -m th_personal_graph.scripts.visualize_knowledge_graph`):**
  Generiert eine interaktive HTML-Visualisierung der Personaldatenbank.

Detaillierte Informationen zur Nutzung und den Parametern dieser Skripte finden Sie auf der Seite **[Personaldatenbank & Personen-Steckbriefe](profiles.md)** sowie in der **[Dokumentation des TH Personal Graph Packages](../packages/th-personal-graph/index.md)**.

---

## Wissensbasis & Memory

### Memory indexieren (Crawler)
Indexiert Dokumente aus den in der Konfiguration definierten Pfaden in die Vektordatenbank.
```bash
mcp-uni memory update
```
Oder direkt über das Skript:
```bash
python scripts/index_memory.py
```

### Vorlesungsskripte zusammenfassen
Sucht nach PDFs in einem Ordner und generiert kompakte Markdown-Zusammenfassungen. Überspringt Dateien, die bereits verarbeitet wurden.
```bash
python scripts/summarize_lectures.py /pfad/zu/vorlesungen
```

### Wissensgraph der Dokumentenmetadaten aufbauen
Baut den Wissensgraphen aus extrahierten E-Mail-Zusammenfassungen und anderen Quellen in `university.db` auf.
```bash
python scripts/build_knowledge_graph.py
```

---

## Termine, Kolloquien & Sonstiges

### Termin-Verwaltung (Gradio GUI)
Öffnet eine Gradio-Benutzeroberfläche zur Visualisierung und schnellen Verwaltung von wöchentlichen Terminen basierend auf `data/appointments.md`.
```bash
python scripts/appointment_gui.py
```

### Kolloquiums-Konfiguration erstellen
Erstellt JSON-Konfigurationsdateien für den `colloquium-protocol-creator`.
```bash
python scripts/create_colloquium_config.py "Name des Kandidaten" --date "2023-10-27" --time "10:00" --location-type campus --room "R3.14"
```

### Embeddings visualisieren
Erstellt eine 2D-Visualisierung der E-Mail-Embeddings mittels t-SNE zur Analyse der Trennbarkeit der E-Mail-Klassen.
```bash
python scripts/visualize_embeddings.py
```
