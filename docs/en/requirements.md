# System Requirements

This document defines the functional and non-functional requirements for the **MCP University Memory System**. It serves as the foundation for development, quality assurance, and system architecture.

---

## 1. Introduction and System Overview

The **MCP University Memory System** is a locally-running, agentic knowledge and memory system designed for academic and research workflows (specifically optimized for TH Köln). It automates email processing, manages student data, facilitates semantic search within local files, and automatically generates email drafts and calendar entries.

The system follows a strict **offline-first approach** to guarantee the privacy and protection of personal data belonging to students and faculty.

---

## 2. Functional Requirements (FR)

### FR-1: Crawler & Filesystem Scanning  
*   **FR-1.1 (Recursive Scan):** The system must recursively scan directories and automatically detect new, modified, or deleted files (PDF, DOCX, MSG, EML, etc.).  
*   **FR-1.2 (Change Detection):** File changes must be detected by comparing SHA-256 hashes against values stored in the metadata database.  
*   **FR-1.3 (Real-time Monitoring):** The system must provide a watcher module (`mcp-uni watch`) to monitor the filesystem in real time and index changes immediately.  
*   **FR-1.4 (Database Cleanup):** When a file is deleted from the filesystem, its corresponding metadata records must be automatically removed from the central database.  
*   **FR-1.5 (Folder Summarization):** The system must generate hierarchical summaries from file level up to the root folder level and store them in the database.  

### FR-2: Document & Email Parsing  
*   **FR-2.1 (PDF Parsing):** PDFs must be parsed using `Docling` as the primary engine (with a simpler fallback parsing if Docling is not available).  
*   **FR-2.2 (Email Parsing):** The system must flawlessly parse Outlook emails in `.msg` format (via `extract-msg`) and `.eml` format.  
*   **FR-2.3 (Resource Constraints):** To prevent performance bottlenecks, only the first **3 pages** of a document shall be parsed/analyzed by default.  
*   **FR-2.4 (Warning Suppression):** Noise and non-critical warnings from third-party libraries (such as `extract-msg`) must be suppressed.  
*   **FR-2.5 (Signed Attachments):** During `.msg` file parsing, signed attachment objects (`SignedAttachment`) must be handled safely and without errors.  

### FR-3: Email Classification & Sorting  
*   **FR-3.1 (ML Models):** Emails must be automatically classified using XGBoost, RandomForest, or PyTorch-based Transformer models (e.g., MiniLM).  
*   **FR-3.2 (Input Formatting):** The model input format must exactly match the structure: `SUBJECT: <Subject> | ATTACHMENTS: <File1, ...> [SEP] <Email Body (anonymized)>`.  
*   **FR-3.3 (Class Remapping):** Classifications of the category `'Other'` must be automatically mapped to the standardized class `'Others'`.  
*   **FR-3.4 (Path Hierarchy):** Archived emails must be automatically relocated into a three-tier directory structure: `Semester / Last Name / (Inbox or SentItems)`.  
*   **FR-3.5 (Special Routing):** Email classes starting with `BA_` (Bachelor Thesis) or `MA_` (Master Thesis) must be sorted directly into `Semester/Inbox` or `Semester/SentItems`.  
*   **FR-3.6 (Name Extraction):** Determining a student's last name from email metadata must follow a strict hierarchical logic:  
    1.  Check for "on behalf of" ("im Auftrag von") headers.  
    2.  *Greedy Name Matching:* Cross-reference parts of the display name with the local-part of the email address. If a part of the display name is found in the local-part, it is identified as the last name (e.g., `Mustermann Max <mustermann@example.com>` -> "Mustermann").  
    3.  *Dot-Separated Fallback:* Split the local-part by dots (`.`) and inspect the segments from back to front (ignoring generic terms).  
    4.  *Generic Fallbacks:* Comma separation (`Lastname, Firstname`), last word of the display name, or uppercase letter detection.  
*   **FR-3.7 (Name Normalization):** Extracted names must be returned in *Title Case*. Umlauts must be normalized for directory paths (e.g., "Müller" -> "Mueller" for the filesystem), but the original name must be preserved in records.  
*   **FR-3.8 (GUI Visibility):** All sorted emails must be fully visible in the Gradio GUI (no hidden or collapsed rows by default).  

