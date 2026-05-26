# AI Agent Instructions - MCP University

This file contains essential information for AI agents working on the **MCP University** (academic-memory-mcp) project.

## Project Overview
MCP University is an offline-first system for managing academic data (students, emails, theses, documents) using local LLMs. It provides automated classification, summarization, and RAG-based search.

### Core Components  
1. **Crawler (`mcp_university/crawler/`)**: Indexes the filesystem, detects changes (SHA-256), and manages metadata.  
2. **Parser (`mcp_university/parser/`)**:  
   - Supports PDF (via `docling`), DOCX, EML, and MSG (via `extract-msg`).  
   - Analyzes only the first 3 pages of documents to save resources.  
   - Suppresses noisy `extract-msg` warnings.  
3. **Classifier (`mcp_university/classifier/`)**:  
   - Classifies emails using XGBoost or RandomForest.  
   - **Data Structure:** Training and test data are organized by class folders, each containing `Inbox` and `SentItems` subfolders.
   - **Feature Modes:** Supports `tfidf` (keyword-based), `embedding` (semantic-based), and `combined`.
   - **Model Naming:** Trained models automatically append the mode to the filename (e.g., `email_classifier_tfidf.pkl`).
   - `sort_emails.py` sorts emails into semester and student folders.  
   - **Special Logic:** Classes starting with `BA_` or `MA_` are stored directly in `Semester/Inbox` or `Semester/SentItems` (no student subfolder).
   - **Name Extraction:** Extracts lastnames from `smail.th-koeln.de` (format: `v.n@smail.th-koeln.de` -> `N`).  
4. **Retrieval (`mcp_university/retrieval/`)**:  
   - Hybrid search using Qdrant (vector) and BM25 (text).  
   - Native Python fallback if the `qmd` CLI is missing.  
5. **Summarizer (`mcp_university/summarizer/`)**:  
   - German-localized summarization and Q&A using Ollama.  
   - Specialized prompts for document types (Thesis, Protokoll, Formular, etc.).  
   - **Persona:** Daniel Gaida, Professor at TH Köln. Signature: 'Viele Grüße, Daniel Gaida'.
6. **Metadata Store (`mcp_university/metadata/`)**:  
   - SQLite database for file metadata, student info, and folder summaries.  
   - Primary source of truth for students is `students.yaml`.
7. **Outlook Integration (`outlook_macro/`)**:  
   - VBA macros for sorting and archiving emails.
   - Consistency: Use 'SentItems' (no space) for sent email folders.

## General Guidelines  
- Follow the project structure and naming conventions.  
- Maintain the offline-first approach (local LLMs, local databases).  
- Ensure all new features are covered by tests.  
- Respect the configurations in `config/folders.yaml` and `config/models.yaml`.  

## Mandatory Rules & Guidelines

### Language Policy  
- **German** is the authoritative language for documentation, UI, and LLM outputs.  
- **English** is a full translation of the documentation.  
- Internal prompts can be English but MUST instruct the model to output German.  
- Standard salutation for students: 'Guten Tag Herr/Frau [Nachname]'.

### Coding Standards  
- **Docstrings:** Google-style required for ALL classes and methods (including private).  
- **Type Hints:** Explicit return type hints are mandatory for API documentation.  
- **Linting:** Run `ruff check . --fix` before submitting.  
- **Coverage:** Minimum 95% docstring coverage (enforced by `interrogate`).  
- **Tests:** Use `pytest`. Avoid global monkey-patching; use scoped patches or fixtures.  

### Documentation Skill  
- **MANDATORY:** Always use the [MkDocs Documentation Ecosystem Skill](https://github.com/dgaida/auto-version-action/blob/main/skills/SKILL_docs.md) when updating documentation, `README.md`, or MkDocs configurations.  
- **Structure:** Bilingual setup using `mkdocs-static-i18n` with `docs_structure: folder`.  
- **Paths:** Always use relative paths in Markdown (e.g., `../assets/...`).  
- **Sync:** Changes to subpackages must be reflected in `api/`, `usage/`, and `architecture/` in BOTH `de` and `en`.  

### Cleanup (MANDATORY)
Delete all temporary files before submission:  
- `__pycache__`, `.pytest_cache`, `.coverage`, `htmlcov`.  
- `*.log`, temporary test artifacts (`test.docx`, etc.).  
- Build artifacts (`dist/`, `build/`, `*.egg-info`).  

## Development Workflow  
1. **Environment:** `pip install -e .`  
2. **CLI Usage:** Use `mcp-uni` CLI for testing indexing and search.  
3. **Database Sync:** Use `mcp-uni db sync-students` after updating `students.yaml`.  
4. **Parsers:** When adding new parsers, update `mcp_university/parser/factory.py`.  
5. **MCP Server:** Keep the MCP server tools in `mcp_university/mcp_server/server.py` updated with new capabilities.  
6. **Classification:** Train with `mcp_university/classifier/train.py`, evaluate with `evaluate.py`.  

## CI/CD  
- **CodeQL:** Requires "Code scanning" to be enabled in the repository settings to function correctly.  

## Prerequisites  
- **qmd CLI:** Required for hybrid search. Install globally via: `npm install -g @tobilu/qmd`  
- **Docling:** Required for PDF parsing. Install with: `pip install docling` and initialize with `cp-config` if prompted.  

## Outlook Macro Maintenance  
- Keep VBA documentation in Google-style (`''' Args:`, `''' Returns:`).  
- Verify email address and folder existence before processing to avoid runtime errors.  
- Use `latin-1` encoding when reading/writing VBA files via Python scripts.  
- **Performance:** Use `DoEvents` and `Sleep` in long-running loops (e.g., email processing) to ensure Outlook remains responsive and does not freeze.  
- **Item Creation:** Use `target_folder.Items.Add(0)` instead of `mail.Move()` to avoid specific Outlook errors in non-default folders.
