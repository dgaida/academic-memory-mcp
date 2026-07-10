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
*   **Automatic Suggestions:** Suitable senders or terms are suggested as you type.  
*   **Separate Views:** Results are clearly separated into **Inbox** and **Sent Items (SentItems)**.  
*   **Preview:** Click an email in the list to view an HTML preview of the content directly in the GUI.  
*   **Integration:** Open the found email with a single click directly in Outlook or jump to the corresponding folder in Windows Explorer.  

## How it works

The search is based on a local JSON index (`data/cache/email_search_cache.json`). The index is updated automatically upon the first start or when new emails are moved into the configured paths (see [Configuration](../configuration.md)).

This enables an extremely high-performance search because the file system does not have to be scanned for every single query.

### Intelligent Association and SentItems Detection

A particular challenge when searching for sent emails is that the sender (`From`) of these emails is always the user themselves (e.g., "Daniel Gaida"). If you search for a student's name (e.g., "Mustermann"), a search solely based on the sender would not find these emails.

The quick search solves this as follows:  
1. **Recipient Indexing:** When indexing emails, the recipients (`To`) are also captured with their name and email address and saved in the index.  
2. **Path-Based Search:** The search query is additionally matched against the entire file path (which contains the student's folder name).  
3. **Extended Matching:** An email is considered a match if the search term occurs in the subject, sender, recipient, filename, or the entire file path. This reliably finds sent emails to students.  

Determining whether an email is in the **Inbox** or **SentItems** is done based on path segments. Folders with names like `SentItems`, `Sent Items`, `Gesendete Elemente`, `Gesendete Objekte`, or `Sent` (case-insensitive) are automatically classified as **SentItems**.

### High-Performance Suggestions Cache

To avoid delays when entering search terms, the GUI uses a dedicated, persisted suggestions cache (`data/cache/suggestions_cache.json`).

* **Initialization:** Upon the first start, the cache is pre-populated with a list of standard terms common in a university context (e.g., *Informatik*, *Bachelorarbeit*, *Masterarbeit*, *Kolloquium*, *Prüfung*, etc.) as well as all names and email addresses (of senders and recipients) present in the index.  
* **Sub-Millisecond Responses:** Autocomplete searches directly inside this optimized in-memory set, enabling a virtually lag-free display of suggestions.  
* **Prefix Prioritization:** Search terms that start with the input are prioritized over terms that contain the input at another position.  
* **Dynamic Extension:** As soon as you perform a new search using the "Search" button, the entered search term is automatically added to the cache and saved permanently. This term will be immediately available in future searches.  
