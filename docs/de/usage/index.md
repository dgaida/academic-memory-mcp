# Nutzung

Das MCP University Memory System bietet verschiedene Schnittstellen für die tägliche Arbeit.

## Kommandozeile (CLI)

Das `mcp-uni` Tool ist der zentrale Einstiegspunkt.

### Indexierung (`index`)
Scannt alle konfigurierten Ordner und aktualisiert den Index.
```bash
mcp-uni index
```

### Suche (`search`)
Führt eine schnelle Abfrage über den gesamten Datenbestand aus.
```bash
mcp-uni search "Inhalt der Vorlesung 5"
```

### Watchdog (`watch`)
Startet einen Hintergrundprozess, der auf Dateiänderungen reagiert und den Index in Echtzeit aktualisiert.
```bash
mcp-uni watch
```

## Model Context Protocol (MCP)

Die leistungsstärkste Nutzung erfolgt über einen MCP-Client (wie Claude Desktop).

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
