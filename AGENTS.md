# AI Agent Instructions - MCP University

This file contains essential information for AI agents working on the **MCP University** (academic-memory-mcp) project.

## Project Overview
MCP University is an offline-first system for managing academic data (students, emails, theses, documents) using local LLMs. It provides automated classification, summarization, and RAG-based search.

### Core Components  
1. **Crawler (`mcp_university/crawler/`)**: Indexes the filesystem, detects changes (SHA-256), and manages metadata.  
   - **Retry Logic:** Folder summarization has a one-time retry with debug output (`.folder_summary_items_debug.txt`).  
   - **Persistence:** Verifies file existence after writing folder summaries.  
2. **Parser (`mcp_university/parser/`)**:  
   - Supports PDF (via `liteparse` > `docling`), DOCX, EML, and MSG (via `extract-msg`).  
   - Analyzes only the first 3 pages of documents to save resources.  
   - Suppresses noisy `extract-msg` warnings.  
   - **Attachment Handling:** `_parse_msg` safely handles `SignedAttachment` objects.  
3. **Classifier (`mcp_university/classifier/`)**:  
   - Classifies emails using XGBoost, RandomForest, or **Transformer** models.  
   - **Transformer Architecture:** Uses PyTorch-based `EmailTransformerClassifier` (e.g., MiniLM).  
   - **Input Formatting:** "SUBJECT: <Betreff> | ATTACHMENTS: <Datei1, ...> [SEP] <E-Mail-Body (anonymisiert)>".  
   - **Data Structure:** Training and test data are organized by class folders, each containing `Inbox` and `SentItems` subfolders.  
   - **Model Naming:** `resolve_model_path` automatically manages paths (e.g., `email_classifier_transformer.pkl`).  
   - **Special Logic:** Classes starting with `BA_` or `MA_` are stored directly in `Semester/Inbox` or `Semester/SentItems`.  
   - **Remapping:** Initial classifications of 'Other' are automatically remapped to 'Others'.  
4. **Retrieval (`mcp_university/retrieval/`)**:  
   - Hybrid search using Qdrant (vector) and BM25 (text).  
   - **Embedding Loading:** Always attempt `local_files_only=True` first. Log `ERFOLG: Modell ... wurde LOKAL geladen.` on success.  
5. **Summarizer (`mcp_university/summarizer/`)**:  
   - German-localized summarization and Q&A using Ollama via `LLMClientWrapper`.  
   - **Persona:** Daniel Gaida, Professor at TH Köln. Signature: Dependent on user name and honorific.  
   - **Person Profiler:** Generates Markdown profiles (`Steckbriefe`) in `D:\Steckbriefe\<email>.md` based on email history.  
6. **Metadata Store (`mcp_university/metadata/`)**:  
   - SQLite database for file metadata, student info, and folder summaries.  
   - **Knowledge Graph:** Implements ontology via an `aliases` table. Resolves names to canonical versions before upsert.  
   - **Ontology Learner:** Automates alias learning (Name-Email pairs, module variations).  
   - **Edge Priorities:** Configured in `ontology.yaml`, allows higher-priority relations to replace existing ones.  
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
- **Type Hints:** Explicit return type hints are mandatory (including `__init__`).  
- **Linting:** Run `ruff check . --fix` before submitting. No E741, E402, F401, F541.  
- **Coverage:** Minimum 95% docstring coverage (interrogate).  
- **Tests:** Use `pytest`. Run with `PYTHONPATH=.` from the root directory.  
  - **Mocking:** Mock `SentenceTransformer.encode` to return a dummy vector (size 384).  
  - **Mocking Outlook:** Use 1-based indexing for collections.  
  - **Mocking extract_msg:** Use `side_effect` for sequential calls to `openMsg`.  
- **File Handling:** Files opened with context managers MUST be closed before they are moved, renamed, or deleted (Windows `[WinError 32]`).  

