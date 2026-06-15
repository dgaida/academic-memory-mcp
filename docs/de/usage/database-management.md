# Datenbank-Management (`db`)

Die `db` Befehlsgruppe erlaubt die direkte Verwaltung der Metadaten und des Suchindex.

## Auflisten von Inhalten
Sie können verschiedene Entitäten in der Datenbank auflisten:

*   **Dateien:** `mcp-uni db list-files`  
*   **Ordner:** `mcp-uni db list-folders`  
*   **Studenten:** `mcp-uni db list-students` (Hinweis: Nutzen Sie `sync-students` zum Befüllen)  
*   **Zusammenfassungen:** `mcp-uni db list-summaries`  
*   **Deadlines:** `mcp-uni db list-deadlines`  

## Synchronisierung von Studenten (`sync-students`)
Befüllt die Datenbank aus einer `students.yaml`.
```bash
mcp-uni db sync-students
```

## Löschen von Inhalten
Einträge können über ihre ID gelöscht werden. Mit der Option `--force` oder `-f` wird die Bestätigungsabfrage übersprungen.

*   **Dateien löschen:** `mcp-uni db delete-file <ID_1> <ID_2> ...`  
*   **Ordner löschen:** `mcp-uni db delete-folder <ID>` (entfernt rekursiv alle enthaltenen Dateien)  
*   **Student löschen:** `mcp-uni db delete-student <ID>`  
*   **Zusammenfassung löschen:** `mcp-uni db delete-summary <ID>`  
*   **Deadline löschen:** `mcp-uni db delete-deadline <ID>`  

## Wissensgraph-Management
Sie können die Knoten und Kanten des Wissensgraphen direkt verwalten:

*   **Knoten auflisten:** `mcp-uni db list-nodes`  
*   **Kanten auflisten:** `mcp-uni db list-edges`  
*   **Knoten löschen:** `mcp-uni db delete-node <ID>` (entfernt auch alle zugehörigen Kanten)  
*   **Kante löschen:** `mcp-uni db delete-edge <ID>`  

## Manuelle Fehlerbehebung
Für komplexe manuelle Korrekturen oder zur direkten Bearbeitung der Datenbank empfehlen wir externe Tools wie:  
*   **[DB Browser for SQLite](https://sqlitebrowser.org/)**: Ein benutzerfreundliches Open-Source-Tool zum Anzeigen, Bearbeiten und Abfragen von SQLite-Datenbanken.  

Öffnen Sie einfach die in der Konfiguration angegebene `.db` Datei (Standard: `data/university.db`) in DB Browser for SQLite.
