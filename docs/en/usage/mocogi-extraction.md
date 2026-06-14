# MOCOGI Data Extraction

This script allows exporting module information from the TH Köln MOCOGI API into a structured Markdown file.

## Purpose
The script `scripts/extract_mocogi_data.py` iterates through all active study programs and their examination regulations (POs). For each module, the following information is extracted:  
* Module Name  
* Module Coordinator  
* First Examiner  
* Second Examiner  

The data is saved in tabular form grouped by study program and PO in the file `mocogi_modules.md`.

## Prerequisites  
* A valid `MOCOGI_API_TOKEN` must be stored in a `.env` or `secrets.env` file in the root directory or the `config/` folder.  

## Usage
Run the script from the project's root directory:

```bash
PYTHONPATH=. python3 scripts/extract_mocogi_data.py
```

## Output Format
The generated file `mocogi_modules.md` follows this schema:

```markdown
# MOCOGI Module Overview

## [Study Program Name]

### PO [Version]

| Module Name | Module Coordinator | First Examiner | Second Examiner |
| :--- | :--- | :--- | :--- |
| Algorithmics | John Doe | John Doe | Jane Doe |
...
```
