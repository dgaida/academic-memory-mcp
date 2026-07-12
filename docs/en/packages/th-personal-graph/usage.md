# Script Usage

The features of the `th_personal_graph` package are controlled by three central CLI scripts. They should be invoked as executable modules.

## 1. TH Personal Crawler
Crawls the personnel directory of TH Köln. Results are grouped by faculty/institution and stored as Markdown files in `data/th_koeln/`, and imported into the SQLite database `th_personal.db`.

### Parameters & Examples  
- **A-Z Crawl for the entire TH:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons
  ```
- **Crawl a specific faculty:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
  ```
- **Crawl a specific institution:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --institution "Campus IT"
  ```
- **List faculties/institutions:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-faculties
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-institutions
  ```
- **Rebuild database from existing Markdown files:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --rebuild
  ```

---

## 2. MOCOGI Extractor
Fetches study programs, examination regulations (PO), and module assignments via the MOCOGI API, extracts responsibilities (module management, first/second examiners), and adds them to the graph in `th_personal.db`.

### Execution
```bash
python -m th_personal_graph.scripts.extract_mocogi_data
```
*Note:* This script requires a valid API token in the `MOCOGI_API_TOKEN` (or `MOCOGI_API_KEY`) environment variable.

---

## 3. Knowledge Graph Visualization
Creates an interactive Pyvis visualization of the knowledge graph as an HTML file (`knowledge_graph.html` in the root folder).

### Parameters & Examples  
- **Visualize the entire graph:**  
  ```bash
  python -m th_personal_graph.scripts.visualize_knowledge_graph
  ```
- **Filter by specific node names:**  
  Creates a subgraph displaying only the filtered node, its parent structures, and outgoing paths.
  ```bash
  python -m th_personal_graph.scripts.visualize_knowledge_graph --filter "Informatik" "Mustermann"
  ```
