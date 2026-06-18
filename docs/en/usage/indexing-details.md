# Indexing Details and Database Structure

The MCP University system uses three specialized SQLite databases in the `data/metadata/` directory to manage information efficiently:

### 1. Metadata Database (`metadata.db`)
This database is the core for managing local files and student interactions.
- **Contents:**
    - Metadata for indexed files (paths, hashes, timestamps).
    - Summaries of folders and email conversations.
    - **Student Knowledge Graph:** Stores connections between students and the tool user (based on `user.yaml`). This includes roles like "Student", "User" and their interactions.
- **Classes:** `MetadataStore`

### 2. Knowledge Graph Database (`knowledge_graph.db`)
This database stores institutional data from TH Köln.
- **Contents:**
    - **Personnel:** Data about lecturers, staff, and professors (crawled via `crawl_th_koeln_persons.py`).
    - **Modules & Study Programs:** Information from the MOCOGI system (imported via `extract_mocogi_data.py`).
    - **Structure:** Mapping of faculties, institutes, and their relationships (e.g., "Professor teaches Module").
- **Classes:** `KnowledgeGraphStore`

### 3. Profile Database (`profiles.db`)
Manages the progress of profile creation.
- **Contents:** Tracks which emails have already been used to generate person profiles (`Steckbriefe/`) to allow incremental updates.
- **Classes:** `ProfileStore`
