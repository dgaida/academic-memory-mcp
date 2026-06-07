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
   - **Attachment Handling:** `_parse_msg` safely handles `SignedAttachment` objects by checking for `getFilename` and falling back to `name` or `longFilename`.  
3. **Classifier (`mcp_university/classifier/`)**:  
   - Classifies emails using XGBoost, RandomForest, or **Transformer** models.  
   - **Transformer Architecture:** Uses PyTorch-based `EmailTransformerClassifier` (e.g., MiniLM).  
   - **Input Formatting:** "SUBJECT: <Betreff> | ATTACHMENTS: <Datei1, ...> [SEP] <E-Mail-Body (anonymisiert)>".  
   - **Data Structure:** Training and test data are organized by class folders, each containing `Inbox` and `SentItems` subfolders.  
   - **Feature Modes:** Supports `tfidf`, `embedding`, and `combined`.  
   - **TF-IDF Settings:** Uses `sublinear_tf=False`, `ALL_STOP_WORDS`, and a token pattern `r"(?u)\b(?!\d{2}\b)[a-zA-ZäöüÄÖÜß0-9]{2,}\b"` (ignores 2-digit numbers).  
   - **Model Naming:** `resolve_model_path` automatically manages paths (e.g., `email_classifier_transformer.pkl`).  
   - **Special Logic:** Classes starting with `BA_` or `MA_` are stored directly in `Semester/Inbox` or `Semester/SentItems`.  
   - **Remapping:** Initial classifications of 'Other' are automatically remapped to 'Others'.  
4. **Retrieval (`mcp_university/retrieval/`)**:  
   - Hybrid search using Qdrant (vector) and BM25 (text).  
   - **Embedding Loading:** Always attempt `local_files_only=True` first. Log `ERFOLG: Modell ... wurde LOKAL geladen.` on success. Fall back to cloud only if offline mode is disabled.  
5. **Summarizer (`mcp_university/summarizer/`)**:  
   - German-localized summarization and Q&A using Ollama.  
   - **Persona:** Daniel Gaida, Professor at TH Köln. Signature: 'Viele Grüße, Daniel Gaida'.  
6. **Metadata Store (`mcp_university/metadata/`)**:  
   - SQLite database for file metadata, student info, and folder summaries.  
   - Primary source of truth for students is `students.yaml`.  
7. **Outlook Integration (`outlook_macro/`)**:  
   - VBA macros for sorting and archiving. Hardcoded account: `daniel.gaida@th-koeln.de`.  
   - Format: `YYYYMMDD_HHMMSS - Subject.msg`.  

## General Guidelines  
- Follow the project structure and naming conventions.  
- Maintain the offline-first approach.  
- Ensure all new features are covered by tests.  
- Respect the configurations in `config/folders.yaml` and `config/models.yaml`.  

## Mandatory Rules & Guidelines

### Preservation Policy (CRITICAL)  
- **Documentation:** NEVER delete existing documentation.  
- **Comments:** NEVER delete pre-existing code comments.  
- **Logging:** NEVER delete logging statements unless obsolete.  
- **Code Integrity:** Do not delete existing code unless requested.  

### Language Policy  
- **German** is the authoritative language for documentation, UI, and LLM outputs.  
- **English** is a full translation of the documentation.  
- Internal prompts can be English but MUST instruct the model to output German.  
- Standard salutation for students: 'Guten Tag Herr/Frau [Nachname]'.  

### Coding Standards  
- **Docstrings:** Google-style required for ALL classes and methods. MUST include `Args:` and `Returns:`.  
- **Type Hints:** Explicit return type hints are mandatory.  
- **Linting:** Run `ruff check . --fix` before submitting. No E741, E402, F401, F541.  
- **Coverage:** Minimum 95% docstring coverage (interrogate).  
- **Tests:** Use `pytest`.  
  - **Mocking:** Mock `SentenceTransformer.encode` to return a dummy vector (size 384).  
  - **Mocking Outlook:** Use 1-based indexing for collections.  
  - **Mocking extract_msg:** Use `side_effect` for sequential calls to `openMsg`.  
- **File Handling:** Files opened with context managers MUST be closed before they are moved, renamed, or deleted (Windows `[WinError 32]`).  

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

## Appointment Management Rules  
- **Timezone:** All appointments must be created in the `Europe/Berlin` timezone.  
- **Default Duration:** If not otherwise specified by the student, the default duration for appointments is **30 minutes**.  
- **Body Text:** The body of the calendar appointment MUST follow the format: "Terminbestätigung auf Basis Ihrer Mail vom DD.MM.YY".  
- **Tool Usage:** Always use the `manage_calendar_appointment` tool for bookings. Pass the date of the student's email as `original_mail_date`.  
- **ANHANG: JA:** This output in the agent's response is a control flag for the script to attach relevant info files (like PO-Wechsel PDFs) to the EMAIL draft. It does not affect the calendar entry.  

## Email Anonymization & Cloud LLMs
When using cloud-based LLMs (e.g., OpenAI via the `--use-cloud` flag), student data MUST be anonymized before being sent to the cloud.  
- **Requirement:** Use the local Ollama model (via `Anonymizer`) to replace student names and emails with "Max Mustermann" and "max.mustermann@student.th-koeln.de".  
- **Bi-directional:** The agent must de-anonymize data locally (using `Anonymizer.deanonymize_text` or `deanonymize_args`) before executing tools like `manage_calendar_appointment` or creating Outlook drafts. This ensures that sensitive internal systems always receive the correct student information while external cloud providers only see placeholders.  
- **Trigger:** Anonymization is automatically handled within `Agent.chat` and `MCPAgent.chat` when `use_cloud` is enabled.  

# Configuration System  
- Loads from `config/user.yaml` and `.env`/`secrets.env`.  
- Access via `get_config().user.name`, etc.  

## Wichtige Hinweise zur Implementierung

### 1. Embedding-Modelle
In `mcp_university/classifier/engine.py` und `mcp_university/retrieval/index.py` MUSS nach dem erfolgreichen lokalen Laden des SentenceTransformer-Modells (mit `local_files_only=True`) zwingend folgende Log-Ausgabe erfolgen:
`logger.info(f"ERFOLG: Modell {self.embedding_model_name} wurde LOKAL geladen.")`
Dies dient der Verifikation, dass keine unnötigen Netzwerk-Anfragen gestellt werden.

### 2. Terminbuchung (Appointment Booking)
In `process_sorted_emails.py` muss bei der Verarbeitung des `APPOINTMENT_BOOKED` Signals zwingend `agent.last_appointment_info` geprüft werden. Dies verhindert, dass der Agent eine erfolgreiche Buchung halluziniert, ohne das entsprechende Tool tatsächlich aufgerufen zu haben.

In `mcp_university/agent/engine.py` sollten im `_tool_manage_calendar_appointment` wichtige Zwischenschritte (Konto gefunden, Kalender gefunden, Entwurf erstellt) mit `ERFOLG:` geloggt werden, um die Fehlersuche zu erleichtern.
