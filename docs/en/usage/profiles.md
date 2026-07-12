# Personnel Database & Person Profiles

This module enables the management of the university personnel database (`th_personal.db`) as well as the automated creation and updating of detailed person profiles (Steckbriefe) based on email history and the knowledge graph.

---

## 1. The Personnel Database (`th_personal.db`)

The personnel database forms the basis for understanding the organizational structure and responsibilities of TH Köln within the system. It contains information about people (faculty, staff), modules, examination regulations (POs), and faculties/institutes.

### Scripts for Creating and Updating the Database

The database `th_personal.db` is populated using two central scripts from the `th_personal_graph` package:

1. **TH Personal Crawler (`python -m th_personal_graph.scripts.crawl_th_koeln_persons`):**  
   Crawls the official TH Köln directory for names, contact information, faculties, institutes, and academic degrees. It stores them in the local SQLite database `th_personal.db` as well as Markdown files in `data/th_koeln/`.

   *Example Command:*
   ```bash
   python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
   ```

2. **MOCOGI Extractor (`python -m th_personal_graph.scripts.extract_mocogi_data`):**  
   Fetches study programs, exam regulations, and module descriptions via the MOCOGI API. It extracts module coordinators, first/second examiners, and links them automatically with person nodes in `th_personal.db` using robust fuzzy name matching.

   *Example Command:*
   ```bash
   python -m th_personal_graph.scripts.extract_mocogi_data
   ```

### Visualizing the Personnel Database

To interactively explore the imported relationships and data structures, use the visualization script:

*   **Knowledge Graph Visualization (`python -m th_personal_graph.scripts.visualize_knowledge_graph`):**  
    Generates an interactive 2D network visualization of the graph as an HTML file (`knowledge_graph.html`). You can filter nodes or explore the entire graph in your browser.

    *Example Command (filtered by name):*
    ```bash
    python -m th_personal_graph.scripts.visualize_knowledge_graph --filter "Informatik" "Mustermann"
    ```

Detailed descriptions of these processes can be found in the **[TH Personal Graph (Package)](../packages/th-personal-graph/index.md)** section.

---

## 2. Person Profiles (Steckbriefe)

A person profile summarizes important, individual information about a person. These profiles are dynamically generated and serve as valuable context for the LLM when automatically drafting email replies.

### Content of a Profile
A profile in Markdown format summarizes:  
- **Role:** Students, faculty, etc.  
- **Preferred Salutation:** (Du or Sie)  
- **First Contact:** Date and context.  
- **Relevant Projects, Theses, or Tasks:** Assignment based on email history and the graph.  

### Determining Salutation (Du/Sie)
The preferred salutation is intelligently determined from the past email history:  
- The last 4 emails sent directly from the user to the person and vice versa are analyzed.  
- Bulk emails (e.g., beginning with "Liebe Kolleg*innen" or "Hallo zusammen") are ignored to prevent incorrect determinations.  
- If no direct emails are found, the system falls back to the latest available individual emails.  

### Creation and Update

*   **Automatic Creation:** If no profile exists for an email address, it is automatically generated in the background when attempting to reply to an email. All available emails of the person (up to the 100 newest for optimal performance) are analyzed.  
*   **Dynamic Updates:** The system tracks which emails have already been processed in `profiles_tracking.db`. When new emails arrive, the profile is updated by the LLM by seamlessly integrating the new details into the existing profile.  

### Manual Management via the CLI

You can also manage profiles manually via the CLI:

```bash
# Update all existing profiles
mcp-uni profiles update

# Update a specific profile
mcp-uni profiles update --email student@example.com
```

### File Paths  
- **Profile Files:** Saved under the path defined in the configuration (e.g., `D:\Steckbriefe\`).  
- **Tracking Database:** `data/profiles_tracking.db`.  
