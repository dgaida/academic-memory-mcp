# Helper Scripts

The system contains various useful scripts to assist with data preparation, migration, and database management.

---

## Directory Cleanup & Filesystem

### Remove Empty Folders
Recursively deletes all empty folders in a target directory.
```bash
python scripts/remove_empty_folders.py /path/to/data
```

### Flatten Directory
Flattens a folder structure by moving all files to the root directory (including automatic name collision checking).
```bash
python scripts/flatten_directory.py /path/to/data
```

---

## Email Management & Classification

### Fix Email Folder Structure
Migrates emails to the standard structure: `Semester/Lastname/Inbox|SentItems/`. This is particularly important for correct assignment within the system.
```bash
python scripts/fix_email_folders.py data/classifier_paths.yaml
```

**Options:**  
- `--dry-run`: Shows only detected errors without fixing them.  
- `--verify`: Recursively checks all emails in all subfolders for correct semester, name, and folder assignment.  

### Restructure Classifier Data
Restructures the classifier's training and test data to prepare it for training.
```bash
python scripts/restructure_classifier_data.py
```

### Replenish Datasets
Replenishes training and test data with old emails from original directories if a minimum count is not met.
```bash
python scripts/replenish_datasets.py -n 100
```

### Summarize Classes (Data Augmentation)
Analyzes training folders and creates LLM summaries for classes with limited data (<= 50 emails). These summaries include topics, style, and personnel identified from `th_personal.db`.
```bash
python scripts/summarize_classes.py
```

### Generate Synthetic Emails
Generates artificial emails based on the previously created class summaries to increase the size of the training dataset.
```bash
python scripts/generate_synthetic_emails.py
```

---

## Knowledge Graph & Personnel Database

These scripts have been refactored into the standalone `th_personal_graph` package and are invoked as executable modules.

- **TH Personnel Crawler (`python -m th_personal_graph.scripts.crawl_th_koeln_persons`):**  
  Crawls the TH Köln directory for contact details, faculties, and institutes.  
- **MOCOGI Data Extraction (`python -m th_personal_graph.scripts.extract_mocogi_data`):**  
  Extracts module information (coordinators, examiners) from the MOCOGI API and links them in the graph.  
- **Visualize Knowledge Graph (`python -m th_personal_graph.scripts.visualize_knowledge_graph`):**  
  Generates an interactive HTML visualization of the personnel database.

Detailed information on the usage and parameters of these scripts can be found on the **[Personnel Database & Person Profiles](profiles.md)** page as well as in the **[TH Personal Graph Package Documentation](../packages/th-personal-graph/index.md)**.

---

## Knowledge Base & Memory

### Index Memory (Crawler)
Indexes documents from the paths defined in the configuration into the vector database.
```bash
mcp-uni memory update
```
Or directly via the script:
```bash
python scripts/index_memory.py
```

### Summarize Lecture Slides
Searches for PDFs in a folder and generates compact Markdown summaries. Skips files that have already been processed.
```bash
python scripts/summarize_lectures.py /path/to/lectures
```

### Build Document Knowledge Graph
Builds the knowledge graph from extracted email summaries and other sources in `university.db`.
```bash
python scripts/build_knowledge_graph.py
```

---

## Appointments, Colloquia & Analytics

### Create Colloquium Configuration
Creates JSON configuration files for the `colloquium-protocol-creator`.
```bash
python scripts/create_colloquium_config.py "Candidate Name" --date "2023-10-27" --time "10:00" --location-type campus --room "R3.14"
```

### Visualize Embeddings
Creates a 2D visualization of email embeddings using t-SNE to analyze the separability of classes.
```bash
python scripts/visualize_embeddings.py
```
