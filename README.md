![Tests](https://github.com/dgaida/academic-memory-mcp/actions/workflows/tests.yml/badge.svg) ![Lint](https://github.com/dgaida/academic-memory-mcp/actions/workflows/lint.yml/badge.svg) ![CodeQL](https://github.com/dgaida/academic-memory-mcp/actions/workflows/codeql.yml/badge.svg) ![Documentation](https://github.com/dgaida/academic-memory-mcp/actions/workflows/docs.yml/badge.svg) ![Auto Versioning](https://github.com/dgaida/academic-memory-mcp/actions/workflows/auto-version.yml/badge.svg)
[![Version](https://img.shields.io/github/v/tag/dgaida/academic-memory-mcp?label=version)](https://github.com/dgaida/academic-memory-mcp/tags)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![codecov](https://codecov.io/gh/dgaida/academic-memory-mcp/branch/master/graph/badge.svg)](https://codecov.io/gh/dgaida/academic-memory-mcp)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://dgaida.github.io/academic-memory-mcp/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/dgaida/academic-memory-mcp/graphs/commit-activity)
![Last commit](https://img.shields.io/github/last-commit/dgaida/academic-memory-mcp)

# MCP University Memory System

A locally-running, agentic knowledge and memory system for university and research work.

## Features  
- Recursive analysis of local folders  
- Semantic understanding of documents and emails  
- Hierarchical summaries (File -> Folder -> Root)  
- Hybrid search (BM25 + Vector)  
- MCP Server integration  
- Fully offline using local LLMs (Ollama)  

## Prerequisites  
- **qmd CLI:** Required for hybrid search. Install globally via: `npm install -g @tobilu/qmd`  
- **Docling:** Required for PDF parsing. Install with: `pip install docling` and initialize with `cp-config` if prompted.  

## Tech Stack  
- **Document Parsing:** Docling  
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
