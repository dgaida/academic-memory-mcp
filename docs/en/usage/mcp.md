# Model Context Protocol (MCP)

The most powerful way to use the system is via an MCP client (such as Claude Desktop). This allows AI agents to directly access your university knowledge.

## Starting the Server
```bash
mcp-uni serve-mcp
```

## Available Tools

The system provides various specialized tools to agents:

*   **`search_documents`**: Semantic search across all indexed documents (PDFs, emails, scripts).  
*   **`get_folder_summary`**: Query aggregated folder information to get a quick overview of a topic or lecture.  
*   **`get_student_context`**: Retrieve complete history and status of a student (email history, thesis status).  
*   **`generate_mail_reply`**: Draft an email based on the existing context and predefined skills.  
*   **`get_open_tasks`**: Extraction of TODOs and open tasks from all documents.  

## Integration
To use the server in **Claude Desktop**, add it to your configuration:

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