### Documentation Skill  
- **MANDATORY:** Always use the [MkDocs Documentation Ecosystem Skill](https://github.com/dgaida/auto-version-action/blob/main/skills/SKILL_docs.md) when updating documentation, `README.md`, or MkDocs configurations.  
- **Structure:** Bilingual setup using `mkdocs-static-i18n` with `docs_structure: folder`.  
- **Paths:** Always use relative paths in Markdown (e.g., `../assets/...`).  

### Cleanup (MANDATORY)
Delete all temporary files before submission:  
- `__pycache__`, `.pytest_cache`, `.coverage`, `htmlcov`.  
- `*.log`, temporary test artifacts (`test.docx`, etc.).  
- Build artifacts (`dist/`, `build/`, `*.egg-info`).  

## Development Workflow  
1. **Environment:** `pip install -e .`  
2. **Conda Support:** The system officially supports Conda. Use `conda env create -f environment.yml` to set up the environment.  
3. **CLI Usage:** Use `mcp-uni` CLI for testing indexing and search.  
4. **Database Sync:** Use `mcp-uni db sync-students` after updating `students.yaml`.  
5. **Parsers:** When adding new parsers, update `mcp_university/parser/factory.py`.  
6. **MCP Server:** Keep the MCP server tools in `mcp_university/mcp_server/server.py` updated with new capabilities.  

## Outlook Macro Maintenance  
- Keep VBA documentation in Google-style (`''' Args:`, `''' Returns:`).  
- **Item Creation:** Use `target_folder.Items.Add(0)` instead of `mail.Move()` to avoid specific Outlook errors.  

## Appointment Management Rules  
- **Timezone:** All appointments must be created in the `Europe/Berlin` timezone.  
- **Default Duration:** 30 minutes.  
- **Tool Usage:** Always use the `manage_calendar_appointment` tool for bookings.  

## Final Submission Skill  
- Automatically triggers `manage_calendar_appointment` (reminder 7 days later at 08:00 AM) and `save_email_attachments` (to email's parent folder) BEFORE generating the final response.  

## Email Anonymization & Cloud LLMs
When using cloud-based LLMs (e.g., OpenAI via the `--use-cloud` flag), student data MUST be anonymized before being sent to the cloud.  
- **Requirement:** Use the local Ollama model (via `Anonymizer`) for replacement.  
- **Bi-directional:** The agent must de-anonymize data locally before executing tools.  

# Configuration System  
- Loads from `config/user.yaml` and `.env`/`secrets.env`.  

## Wichtige Hinweise zur Implementierung

### 1. Embedding-Modelle
In `mcp_university/classifier/engine.py` und `mcp_university/retrieval/index.py` MUSS nach dem erfolgreichen lokalen Laden des SentenceTransformer-Modells folgende Log-Ausgabe erfolgen:
`logger.info(f"ERFOLG: Modell {self.embedding_model_name} wurde LOKAL geladen.")`

### 2. Terminbuchung (Appointment Booking)
In `scripts/process_sorted_emails.py` muss bei der Verarbeitung des `APPOINTMENT_BOOKED` Signals zwingend `agent.last_appointment_info` geprüft werden.

### 3. F-Strings
Achte auf f-string Kompatibilität mit Python 3.10 (vermeide verschachtelte Anführungszeichen gleichen Typs).

## Personnel Crawling (TH Köln)
The script `scripts/crawl_th_koeln_persons.py` is used to fetch personnel data.  
- **Encoding:** When filtering by institution or faculty with umlauts (e.g., "Präsidium"), ensure the environment handles UTF-8 correctly. The script attempts to reconfigure `sys.stdout` and `sys.stdin` to UTF-8.  
- **Discovery:** Use `--list-institutions` and `--list-faculties` to see available filters.  
- **Bulk Crawling:** Use `--crawl-all [faculties|institutions|both]` to crawl all persons for the respective categories. This iterates through each category and saves separate Markdown files.  
- **Output:** The script ensures that the `data/` directory and subdirectories are created automatically.  

## Steckbrieferstellung (PersonProfiler)  
- Um die Performance zu gewährleisten und die Kontextgröße des LLM nicht zu sprengen, werden bei der Erstellung oder Aktualisierung eines Steckbriefs maximal die **100 neuesten E-Mails** einer Person berücksichtigt.  
- Bei der Aktualisierung eines bestehenden Steckbriefs werden nur E-Mails berücksichtigt, die neuer sind als die Steckbrief-Datei selbst (Dateidatum).  

## Email Handling Rules
### Email Parsing Rules (CRITICAL)  
- **Hierarchical Extraction:**  
  1. Handle "im Auftrag von" headers first.  
  2. **Greedy Name Matching:** Match display name parts against the local part of the email. If a part of the display name (like "Mustermann") is found within the local part (like "mustermann.max"), it is definitively the **lastname**.  
  3. **Dot-Separated Fallback:** If no display name match, use segments from dot-separated local parts.  
  4. **Validation:** Always return identified names in Title Case.  
- **Priority:** Direct 'To' recipients are prioritized over CC/BCC for folder organization in SentItems.  
- **Consistency:** Ensure `extract_lastname` and `extract_firstname` are used consistently across all sorting and processing scripts.  
- **Example:** "Mustermann Max <mustermann@example.com>" MUST result in lastname "Mustermann".  
  
- **SentItems:** Emails located in the `SentItems` folder must ALWAYS be archived and never require a reply action, regardless of their age or the overall conversation state.  

- **Memory Recording:** Always document significant logic changes (like the SentItems archiving rule) in AGENTS.md and relevant documentation folders to maintain project clarity.  

## Erweitere Coding Standards (Update)  
- **Variablennamen:** Verwende sprechende Variablennamen (z.B. `local_part` statt `lp`, `display_name` statt `dn`). Abkürzungen sind zu vermeiden.  
- **Erhaltung:** Bestehende Logging-Statements und Kommentare dürfen nicht gelöscht werden, es sei denn, sie sind nachweislich falsch oder obsolet. Es dürfen keine Kommentare gelöscht werden, die noch gültig sind.  
- **Formatierung:** Komplexe Ausdrücke wie `parser.add_argument()` oder verkettete Methodenaufrufe sollten für bessere Lesbarkeit auf neue Zeilen aufgeteilt werden.  
- **Dokumentation:** Die Docstring-Abdeckung (interrogate) muss dauerhaft bei mindestens 99% liegen. Alle neuen Tests und Skripte müssen vollständige Google-Style Docstrings enthalten.  

### GUI & Logging Rules (NEW)  
- **Visibility:** All sorted emails MUST be displayed in the Gradio GUI to ensure complete visibility. No emails should be hidden or collapsed unless explicitly requested.  
- **Logging:** Dense and detailed logging is required for all email processing steps. This includes logging each email being processed for the GUI and issuing warnings if expected files are missing.  

## Email Schnellsuche (Email Search GUI)  
- **Engine:** Die `EmailSearchEngine` in `mcp_university/utils/email_search.py` indiziert E-Mails aus den in `classifier_paths.yaml` und `train_test_folders.yaml` konfigurierten Pfaden.  
- **Cache:** Der Index wird in `data/cache/email_search_cache.json` zwischengespeichert, um schnelle Suchergebnisse zu ermöglichen.  
- **GUI:** Ein Gradio-Skript `scripts/email_search_gui.py` bietet eine Benutzeroberfläche mit Autovervollständigung, einer Liste der Suchergebnisse und einem E-Mail-Viewer.  
- **Funktionen:** E-Mails können direkt in Outlook oder im Datei-Explorer geöffnet werden.  

## Email Processing & GUI Rules (Update 2026-07)
- **Automatic Suggestions:** The system must automatically suggest "4) E-Mail nur archivieren" for emails that are older than the configured threshold or are located in the `SentItems` folder.
- **Attachment Handling:** The Gradio GUI (`scripts/process_sorted_emails.py`) must provide a checkbox for "Anhang speichern" on both Tab 1 and Tab 2. The selection state from Tab 1 must be preserved when moving a mail to Tab 2.
