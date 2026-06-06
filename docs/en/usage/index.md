# Usage

The MCP University Memory System provides various interfaces for interacting with your data.

## Command Line Interface (CLI)

The CLI is the primary way to manage the system and perform manual searches.

### Indexing (`index`)
This command scans all configured folders, creates summaries, and updates the index.
```bash
mcp-uni index
```

### Search (`search`)
Performs a quick query across the entire dataset.
```bash
mcp-uni search "Content of lecture 5"
```

### Watchdog (`watch`)
Starts a background process that reacts to file changes and updates the index in real-time.
```bash
mcp-uni watch
```

## Email Classification

The system includes a subpackage for the automated classification of student emails (e.g., Bachelor's thesis, internship project).

### Training the Model
To use the classifier, it must first be trained with example data. It expects a folder structure where each subfolder represents a class and contains the emails (.msg).

```bash
python3 mcp_university/classifier/train.py /path/to/training_data --mode combined --method xgboost
```

You can choose between `randomforest` and `xgboost` (default).

### Classifying an Email
After training, a single email file can be classified:

```bash
python3 mcp_university/classifier/predict.py /path/to/email.msg
```

The output contains the most likely class as well as the confidence and a detailed probability distribution.

### XAI Analysis (Interpretability)
To understand which words were particularly important for classification, the XAI analysis can be used. It uses SHAP values to calculate the influence of individual words on the prediction.

```bash
python3 mcp_university/classifier/xai_analysis.py --model-path data/email_classifier_xgboost_tfidf.pkl --test-data-path /path/to/test_data
```

The script analyzes up to 20 emails per class and returns the top 5 words that are most characteristic for the respective class.

### Email Sorting (Student Folders)
The most powerful script sorts emails not only by class, but also by semester and student (last name):

```bash
python3 mcp_university/classifier/sort_emails.py /source/folder --config config/class_paths.yaml --model data/email_classifier_xgboost_combined.pkl
```

It automatically detects:  
- **Semester:** Based on the email date (Summer/Winter semester).  
- **Student:** Extracts the last name from `smail.th-koeln.de` addresses or display names.  
- **Direction:** Sorts into `Inbox` or `SentItems` subfolders.  
- **Report:** Creates a `sorted_emails.md` with an overview of all moved emails.  

### Batch Classification
To automatically sort an entire folder of emails (classification only):
```bash
python3 mcp_university/classifier/classify_folder.py /source/folder --model data/email_classifier_xgboost_combined.pkl
```
This moves the emails into subfolders named after their predicted classes.

### Data Distribution Visualization
To visualize the distribution of emails per class (split by Inbox and SentItems), the following script can be used:

```bash
python3 mcp_university/classifier/plot_data_distribution.py --train-dir D:\\TH_Koeln\\MailTrainingData --test-dir D:\\TH_Koeln\\MailTestData --output-dir data
```

This generates two high-resolution PNG files in `data/`:  
- `train_data_distribution.png`  
- `test_data_distribution.png`  


## Database Management (`db`)

The `db` command group allows for direct management of metadata and the search index.

### Listing Content
You can list various entities in the database:

*   **Files:** `mcp-uni db list-files`  
*   **Folders:** `mcp-uni db list-folders`  
*   **Students:** `mcp-uni db list-students` (Note: Use `sync-students` to populate)  
*   **Summaries:** `mcp-uni db list-summaries`  
*   **Deadlines:** `mcp-uni db list-deadlines`  

### Student Synchronization (`sync-students`)
Populates the database from a `students.yaml`.
```bash
mcp-uni db sync-students
```

### Deleting Content
Entries can be deleted using their ID. Use the `--force` or `-f` option to skip the confirmation prompt.

*   **Delete Files:** `mcp-uni db delete-file <ID_1> <ID_2> ...`  
*   **Delete Folder:** `mcp-uni db delete-folder <ID>` (recursively removes all contained files)  
*   **Delete Student:** `mcp-uni db delete-student <ID>`  
*   **Delete Summary:** `mcp-uni db delete-summary <ID>`  
*   **Delete Deadline:** `mcp-uni db delete-deadline <ID>`  

## Model Context Protocol (MCP)

The most powerful way to use the system is via an MCP client (like Claude Desktop).

### Start Server
```bash
mcp-uni serve-mcp
```

### Available Tools  
*   `search_documents`: Semantic search in documents.  
*   `get_folder_summary`: Query aggregated folder information.  
*   `get_student_context`: Retrieve complete history and status of a student.  
*   `generate_mail_reply`: Draft an email based on the context.  
*   `get_open_tasks`: Extraction of TODOs from all documents.  

## Typical Workflows

### 1. Preparing for Office Hours
Ask your agent: "Give me the context for student Max Mustermann and show me his latest submissions."
The agent uses `get_student_context` and `search_documents` to provide you with a compact overview.

### 2. Answering Emails
Copy a student's email into the chat and use the `generate_mail_reply` tool. The system automatically takes the status of the thesis or open deadlines into account.

## Configuration

### Two-Stage Summarization
In `config/folders.yaml`, the `summarize_emails_individually` option (default: `false`) can be enabled. When set to `true`, email threads are summarized in two stages: first each email individually, then the entire conversation.

## Utility Scripts

The system includes useful scripts in the `scripts/` folder:

- **`remove_empty_folders.py`**: Recursively deletes all empty folders in a directory.  
- **`flatten_directory.py`**: Flattens a directory structure by moving all files to the root directory (includes name collision checks).  

## Feature Modeling (Email Classification)

The `EmailClassifier` supports three different modes for feature extraction:

1.  **TF-IDF (`tfidf`)**:  
    - **How it works:** Uses Term Frequency-Inverse Document Frequency to weigh the importance of keywords.  
    - **Pros:** Very fast, interpretable, effective for distinct terminology (e.g., "Bachelor Thesis", "Registration").  
    - **Cons:** Ignores word order and semantics (doesn't recognize synonyms).  

2.  **Embeddings (`embedding`)**:  
    - **How it works:** Uses `Sentence-Transformers` (default: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) to project text into a high-dimensional vector space.  
    - **Pros:** Captures semantic meaning. Recognizes similar concepts even if different words are used.  
    - **Cons:** More computationally expensive (requires model downloads), harder to interpret.  

3.  **Combined (`combined`)**:  
    - **How it works:** Concatenates TF-IDF vectors with embedding vectors.  
    - **Pros:** Combines keyword precision with deep semantic understanding. Usually yields the highest accuracy.  
    - **Cons:** Largest feature vectors, longer training time.  

### Model Naming
During training, the chosen method and mode are automatically appended to the filename (e.g., `email_classifier_transformer.pkl` or `email_classifier_xgboost_tfidf.pkl`) to prevent model confusion.
