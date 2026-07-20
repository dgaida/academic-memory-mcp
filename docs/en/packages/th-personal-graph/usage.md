# Script Usage

The features of the `th_personal_graph` package are controlled by three central CLI scripts. They should be invoked as executable modules.

## 1. TH Personal Crawler
Crawls the personnel directory of TH Köln, extracting contact details, faculties, and academic degrees. It stores the results as Markdown files and imports them into the local SQLite database `th_personal.db`.

Detailed information regarding the extracted data, sources, and all available parameters can be found on the [TH Personal Crawler](crawler.md) page.

### Short Example
A full A-Z crawl of the entire personnel directory can be executed with:
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons
```

---

## 2. MOCOGI Extractor
Fetches study programs, examination regulations (PO), and module assignments via the MOCOGI API, extracts responsibilities (module management, first/second examiners), and adds them to the graph in `th_personal.db`.

For more details on functionality, prerequisites, and output formats, see [MOCOGI Extraction](mocogi.md).

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
