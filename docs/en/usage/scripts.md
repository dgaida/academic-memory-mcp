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
mcp-uni graph visualize
```
Alternatively, the script can be called directly:
```bash
python scripts/visualize_knowledge_graph.py
```
The output is generated in `knowledge_graph.html`.

Supports the `--filter <name>` parameter (or `-f` in the CLI) to restrict the graph to a specific node and its context. This includes all "parent structures" (incoming edges, e.g., a person's institute or faculty) as well as all subgraphs originating from those structures (outgoing edges, e.g., all members of that institute or the person's modules).

### TH Köln Person Crawler
Crawls the TH Köln personnel directory for names, emails, faculties, and institutes.
```bash
python scripts/crawl_th_koeln_persons.py A B C

Supports filters by faculty or institution:
```bash
python scripts/crawl_th_koeln_persons.py --institution "Präsidium"
python scripts/crawl_th_koeln_persons.py --faculty "Informatik und Ingenieurwissenschaften"
```

Use `--list-institutions` or `--list-faculties` to see all available options. For a full crawl of all areas:
```bash
python scripts/crawl_th_koeln_persons.py --crawl-all both
```
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
