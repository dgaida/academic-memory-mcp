# Usage

The MCP University Memory System provides various interfaces for interacting with your data.

## Core Features

*   **[Indexing in Detail](indexing-details.md)**: Learn exactly how the indexing process works and which files are generated.  
*   **[Email Classification](../packages/email-classifier/index.md)**: Training and using the classifier for student inquiries.  
*   **[Database Management](database-management.md)**: Manual management of the SQLite database and search index.  
*   **[Model Context Protocol (MCP)](mcp.md)**: Integration into AI agents like Claude Desktop.  
*   **[Helper Scripts](scripts.md)**: Tools for data cleanup and visualization.  

## Command Line Interface (CLI)

The CLI is the primary way to manage the system.

### Indexing (`index`)
This command scans all configured folders, creates summaries, and updates the index.
```bash
mcp-uni index
```

### Search (`search`)
Performs a quick query across the entire dataset.
```bash
mcp-uni search "Lecture 5 content"
```

### Watch (`watch`)
Starts a background process that responds to file changes and updates the index in real-time.
```bash
mcp-uni watch
```

## Workflows

*   **[Email Workflow](email-workflow.md)**: The complete process from email to response draft.  
