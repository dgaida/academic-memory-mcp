# Getting Started

This guide will walk you through the setup and initial steps with the MCP University Memory System.

## Prerequisites

Ensure the following software is installed:

*   **Python 3.10+**  
*   **Node.js >= 22:** Required for `qmd`.  
*   **qmd:** `npm install -g @tobilu/qmd`  
*   **Ollama:** Install Ollama and pull the default model:  
    ```bash
    ollama pull gemma2:2b
    ```
*   **MinerU (magic-pdf):** For PDF parsing (installed via pip).  

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/example/mcp-university.git
cd mcp-university
pip install -e .
```

## Configuration

Adjust the folders to be monitored in `config/folders.yaml`:

```yaml
folders:
  - /path/to/your/lectures
  - /path/to/student/records
exclude_patterns:
  - ".git"
  - "node_modules"
```

## First Index Run

Start the crawler to analyze your documents and create summaries:

```bash
mcp-uni index
```

The process performs the following steps:  
1. Scans the configured folders.  
2. Extracts text from PDF, DOCX, MD, etc.  
3. Generates summaries using Ollama.  
4. Stores metadata in SQLite and indexes the text in the search index.  

## Using Search

Test the search directly via the CLI:

```bash
mcp-uni search "When is the deadline for Max Mustermann's master's thesis?"
```

## Start MCP Server

Provide the tools for your AI agents (e.g., in Claude Desktop):

```bash
mcp-uni serve-mcp
```

Now your agent can access documents, draft email replies, and retrieve student context.
