# Helper Scripts

The system includes various useful scripts in the `scripts/` folder for preparing and managing your data.

## Directory Cleanup

### Remove Empty Folders
Recursively deletes all empty folders in a directory.
```bash
python scripts/remove_empty_folders.py /path/to/data
```

### Flatten Directory
Flattens a folder structure by moving all files to the root directory (including automatic name collision checking).
```bash
python scripts/flatten_directory.py /path/to/data
```

## Knowledge Graph & Persons

### Visualize Knowledge Graph
Generates an interactive HTML visualization of the knowledge graph.
```bash
python scripts/visualize_knowledge_graph.py
```
The output is generated in `knowledge_graph.html`.

### TH Köln Person Crawler
Crawls the TH Köln personnel directory for names, emails, faculties, and institutes.
```bash
python scripts/crawl_th_koeln_persons.py A B C
```
Supports multiple initial characters as arguments.

### Create Person Profiles
Manually creates a profile (Steckbrief) for a specific email address based on existing emails.
```bash
python scripts/create_person_profiles.py student@smail.th-koeln.de
```

### MOCOGI Data Extraction
Extracts module information (coordinators, examiners) from the MOCOGI API and links them in the knowledge graph.
```bash
python scripts/extract_mocogi_data.py
```

## Lectures & Teaching

### Summarize Lecture Slides
Searches for PDFs in a folder and generates compact Markdown summaries. Skips files that have already been processed (mtime check).
```bash
python scripts/summarize_lectures.py /path/to/lectures
```
Primarily uses `liteparse` with an LLM fallback on failure.
