# AI Agent Instructions

This file provides instructions and guidelines for AI agents working on the MCP University project.

## General Guidelines  
- Follow the project structure and naming conventions.  
- Maintain the offline-first approach (local LLMs, local databases).  
- Ensure all new features are covered by tests.  
- Respect the configurations in `config/folders.yaml` and `config/models.yaml`.  

## Cleanup Requirements  
- **MANDATORY:** Delete all temporary files and directories before creating a pull request or submitting changes.  
- Temporary files include:  
    - `__pycache__` directories  
    - `.pytest_cache`  
    - `.coverage` and `htmlcov`  
    - Log files (`*.log`)  
    - Temporary test artifacts (e.g., `test.docx`, `test.json`, `test.md` in the root)  
    - Build artifacts (e.g., `dist/`, `build/`, `*.egg-info`)  

## Development  
- Use `mcp-uni` CLI for testing indexing and search.  
- When adding new parsers, update `mcp_university/parser/factory.py`.  
- Keep the MCP server tools in `mcp_university/mcp_server/server.py` updated with new capabilities.  

## Pull Request Policy  
- Before creating a pull request, you MUST delete all temporary files and folders to keep the repository clean.  

## CI/CD  
- **CodeQL:** Requires "Code scanning" to be enabled in the repository settings to function correctly.  

## Prerequisites  
- **qmd CLI:** Required for hybrid search. Install globally via: `npm install -g @tobilu/qmd`  
- **Docling:** Required for PDF parsing. Install with: `pip install docling` and initialize with `cp-config` if prompted.  

## Outlook Macros  
- **Documentation:** All functions and subroutines in Outlook macros (`outlook_macro/*.bas`) must remain documented using the `''' Args:` and `''' Returns:` format (Google-style documentation for VBA).  

## Documentation Skill
- **MANDATORY:** Always use the [MkDocs Documentation Ecosystem Skill](https://github.com/dgaida/auto-version-action/blob/main/skills/SKILL_docs.md) when updating documentation, `README.md`, or MkDocs configurations.
