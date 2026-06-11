# Model Context Protocol (MCP)

Der leistungsfähigste Weg, das System zu nutzen, ist über einen MCP-Client (wie Claude Desktop). Dies ermöglicht es KI-Agenten, direkt auf Ihr universitäres Wissen zuzugreifen.

## Server starten
```bash
mcp-uni serve-mcp
```

## Verfügbare Tools

Das System stellt Agenten verschiedene spezialisierte Tools zur Verfügung:

*   **`search_documents`**: Semantische Suche in allen indexierten Dokumenten (PDFs, E-Mails, Skripte).  
*   **`get_folder_summary`**: Abfrage von aggregierten Ordner-Informationen, um einen schnellen Überblick über ein Thema oder eine Vorlesung zu erhalten.  
*   **`get_student_context`**: Komplette Historie und Status eines Studenten abrufen (E-Mail-Verlauf, Abschlussarbeit-Status).  
*   **`generate_mail_reply`**: Entwurf einer E-Mail basierend auf dem vorhandenen Kontext und vordefinierten Skills.  
*   **`get_open_tasks`**: Extraktion von TODOs und offenen Aufgaben aus allen Dokumenten.  

## Integration
Um den Server in **Claude Desktop** zu nutzen, fügen Sie ihn zu Ihrer Konfiguration hinzu:

```json
{
  "mcpServers": {
    "mcp-university": {
      "command": "mcp-uni",
      "args": ["serve-mcp"]
    }
  }
}
```
