# Nutzung der Skripte

Die Funktionalitäten des `th_personal_graph`-Packages werden über drei zentrale CLI-Skripte gesteuert. Diese sollten als ausführbare Module aufgerufen werden.

## 1. TH Personal Crawler
Crawlt das Personalverzeichnis der TH Köln, extrahiert Kontaktdaten, Fakultäten und akademische Grade und speichert sie in Markdown sowie in der lokalen SQLite-Datenbank `th_personal.db`.

Detaillierte Informationen zu den extrahierten Daten, den Quellen und allen verfügbaren Parametern finden Sie auf der Seite [TH Personal Crawler](crawler.md).

### Kurzes Beispiel
Ein vollständiger A-Z Crawl für das gesamte Personalverzeichnis kann wie folgt aufgerufen werden:
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons
```

---

## 2. MOCOGI Extraktor
Ruft über die MOCOGI-API Studiengänge, Prüfungsordnungen (PO) und Modulzuordnungen ab, liest die Verantwortlichkeiten aus (Modulverantwortung, Erst-/Zweitprüfer) und trägt sie in den Graphen von `th_personal.db` ein.

Weitere Details zur Funktionsweise, den Voraussetzungen und dem Ausgabeformat finden Sie auf der Seite [MOCOGI Extraktion](mocogi.md).

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
