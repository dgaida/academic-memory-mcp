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

## Knowledge Graph

### Visualize Knowledge Graph
Generates an interactive HTML visualization of the knowledge graph.
```bash
python scripts/visualize_knowledge_graph.py
```
The output is generated in `knowledge_graph.html`.

## Lectures & Teaching

### Summarize Lecture Slides
Searches for PDFs in a folder and generates compact Markdown summaries. Skips files that have already been processed.
```bash
python scripts/summarize_lectures.py /path/to/lectures
```
