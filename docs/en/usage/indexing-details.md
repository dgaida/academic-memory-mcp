# Indexing in Detail

This section describes precisely what happens when the `mcp-uni index` command is executed.

## Process Workflow

Indexing takes place in several phases:

1.  **Initialization:**  
    - Configuration is loaded from `config/folders.yaml`, `config/user.yaml`, and `config/models.yaml`.  
    - Connections to the SQLite metadata database (`data/metadata/university.db`) and the Qdrant vector index (`data/indexes/qdrant`) are established.  
    - The Parser Factory is initialized (supporting PDF, Docx, Text, Email).  

2.  **Crawling (Folder Scan):**  
    - The crawler recursively traverses all paths defined in `config/folders.yaml`.  
    - For each folder, it checks if it already exists in the database (`folders` table). If not, it is created.  
    - Integration with `qmd` (Quick Markdown): The crawler attempts to add folders as `qmd` collections to speed up file discovery.  

3.  **File Processing:**  
    - A SHA-256 hash is calculated for each file.  
    - The hash is compared with the entry in the `files` table.  
    - **Only new or changed files are processed.**  

4.  **Parsing & Extraction:**  
    - Depending on the file type, the appropriate parser is called:  
        - `PDFParser`: Uses `liteparse` (primary) or `docling` (fallback) for PDF/Docx.  
        - `MailParser`: Extracts metadata (From, To, Date) and text from `.eml` and `.msg`.  
        - `TextParser`: Reads plaintext from `.md`, `.txt`, `.py`, `.json`, etc.  

5.  **Summarization:**  
    - The extracted text is sent to the configured LLM (defaulting to Ollama).  
    - A structured Markdown summary is created.  

6.  **Special Case: Email Conversations:**  
    - If the crawler detects a structure with `Inbox` and `SentItems` subfolders, it groups emails by conversation partners.  
    - An aggregated summary of the entire communication with a person is created.  
    - This is saved as `.emails_summary.md` in the folder.

7.  **Special Case: Folder Summaries:**  
    - After all files in a folder have been processed, the LLM creates a summary of the entire folder content based on the individual summaries.  
    - This is saved as a hidden file `.<foldername>_summary.md` in the **parent directory**. This also applies to root folders (which are stored in the same directory as the folder itself).

8.  **Storage & Indexing:**  
    - **Metadata:** File paths, hashes, timestamps, and the Markdown summaries are stored in the SQLite database:
        - `files` table: Path, Hash, Mtime, Type, Folder ID.
        - `folders` table: Path, Parent ID, Hash (for emails), Timestamp.
        - `summaries` table: The actual Markdown summaries for files and folders.
    - **Vector Search:** The **summaries** (not the full text) are vectorized (defaulting to `BAAI/bge-m3`) and stored in the Qdrant index.  

## Example: Before and After Indexing

Suppose you have the following structure:
```text
Lectures/
├── AI/
│   ├── lecture1.pdf
│   └── script.txt
└── Math/
    └── analysis.pdf
```

After indexing, it looks like this:
```text
.Lectures_summary.md
Lectures/
├── .AI_summary.md
├── AI/
│   ├── lecture1.pdf
│   └── script.txt
├── .Math_summary.md
└── Math/
    └── analysis.pdf
```

### Example: Email Structures

**Case 1: Inbox only (Standard Processing)**
Before:
```text
Student_A/
└── Inbox/
    └── question.msg
```
After:
```text
.Student_A_summary.md
Student_A/
├── .Inbox_summary.md
└── Inbox/
    └── question.msg
```

**Case 2: SentItems only (Standard Processing)**
Before:
```text
Student_B/
└── SentItems/
    └── answer.msg
```
After:
```text
.Student_B_summary.md
Student_B/
├── .SentItems_summary.md
└── SentItems/
    └── answer.msg
```

**Case 3: Combined Email Conversation (Special Case)**
If both `Inbox` and `SentItems` are present, the crawler recognizes this as a conversation and creates a combined summary (`.emails_summary.md`). The individual folders then no longer receive their own `.Inbox_summary.md` files, as they are merged into the conversation.

Before:
```text
Student_C/
├── Inbox/
│   └── question.msg
└── SentItems/
    └── answer.msg
```
After:
```text
.Student_C_summary.md
Student_C/
├── .emails_summary.md
├── Inbox/
│   └── question.msg
└── SentItems/
    └── answer.msg
```

## Supported File Formats

| Status | Formats |
| :--- | :--- |
| **Supported** | `.pdf`, `.docx`, `.md`, `.txt`, `.eml`, `.msg`, `.py`, `.ipynb`, `.json`, `.html` |
| **Planned / Not Supported** | `.pptx`, `.xlsx`, `.csv`, Image formats (OCR required) |

**Note on Markdown files:** All `.md` files are indexed and summarized, unless they start with a dot (`.`) and end with `_summary.md`. These are skipped as system-internal summaries.

## Generated Files and Storage Locations

| Type | Location | Description |
| :--- | :--- | :--- |
| **SQLite DB** | `data/metadata/university.db` | Stores metadata, hashes, paths, and summaries. |
| **Vector Index** | `data/indexes/qdrant/` | Binary files of the Qdrant search index. |
| **Folder Summary** | `../.<foldername>_summary.md` | Hidden Markdown file in the parent directory. |
| **Email Summary** | `./.emails_summary.md` | Aggregated conversation history for emails. |
| **Logs** | `data/logs/mcp-university.log` | Detailed logging of the indexing process. |
| **Cache** | `data/cache/` | Temporary artifacts from the PDF parser. |

## State Verification

The command is idempotent. Upon subsequent execution, only files whose hash has changed since the last run are processed. Files deleted from the file system are also removed from the database during indexing.
