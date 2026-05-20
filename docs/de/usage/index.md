# Nutzung

Das MCP University Memory System bietet verschiedene Schnittstellen zur Interaktion mit Ihren Daten.

## Kommandozeile (CLI)

Die CLI ist der primäre Weg, um das System zu verwalten und manuelle Suchen durchzuführen.

### Indexierung (`index`)
Dieser Befehl scannt alle konfigurierten Ordner, erstellt Zusammenfassungen und aktualisiert den Index.
```bash
mcp-uni index
```

### Suche (`search`)
Führt eine schnelle Abfrage über den gesamten Datenbestand durch.
```bash
mcp-uni search "Inhalt der Vorlesung 5"
```

### Überwachung (`watch`)
Startet einen Hintergrundprozess, der auf Dateiänderungen reagiert und den Index in Echtzeit aktualisiert.
```bash
mcp-uni watch
```

## E-Mail Klassifizierung

Das System enthält ein Subpackage zur automatisierten Klassifizierung von studentischen E-Mails (z.B. Bachelorarbeit, Praxisprojekt).

### Modell trainieren
Um den Klassifikator zu nutzen, muss er zuerst mit Beispieldaten trainiert werden. Erwarten wird eine Ordnerstruktur, in der jeder Unterordner eine Klasse repräsentiert und die E-Mails (.msg) enthält.

```bash
python3 mcp_university/classifier/train.py /pfad/zu/trainingsdaten --mode combined --method xgboost
```

Dabei kann zwischen `randomforest` und `xgboost` (Standard) gewählt werden.

### E-Mail klassifizieren
Nach dem Training kann eine einzelne E-Mail-Datei klassifiziert werden:

```bash
python3 mcp_university/classifier/predict.py /pfad/zur/email.msg
```

Die Ausgabe enthält die wahrscheinlichste Klasse sowie die Konfidenz und eine detaillierte Wahrscheinlichkeitsverteilung.
### E-Mail Sortierung (Studenten-Ordner)
Das leistungsfähigste Skript sortiert E-Mails nicht nur nach Klasse, sondern auch nach Semester und Student (Nachname):

```bash
python3 mcp_university/classifier/sort_emails.py /quell/ordner --config config/class_paths.yaml --model data/email_classifier.pkl
```

Es erkennt automatisch:  
- **Semester:** Basierend auf dem E-Mail-Datum (SoSe/WS).  
- **Student:** Extrahiert den Nachnamen aus `smail.th-koeln.de` Adressen oder Anzeigenamen.  
- **Richtung:** Sortiert in `Inbox` oder `SentItems` Unterordner.  
- **Bericht:** Erstellt eine `sorted_emails.md` mit einer Übersicht aller verschobenen Mails.  

### Batch-Klassifizierung
Um einen ganzen Ordner mit E-Mails automatisch zu sortieren (nur Klassifizierung):
```bash
python3 mcp_university/classifier/classify_folder.py /quell/ordner --model data/email_classifier.pkl
```
Dies verschiebt die E-Mails in Unterordner, die nach den vorhergesagten Klassen benannt sind.


## Datenbank-Management (`db`)

Die `db` Befehlsgruppe erlaubt die direkte Verwaltung der Metadaten und des Suchindex.

### Auflisten von Inhalten
Sie können verschiedene Entitäten in der Datenbank auflisten:

*   **Dateien:** `mcp-uni db list-files`  
*   **Ordner:** `mcp-uni db list-folders`  
*   **Studenten:** `mcp-uni db list-students` (Hinweis: Nutzen Sie `sync-students` zum Befüllen)  
*   **Zusammenfassungen:** `mcp-uni db list-summaries`  
*   **Deadlines:** `mcp-uni db list-deadlines`  

### Synchronisierung von Studenten (`sync-students`)
Befüllt die Datenbank aus einer `students.yaml`.
```bash
mcp-uni db sync-students
```

### Löschen von Inhalten
Einträge können über ihre ID gelöscht werden. Mit der Option `--force` oder `-f` wird die Bestätigungsabfrage übersprungen.

*   **Dateien löschen:** `mcp-uni db delete-file <ID_1> <ID_2> ...`  
*   **Ordner löschen:** `mcp-uni db delete-folder <ID>` (entfernt rekursiv alle enthaltenen Dateien)  
*   **Student löschen:** `mcp-uni db delete-student <ID>`  
*   **Zusammenfassung löschen:** `mcp-uni db delete-summary <ID>`  
*   **Deadline löschen:** `mcp-uni db delete-deadline <ID>`  

## Model Context Protocol (MCP)

Der leistungsfähigste Weg, das System zu nutzen, ist über einen MCP-Client (wie Claude Desktop).

### Server starten
```bash
mcp-uni serve-mcp
```

### Verfügbare Tools  
*   `search_documents`: Semantische Suche in Dokumenten.  
*   `get_folder_summary`: Abfrage von aggregierten Ordner-Informationen.  
*   `get_student_context`: Komplette Historie und Status eines Studenten abrufen.  
*   `generate_mail_reply`: Entwurf einer E-Mail basierend auf dem Kontext.  
*   `get_open_tasks`: Extraktion von TODOs aus allen Dokumenten.  

## Typische Workflows

### 1. Vorbereitung einer Sprechstunde
Bitten Sie Ihren Agenten: "Gib mir den Kontext zu Student Max Mustermann und zeige mir seine letzten Abgaben."
Der Agent nutzt `get_student_context` and `search_documents`, um Ihnen eine kompakte Übersicht zu liefern.

### 2. Beantworten von E-Mails
Kopieren Sie die E-Mail eines Studenten in den Chat und nutzen Sie das Tool `generate_mail_reply`. Das System berücksichtigt dabei automatisch den Status der Abschlussarbeit oder offene Deadlines.

## Konfiguration

### Zweistufige Zusammenfassung
In der `config/folders.yaml` kann die Option `summarize_emails_individually` (Standard: `false`) aktiviert werden. Wenn diese auf `true` gesetzt ist, werden E-Mail-Threads in zwei Stufen zusammengefasst: erst jede E-Mail einzeln, dann die gesamte Konversation.

## Hilfsskripte

Das System enthält nützliche Skripte im Ordner `scripts/`:

- **`remove_empty_folders.py`**: Löscht rekursiv alle leeren Ordner in einem Verzeichnis.  
- **`flatten_directory.py`**: Flacht eine Ordnerstruktur ab, indem alle Dateien in das Wurzelverzeichnis verschoben werden (inkl. Namenskollisionsprüfung).  
