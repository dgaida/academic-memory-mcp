# Nutzung

Das MCP University Memory System bietet verschiedene Schnittstellen zur Interaktion mit Ihren Daten.

## Kernfunktionen

*   **[Indexierung im Detail](indexing-details.md)**: Erfahren Sie genau, wie der Indexierungsprozess abläuft und welche Dateien erzeugt werden.  
*   **[E-Mail Klassifizierung](../packages/email-classifier/index.md)**: Training und Nutzung des Klassifikators für studentische Anfragen.  
*   **[Datenbank-Management](database-management.md)**: Manuelle Verwaltung der SQLite-Datenbank und des Suchindex.  
*   **[Model Context Protocol (MCP)](mcp.md)**: Integration in KI-Agenten wie Claude Desktop.  
*   **[Hilfsskripte](scripts.md)**: Werkzeuge zur Datenbereinigung und Visualisierung.  

## Kommandozeile (CLI)

Die CLI ist der primäre Weg, um das System zu verwalten.

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

## Workflows

*   **[E-Mail Workflow](email-workflow.md)**: Der vollständige Prozess von der E-Mail bis zum Antwort-Entwurf.  
