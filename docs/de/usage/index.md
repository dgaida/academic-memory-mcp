# Nutzung

Das MCP University Memory System bietet verschiedene Schnittstellen zur Interaktion mit Ihren Daten.

## Kommandozeile (CLI)

Die CLI ist der primäre Weg, um das System zu verwalten und manuelle Suchen durchzuführen.

### Indexierung (`index`)
Dieser Befehl scannt alle konfigurierten Ordner, erstellt Zusammenfassungen und aktualisiert den Index.
- **[Details zum Indexierungsprozess](indexing-details.md)**

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
[Details zum E-Mail Workflow](email-workflow.md)

## Datenbank-Management (`db`)

Die `db` Befehlsgruppe erlaubt die direkte Verwaltung der Metadaten und des Suchindex.

## Model Context Protocol (MCP)

Der leistungsfähigste Weg, das System zu nutzen, ist über einen MCP-Client (wie Claude Desktop).