### FR-4: Hybrid Search & RAG Process  
*   **FR-4.1 (Hybrid Search):** The system must provide a hybrid search engine combining BM25 keyword search with Qdrant vector search.  
*   **FR-4.2 (Local Loading):** Embeddings and language models must be loaded locally by default (`local_files_only=True`). On successful load, the log entry `ERFOLG: Modell <Model Name> wurde LOKAL geladen.` must be emitted.  
*   **FR-4.3 (RAG Workflow):** The Retrieval-Augmented Generation (RAG) process must follow a multi-step workflow:  
    1.  Generate **3 precise search queries (questions)** using the LLM based on the email content.  
    2.  Retrieve relevant chunks from the class-specific vector database (e.g., `data/memory/<Class>`).  
    3.  Select the **top 3 unique chunks** based on similarity score.  
    4.  Inject these chunks as "additional context" into the prompt for response generation.  
*   **FR-4.4 (qmd Integration):** The system must optionally use the globally installed Node.js CLI `qmd` for query expansion and re-ranking. If `qmd` is missing, it must fall back to native Python search (Qdrant + BM25).  

### FR-5: Email Workflow Control & GUI  
*   **FR-5.1 (Gradio GUI):** The interface must be powered by Gradio, divided into two tabs:  
    *   *Tab 1 (Fast Sorting):* Bulk processing and archiving of already correctly classified emails.  
    *   *Tab 2 (Detail View):* Detailed analysis of a selected email with an AI summary (max. 2 sentences), context display, and action selection.  
*   **FR-5.2 (Action Suggestions):** Based on the email content and RAG context, the system must suggest one of six actions:  
    1.  *Write reply:* Generate draft based on topic and personas.  
    2.  *Reply with appointment suggestion:* Retrieve free slots from `free_slots.md` via `get_appointment_slots` and integrate them.  
    3.  *Book appointment directly:* Create a calendar entry upon receiving appointment confirmation emails.  
    4.  *Archive only:* Move the email directly to the archive without drafting a reply.  
    5.  *Task "Read Attachment" (Thesis submissions):* Automatic processing of final thesis submissions.  
    6.  *Colloquium appointment:* Special booking for final colloquium presentations.  
*   **FR-5.3 (Archiving Suggestion):** The system must automatically suggest the action "Archive only" for:  
    *   Emails older than the configured threshold (e.g., 6 months).  
    *   Emails located in the `SentItems` folder.  
    *   Emails that have already been replied to.  
*   **FR-5.4 (Attachment Handling in GUI):** The GUI must provide a checkbox for "Anhang speichern" (Save Attachment) in both Tab 1 and Tab 2. The selection state from Tab 1 must be preserved when switching to Tab 2.  
*   **FR-5.5 (Action "Read Attachment" - Automation):** When an email is classified as a final thesis submission, the following steps must be executed automatically:  
    1.  Save all attachments directly in the student's main folder (`Semester / Last Name /`).  
    2.  Create/update the `config.json` configuration file in the student's folder, including the PDF filename.  
    3.  Create an Outlook calendar reminder for **exactly 7 days after email receipt at 08:00 AM**.  
    4.  Automatically generate an Outlook reply draft confirming receipt.  
*   **FR-5.6 (Action "Colloquium Appointment" - Automation):**  
    1.  Create/update the `config.json` in the student's folder with presentation parameters (date, time, room, location type).  
    2.  Automatically book the colloquium in the Outlook calendar (duration fixed at 60 minutes) and export these details to the `config.json`.  

### FR-6: Person Profiles & PersonProfiler  
*   **FR-6.1 (Profile Generation):** The system must generate and update Markdown-based person profiles at `D:\Steckbriefe\<email>.md`.  
*   **FR-6.2 (Profile Content):** The profile must contain role, preferred honorific (Du/Sie), first contact, and relevant projects/theses.  
*   **FR-6.3 (Honorific Determination - Du/Sie):** The preferred honorific must be determined by analyzing the last 4 direct emails sent to the person and the last 4 received from them. Bulk/Sammelmails (e.g., "Hallo zusammen") must be ignored.  
*   **FR-6.4 (Performance Limits):** A maximum of the **100 newest emails** of a person may be analyzed when generating or updating a profile.  
*   **FR-6.5 (Incremental Updates):** When updating an existing profile, only emails newer than the modification date of the profile file shall be processed.  
*   **FR-6.6 (Tracking):** Processed emails must be tracked in the SQLite database `profiles_tracking.db`.  

