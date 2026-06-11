# Usage

The MCP University Memory System provides various interfaces for interacting with your data.

## Command Line Interface (CLI)

The CLI is the primary way to manage the system and perform manual searches.

### Indexing (`index`)
This command scans all configured folders, creates summaries, and updates the index.
- **[Details of the indexing process](indexing-details.md)**

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

## Email Classification

The system includes a subpackage for the automated classification of student emails (e.g., bachelor's thesis, internship project).
[Details of the Email Workflow](email-workflow.md)

## Database Management (`db`)

The `db` command group allows direct management of metadata and the search index.

## Model Context Protocol (MCP)

The most powerful way to use the system is via an MCP client (such as Claude Desktop).
