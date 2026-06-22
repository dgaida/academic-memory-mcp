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

## Email Management & Classification

### Fix Email Folder Structure
Migrates emails to the standard structure: `Semester/Lastname/Inbox|SentItems/`. This is particularly important for correct assignment within the system.
```bash
python scripts/fix_email_folders.py data/classifier_paths.yaml
```

### Restructure Classifier Data
Restructures the classifier's training and test data to prepare it for training.
```bash
python scripts/restructure_classifier_data.py
```

### Summarize Classes (Data Augmentation)
Analyzes training folders and creates LLM summaries for classes with limited data (<= 50 emails). These summaries include information about topics, style, and personnel identified from `th_personal.db`.
```bash
python scripts/summarize_classes.py
```

### Generate Synthetic Emails
Generates artificial emails based on the previously created class summaries to increase the size of the training dataset.
```bash
python scripts/generate_synthetic_emails.py
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

**Offline Support:**
The script is fully offline-capable, as all resources (vis-network) are embedded into the HTML file.

Supports the `--filter <name>` parameter (or `-f` in the CLI) to restrict the graph to a specific node and its context.

### Build Knowledge Graph
Builds the knowledge graph from extracted email summaries and other sources.
```bash
python scripts/build_knowledge_graph.py
```

### TH Köln Person Crawler
Crawls the TH Köln personnel directory for names, emails, faculties, and institutes.
```bash
python scripts/crawl_th_koeln_persons.py A B C
```

Supports filters by faculty or institution:
```bash
python scripts/crawl_th_koeln_persons.py --institution "Präsidium"
python scripts/crawl_th_koeln_persons.py --faculty "Informatik und Ingenieurwissenschaften"
```

Use `--list-institutions` or `--list-faculties` to see all available options. For a full crawl of all areas:
```bash
python scripts/crawl_th_koeln_persons.py --crawl-all both
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

## Knowledge Base & Memory

### Index Memory
Indexes documents from the paths defined in the configuration into the vector database.
```bash
mcp-uni memory update
```
Or directly:
```bash
python scripts/index_memory.py
```

## Appointments & Colloquia

### Appointment Management (GUI)
Opens a Gradio interface for managing weekly appointments, based on `data/appointments.md`.
```bash
python scripts/appointment_gui.py
```

### Create Colloquium Configuration
Creates JSON configuration files for the `colloquium-protocol-creator`.
```bash
python scripts/create_colloquium_config.py "Candidate Name" --date "2023-10-27" --time "10:00" --location-type campus --room "R3.14"
```

## Analysis & Visualization

### Visualize Embeddings
Creates a 2D visualization of email embeddings using t-SNE to analyze the separability of classes.
```bash
python scripts/visualize_embeddings.py
```

## Lectures & Teaching

### Summarize Lecture Slides
Searches for PDFs in a folder and generates compact Markdown summaries. Skips files that have already been processed.
```bash
python scripts/summarize_lectures.py /path/to/lectures
```
