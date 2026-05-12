# MCP University Memory System

A locally-running, agentic knowledge and memory system for university and research work.

## Features
- Recursive analysis of local folders
- Semantic understanding of documents and emails
- Hierarchical summaries (File -> Folder -> Root)
- Hybrid search (BM25 + Vector)
- MCP Server integration
- Fully offline using local LLMs (Ollama)

## Tech Stack
- **Document Parsing:** MinerU (magic-pdf)
- **Local LLM:** Ollama
- **Embeddings:** bge-m3
- **Vector DB:** Qdrant
- **MCP Framework:** FastMCP
- **Metadata:** SQLite
- **File Watching:** watchdog

## Project Structure
```text
mcp_university/
├── config/             # YAML configurations and prompts
├── data/               # Persistent data (SQLite, Indexes, Cache)
├── src/mcp_university/ # Core package
│   ├── crawler/        # File system crawling and watching
│   ├── parser/         # Document and email parsing
│   ├── summarizer/     # LLM summary generation
│   ├── retrieval/      # Hybrid search index
│   ├── metadata/       # SQLite storage
│   ├── mcp_server/     # FastMCP server
│   ├── agent/          # Agentic workflows
│   ├── cli/            # Typer-based CLI
│   └── config.py       # Config loader
└── tests/              # Unit and integration tests
```

## Installation
```bash
pip install -e .
```

## Usage
```bash
mcp-uni index
mcp-uni search "your query"
mcp-uni serve-mcp
```
