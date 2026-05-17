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
Der Agent nutzt `get_student_context` und `search_documents`, um Ihnen eine kompakte Übersicht zu liefern.

### 2. Beantworten von E-Mails
Kopieren Sie die E-Mail eines Studenten in den Chat und nutzen Sie das Tool `generate_mail_reply`. Das System berücksichtigt dabei automatisch den Status der Abschlussarbeit oder offene Deadlines.