### FR-7: Outlook VBA Macros  
*   **FR-7.1 (Data Export):** VBA macros must export emails to the `inbox` folder in the format `YYYYMMDD_HHMMSS - Subject.msg`.  
*   **FR-7.2 (Free Slots):** Free slots must be exported to a file named `free_slots.md`.  
*   **FR-7.3 (Outlook Error Avoidance):** To move items within Outlook, `target_folder.Items.Add(0)` must be used instead of `mail.Move()` to avoid specific VBA runtime errors.  
*   **FR-7.4 (Account Mapping):** The macros must be designed strictly for the account `daniel.gaida@th-koeln.de`.  

### FR-8: Model Context Protocol (MCP) Server  
*   **FR-8.1 (Server Start):** The system must provide an MCP server started via the CLI command `mcp-uni serve-mcp`.  
*   **FR-8.2 (Tools for Agents):** The server must expose the following tools to clients (e.g., Claude Desktop):  
    *   `search_documents`: Semantic search in documents.  
    *   `get_folder_summary`: Fetch aggregated folder information.  
    *   `get_student_context`: Full history and status of a student.  
    *   `generate_mail_reply`: Draft email based on context and skills.  
    *   `get_open_tasks`: Extract open tasks.  

### FR-9: Metadata, Knowledge Graph & TH Personal Graph  
*   **FR-9.1 (Database Separation):** The system must maintain two separate SQLite databases:  
    1.  `university.db`: File metadata, folder structures, student sync, and email conversations.  
    2.  `th_personal.db`: Organizational hierarchy, TH Köln staff, and module responsibilities.  
*   **FR-9.2 (Ontology Learner):** The system must automatically learn name-email pairs and module variations (e.g., "KI" vs. "Künstliche Intelligenz") and store them in the `aliases` table.  
*   **FR-9.3 (Edge Priorities):** Knowledge graph relationships must have priorities defined in `ontology.yaml`. Higher-priority relationships must overwrite lower-priority ones.  
*   **FR-9.4 (TH Personal Crawler):** A crawler script must scrape the TH Köln directory and create people and organization nodes in `th_personal.db`.  
*   **FR-9.5 (MOCOGI Extraction):** Degree programs, examination regulations, modules, and examiners must be extracted via the MOCOGI API, mapped using fuzzy matching to persons, and saved in `th_personal.db`.  
*   **FR-9.6 (Visualization):** The knowledge graph must be visualizable as an interactive HTML file (`knowledge_graph.html`).  

### FR-10: Anonymization & Privacy  
*   **FR-10.1 (Local Anonymization):** Personally Identifiable Information (PII) like student names must be anonymized locally (using local Ollama models via `Anonymizer`) before sending to optional Cloud LLMs.  
*   **FR-10.2 (Bidirectionality):** Anonymized data must be de-anonymized locally before executing local actions/tools.  

---

## 3. Non-Functional Requirements (NFR)

### NFR-1: Security & Privacy  
*   **NFR-1.1 (Local Execution):** All core components (Ollama LLM, Qdrant vector database, SQLite metadata, parsing, indexing) must run completely offline without an active internet connection.  
*   **NFR-1.2 (Data Isolation):** Student data, emails, and notes must never leave the local machine unencrypted or unanonymized.  

### NFR-2: Performance & Scalability  
*   **NFR-2.1 (Parser Limits):** To conserve RAM and CPU, document parsing (PDF, DOCX) must be strictly limited to the first **3 pages**.  
*   **NFR-2.2 (LLM Context Window Protection):** A maximum of the **100 newest emails** of a person may be analyzed during profile generation/updates to protect the context window limit of local LLMs.  
*   **NFR-2.3 (GUI Response Times):** Search results in the email search GUI must return in under 1 second by utilizing an indexing cache (`data/cache/email_search_cache.json`).  

