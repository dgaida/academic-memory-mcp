# Email Search (Email Search GUI)

The Email Quick Search allows you to search through thousands of archived emails in seconds. It is particularly useful for quickly finding context on a request without having to open Outlook.

## Starting the GUI

Run the following script:

```bash
python scripts/email_search_gui.py
```

The GUI will automatically open in your default browser.

## Features

*   **Quick Search:** Search by names, email addresses, subject lines, or filenames.  
*   **Fuzzy Search (Fault-Tolerant):** Finds emails even when hyphens, spaces, or special characters are missing or entered differently in the search term (e.g., searching for "Campus IT" will find "support@campus-it.th-koeln.de").  
*   **Automatic Suggestions:** Suitable senders or terms are suggested as you type (also fault-tolerant).  
*   **Separate Views:** Results are clearly separated into **Inbox** and **Sent Items (SentItems)**.  
*   **Preview:** Click an email in the list to view an HTML preview of the content directly in the GUI.  
*   **Integration:** Open the found email with a single click directly in Outlook or jump to the corresponding folder in Windows Explorer.  

## How it works

The email quick search relies on a two-tier caching system consisting of two local JSON files in the `data/cache/` directory.

### 1. The Main Search Index (`data/cache/email_search_cache.json`)

This index stores all indexed emails as a JSON list of objects. The source data is extracted from `.msg` and `.eml` files located in the directories defined in the following configuration files:  
*   `config/classifier_paths.yaml` (or `config/classifier_paths.yaml.example` as a fallback): Maps email classes under `class_paths` (e.g., `BachelorThesis`, `MasterThesis`, `PraxisProjekt` etc.) to their target paths.  
*   `config/train_test_folders.yaml`: Defines the `train_path` and `test_path`.  

The cache is automatically updated upon the first start or when new email files are detected in these paths. Each object in the JSON array of `email_search_cache.json` has the following precise JSON keys/attributes:

*   `subject`: The subject line of the email (String).  
*   `from`: The email address of the sender (String).  
*   `from_name`: The display name of the sender (String).  
*   `to`: A list of recipients. Each item in this list is either:  
    *   A JSON object with the fields:  
        *   `to[].name`: The display name of the recipient.  
        *   `to[].email`: The email address of the recipient.  
    *   Or directly a String (e.g. a plain email address).  
*   `date`: The date of the email in ISO format (String).  
*   `path`: The absolute file path to the original email file on disk (String).  
*   `filename`: The filename of the email (String).  
*   `folder`: The classification of the folder (String, either `"Inbox"` or `"SentItems"`), determined by matching the path segments.  

This enables an extremely high-performance search because the file system does not have to be scanned for every single query.

### Intelligent Association and SentItems Detection

A particular challenge when searching for sent emails is that the sender (`From`) of these emails is always the user themselves (e.g., "Daniel Gaida"). If you search for a student's name (e.g., "Mustermann"), a search solely based on the sender would not find these emails.

The quick search solves this as follows:  
1. **Recipient Indexing:** When indexing emails, the recipients (`To`) are also captured with their name and email address and saved in the index.  
2. **Path-Based Search:** The search query is additionally matched against the entire file path (which contains the student's folder name).  
3. **Extended Matching:** An email is considered a match if the search term occurs in the subject, sender, recipient, filename, or the entire file path. This reliably finds sent emails to students.  

### Fuzzy Search (Fault-Tolerant Search)

To make searching as simple and flexible as possible, the quick search utilizes a fault-tolerant fuzzy matching logic. This is particularly useful for search terms containing hyphens, spaces, or special characters:

*   **Normalization:** Both the entered search query and the indexed email fields (subject, sender name, sender email, recipient name, recipient email, filename, file path) are normalized for matching. During normalization, all spaces, hyphens, and other special characters are completely removed, and the text is converted to lowercase.  
*   **Example:** Searching for `"Campus IT"` or `"campusit"` normalizes to `"campusit"`. This allows the search to successfully find the email address `"support@campus-it.th-koeln.de"` (which normalizes to `"supportcampusitthkoelnde"`, containing `"campusit"`).  
*   **Suggestions:** The suggestions cache also leverages this normalization, ensuring that relevant suggestions (such as `Campus IT Support`) appear accurately in the dropdown even when the user's input is imprecise.  

Determining whether an email is in the **Inbox** or **SentItems** is done based on path segments. Folders with names like `SentItems`, `Sent Items`, `Gesendete Elemente`, `Gesendete Objekte`, or `Sent` (case-insensitive) are automatically classified as **SentItems**.

### 2. The Suggestions Cache (`data/cache/suggestions_cache.json`)

To avoid delays when entering search terms, the GUI uses a dedicated, persisted suggestions cache (`data/cache/suggestions_cache.json`).

This file contains a flat JSON array of strings (e.g. `["Albert", "albert@test.com", "Informatik", ...]`), which is built and expanded as follows:

*   **Initialization:** Upon the first start, the suggestions cache is pre-populated with a list of standard university terms and is automatically extended using all names and email addresses extracted from the main index (`data/cache/email_search_cache.json`). Specifically, the following values/paths are collected:  
    *   The values of the `from_name` key (sender display name).  
    *   The values of the `from` key (sender email).  
    *   The values from the `to` recipient list:  
        *   The path/field `to[].name` (recipient name) of objects in the recipient list.  
        *   The path/field `to[].email` (recipient email) of objects in the recipient list.  
        *   Direct string elements in the recipient list.  
*   **Sub-Millisecond Responses:** Autocomplete searches directly inside this optimized in-memory set, enabling a virtually lag-free display of suggestions.  
*   **Prefix Prioritization:** Search terms that start with the input are prioritized over terms that contain the input at another position.  
*   **Dynamic Extension:** As soon as you perform a new search using the "Search" button in the GUI, the entered search term (if it is at least 2 characters long) is automatically added to the suggestions list and saved permanently to `suggestions_cache.json`. This term will be immediately available in future searches.  
