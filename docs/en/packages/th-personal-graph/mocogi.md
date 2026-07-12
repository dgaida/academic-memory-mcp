# MOCOGI Data Extraction

This page describes the data extraction from the MOCOGI API of TH Köln and its integration into the `th_personal.db`.

## Purpose
The script `extract_mocogi_data.py` (invoked as an executable module `python -m th_personal_graph.scripts.extract_mocogi_data`) iterates through all active study programs and their examination regulations (POs). For each module, the following information is extracted:
* Module Name
* Module Coordinator (full names)
* First Examiner
* Second Examiner

The data is saved in tabular form grouped by study program and PO in the file `data/mocogi_modules.md`.

## Prerequisites
* A valid `MOCOGI_API_TOKEN` must be stored in a `.env` or `secrets.env` file in the root directory or the `config/` folder.

## Usage
Run the script from the project's root directory:

```bash
python -m th_personal_graph.scripts.extract_mocogi_data
```

## Output Format
The generated file `data/mocogi_modules.md` follows this schema:

```markdown
# MOCOGI Module Overview

## [Study Program Name]

### PO [Version]

| Module Name | Module Coordinator (full names) | First Examiner | Second Examiner |
| :--- | :--- | :--- | :--- |
| Algorithmics | John Doe | John Doe | Jane Doe |
...
```

---

## Integration into the Knowledge Graph
The script automatically integrates the extracted data into the SQLite-based Knowledge Graph of the personnel database (`th_personal.db`).

### Created Nodes and Edges
For each extracted record, the following entities are created or updated in the graph:

- **Nodes:**
    - `Study Program` (Studiengang): The name of the study program (e.g., "Informatik").
    - `Examination Regulation` (Prüfungsordnung): The specific PO version (e.g., "Informatik (PO 2024)").
    - `Module`: The individual subject (e.g., "Algorithmics").
- **Edges (Relationships):**
    - `is element of` (ist Element von): Links modules to examination regulations, and examination regulations to study programs.
    - `is module coordinator` (ist Modulverantwortlicher): Links a person to a module.
    - `is first examiner` / `is second examiner` (ist Erstprüfer / ist Zweitprüfer): Links examiners to modules.

### Study Program Director
A special process identifies persons marked as **Study Program Director** (based on data from the Person Crawler). If a match is found between the program director specified in the profile and an existing study program node, an edge of type `has study program director` (hat Studiengangsleitung) is automatically created.
