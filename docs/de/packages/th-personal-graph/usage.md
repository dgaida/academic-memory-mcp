# Nutzung der Skripte

Die Funktionalitäten des `th_personal_graph`-Packages werden über drei zentrale CLI-Skripte gesteuert. Diese sollten als ausführbare Module aufgerufen werden.

## 1. TH Personal Crawler
Crawlt das Personalverzeichnis der TH Köln. Ergebnisse werden nach Fakultäten/Einrichtungen aufgeteilt als Markdown in `data/th_koeln/` abgelegt und in die SQLite-Datenbank importiert.

### Parameter & Beispiele  
- **A-Z Crawl für gesamte TH:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons
  ```
- **Spezifische Fakultät crawlen:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
  ```
- **Spezifische Einrichtung crawlen:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --institution "Campus IT"
  ```
- **Fakultäten/Einrichtungen auflisten:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-faculties
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-institutions
  ```
- **Datenbank aus vorhandenen Markdown-Dateien neu aufbauen:**  
  ```bash
  python -m th_personal_graph.scripts.crawl_th_koeln_persons --rebuild
  ```

---

## 2. MOCOGI Extraktor
Ruft über die MOCOGI-API Studiengänge, Prüfungsordnungen (PO) und Modulzuordnungen ab, liest die Verantwortlichkeiten aus (Modulverantwortung, Erst-/Zweitprüfer) und trägt sie in den Graphen von `th_personal.db` ein.

### Ausführung
```bash
python -m th_personal_graph.scripts.extract_mocogi_data
```
*Hinweis:* Das Skript benötigt einen gültigen API-Token in der Umgebungsvariable `MOCOGI_API_TOKEN` (bzw. `MOCOGI_API_KEY`).

---

## 3. Wissensgraph-Visualisierung
Erstellt eine interaktive Pyvis-Visualisierung des Wissensgraphen als HTML-Datei (`knowledge_graph.html` im Hauptverzeichnis).

### Parameter & Beispiele  
- **Gesamten Graphen visualisieren:**  
  ```bash
  python -m th_personal_graph.scripts.visualize_knowledge_graph
  ```
- **Nach bestimmten Knotennamen filtern:**  
  Erstellt einen Teilgraphen, der nur den gefilterten Knoten, seine Eltern-Strukturen und ausgehenden Pfade anzeigt.
  ```bash
  python -m th_personal_graph.scripts.visualize_knowledge_graph --filter "Informatik" "Mustermann"
  ```
