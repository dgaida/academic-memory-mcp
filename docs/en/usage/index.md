# Usage

The MCP University Memory System provides various interfaces for daily work.

## Command Line Interface (CLI)

The `mcp-uni` tool is the central entry point.

### Indexing (`index`)
Scans all configured folders and updates the index.
```bash
mcp-uni index
```

### Search (`search`)
Performs a quick query across the entire dataset.
```bash
mcp-uni search "Content of lecture 5"
```

### Watchdog (`watch`)
Starts a background process that reacts to file changes and updates the index in real-time.
```bash
mcp-uni watch
```

## Model Context Protocol (MCP)

The most powerful way to use the system is via an MCP client (like Claude Desktop).

### Start Server
```bash
mcp-uni serve-mcp
```

### Available Tools  
*   `search_documents`: Semantic search in documents.  
*   `get_folder_summary`: Query aggregated folder information.  
*   `get_student_context`: Retrieve complete history and status of a student.  
*   `generate_mail_reply`: Draft an email based on the context.  
*   `get_open_tasks`: Extraction of TODOs from all documents.  

## Typical Workflows

### 1. Preparing for Office Hours
Ask your agent: "Give me the context for student Max Mustermann and show me his latest submissions."
The agent uses `get_student_context` and `search_documents` to provide you with a compact overview.

### 2. Answering Emails
Copy a student's email into the chat and use the `generate_mail_reply` tool. The system automatically takes the status of the thesis or open deadlines into account.