### NFR-3: Reliability & Robustness  
*   **NFR-3.1 (Windows File Locks):** Because the system runs on Windows, files opened in code (e.g., via context managers) must be closed before moving, renaming, or deleting them to prevent `[WinError 32]`.  
*   **NFR-3.2 (Crawler Fault Tolerance):** Folder summarization must feature a one-time retry logic with detailed debug output (`.folder_summary_items_debug.txt`).  
*   **NFR-3.3 (Summary Verification):** After writing folder summaries, the system must verify the physical existence of the generated files.  
*   **NFR-3.4 (Past-Date Appointments):** Appointments with dates in the past must be automatically detected, skipped during calendar booking, and directly archived as `Archiviert (Termin in Vergangenheit)`.  

### NFR-4: Compatibility & Platform Support  
*   **NFR-4.1 (Platforms):** The system must run flawlessly on Windows 10/11, macOS (Intel and Apple Silicon), and Linux.  
*   **NFR-4.2 (Python Compatibility):** The system must be compatible with Python 3.10+. F-strings must not contain nested quotes of the same type to maintain Python 3.10 compatibility.  
*   **NFR-4.3 (Environment Support):** The project must natively support both standard virtual environments (`venv`) and Anaconda environments (`environment.yml`).  
*   **NFR-4.4 (GPU Support):** The system must optionally support NVIDIA GPUs via CUDA and Apple Silicon GPUs via MPS to accelerate transformer models.  
*   **NFR-4.5 (Timezone Locking):** All calendar appointments must be booked in the `Europe/Berlin` timezone. Default appointment duration is 30 minutes (colloquia excluded: 60 minutes).  

### NFR-5: Maintainability & Quality Standards  
*   **NFR-5.1 (Google-Style Docstrings):** All classes, methods, and functions must be fully documented using Google-Style Docstrings. These must include `Args:` and `Returns:` sections when applicable.  
*   **NFR-5.2 (Docstring Coverage):** Docstring coverage (verified using `interrogate`) must be maintained at **99%** or above.  
*   **NFR-5.3 (Typing):** Explicit Python type hints are mandatory for all function parameters and return types (including `-> None` for `__init__`).  
*   **NFR-5.4 (Variable Names):** Highly descriptive and self-explanatory variable names must be used (e.g., `local_part` instead of `lp`, `display_name` instead of `dn`). Abbreviations must be avoided.  
*   **NFR-5.5 (Preservation Policy):** Existing comments, docstrings, and logging statements must never be deleted unless they are proven incorrect or completely obsolete.  
*   **NFR-5.6 (Code Formatting & Linting):** Code must be ruff-compliant. Run `ruff check . --fix` before committing. Violations of error classes E741, E402, F401, F541 are disallowed.  
*   **NFR-5.7 (Detailed Logging):** Every email processing step must be logged densely and traceably in `process_emails.log`.  
*   **NFR-5.8 (Test Coverage):** The system must have a comprehensive test suite (pytest) with at least 95% test coverage, respecting these mocking requirements:  
    *   `SentenceTransformer.encode` must be mocked to return a dummy vector of size 384.  
    *   Outlook collections must use 1-based indexing.  
    *   `extract_msg` must use `side_effect` for sequential `openMsg` calls.  

### NFR-6: Internationalization & Documentation  
*   **NFR-6.1 (Bilingual Documentation):** The documentation must be bilingual (German/English) using the MkDocs ecosystem, `mkdocs-static-i18n` plugin, and `docs_structure: folder` configuration.  
*   **NFR-6.2 (Authoritative Language):** German is the authoritative and leading language for all user manuals, interfaces, and LLM instructions. English serves as a full translation.  
*   **NFR-6.3 (Relative Paths):** All links and images in Markdown documents must use relative paths (e.g., `../assets/`) to ensure the portability of the built documentation.  
*   **NFR-6.4 (Clean-up Policy):** Before any release or submission, all temporary development artifacts (`__pycache__`, `.pytest_cache`, `.coverage`, `htmlcov`, `*.log`, temporary test files like `test.docx`, build directories `dist/`, `build/` and `*.egg-info`) must be completely cleaned up.  
