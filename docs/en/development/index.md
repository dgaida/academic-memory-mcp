# Developer Documentation

Welcome to the development of the MCP University Memory System.

## Architecture Principles

1.  **Offline-First:** No dependency on cloud APIs (except optionally for model downloads).  
2.  **Modularity:** Parsers, crawlers, and summarizers are decoupled.  
3.  **Type Safety:** Consistent use of Python type hints and Pydantic.  

## Local Setup

1.  Clone the repository.  
2.  Create and activate a virtual environment.  
3.  Editable installation: `pip install -e ".[dev]"`  

## Coding Standards

### Docstrings
We consistently use the **Google-style** format for all functions and classes. See [Docstring Guide](docstring-guide.md).

### Testing
Tests are performed using `pytest`:
```bash
python3 -m pytest
```

### Quality Assurance
The following tools should be run before every commit:  
*   `interrogate`: Checks docstring coverage (Target: >95%).  
*   `markdownlint`: Checks documentation files.  

## Building Documentation

You can view the documentation locally as follows:
```bash
mkdocs serve
```

This starts a server at `http://127.0.0.1:8000` with live-reload.
