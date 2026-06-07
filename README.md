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
- **Recursive Analysis:** Analyzes local folders and documents recursively.
- **Semantic Understanding:** Deep understanding of documents (PDF, DOCX) and emails (.msg, .eml).
- **Advanced Classification:** Automated E-Mail classification using Transformer (MiniLM), XGBoost, or RandomForest.
- **Privacy First:** Deterministic anonymization for PII and optional cloud LLM usage with bi-directional anonymization.
- **Intelligent Workflows:** Automated reply generation, necessity checks, and calendar management (Outlook).
- **Interactive Review:** Gradio-based GUI for manual review and re-classification of processed emails.
- **Hierarchical Summaries:** Generates summaries from file level up to the root folder.  
- **Hybrid Search:** Combines BM25 keyword search with Qdrant vector search.  
- **MCP Integration:** Fully integrated with the Model Context Protocol (FastMCP) for tool use.
- **Fully Offline:** Optimized for local LLMs (Ollama) and local databases.

## Prerequisites  
- **Ollama:** Required for local LLM and embedding support.
- **qmd CLI:** Required for hybrid search. Install globally via: `npm install -g @tobilu/qmd`  
- **Docling:** Required for PDF parsing. Install with: `pip install docling` and initialize with `cp-config` if prompted.  

## Tech Stack  
- **LLM/Embeddings:** Ollama, Sentence-Transformers (MiniLM, BGE-M3)
- **Classification:** Scikit-learn, XGBoost, PyTorch (Transformers)
- **Vector DB:** Qdrant  
- **Document Parsing:** Docling, extract-msg  
- **MCP Framework:** FastMCP  
- **Metadata:** SQLite, Pandas
- **GUI:** Gradio

## Project Structure
```text
mcp_university/
├── config/             # YAML configurations and prompts
├── data/               # Persistent data (SQLite, Models, Cache)
├── mcp_university/     # Core package
│   ├── agent/          # Agentic workflows and tool definitions
│   ├── classifier/     # Email classification pipeline (Train, Predict, Evaluate)
│   ├── crawler/        # File system crawling and watching
│   ├── metadata/       # SQLite storage and student management
│   ├── mcp_server/     # FastMCP server implementation
│   ├── parser/         # Document and email parsing logic
│   ├── retrieval/      # Hybrid search index (Qdrant + BM25)
│   ├── summarizer/     # LLM summary and response generation
│   ├── utils/          # Utilities (Anonymization, Config loader)
│   └── cli/            # Typer-based CLI
├── outlook_macro/      # VBA macros for Outlook integration
├── tests/              # Unit and integration tests
└── process_sorted_emails.py # Main workflow script
```

## Installation
```bash
pip install -e .
# Or using conda
conda env create -f environment.yml
```

## Usage
```bash
# Index your files
mcp-uni index

# Search the knowledge base
mcp-uni search "Themenvorschläge Bachelorarbeit"

# Start the MCP server
mcp-uni serve-mcp

# Process and classify new emails
python process_sorted_emails.py
```

Detailed documentation can be found in the `docs/` directory or on the [Documentation Page](https://dgaida.github.io/academic-memory-mcp/).
