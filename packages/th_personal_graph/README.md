# TH Personal und Modulzuordnungen Graph (th_personal_graph)

Dieses Package enthält alle Funktionalitäten und Skripte zur Extraktion, Speicherung und interaktiven Visualisierung des TH Köln Personal- und Modulzuordnungsgraphen.

## Features
- **TH Köln Personal-Crawler:** Durchsucht das TH-Personalverzeichnis und extrahiert Namen, E-Mails, Fakultäten, Institute und besondere Funktionen (z. B. DekanIn, PA-Vorsitz, Senat, Präsidium). Speichert Daten in Markdown-Dateien und der lokalen SQLite-Datenbank `th_personal.db`.
- **MOCOGI API Extraktor:** Extrahiert alle Studiengänge, Prüfungsordnungen (PO) sowie Module samt Modulverantwortlichen, Erstprüfern und Zweitprüfern über die MOCOGI-API und integriert sie in den Graphen von `th_personal.db`.
- **Pyvis Visualisierung:** Generiert eine interaktive 2D-HTML-Visualisierung des Graphen aus `th_personal.db` mit Filter- und Zoommöglichkeiten.

## Ordnerstruktur
- `src/th_personal_graph/`: Kernmodule und Logik.
- `src/th_personal_graph/scripts/`: Benutzerorientierte CLI-Skripte zur Ausführung der Workflows.
- `tests/`: Umfassende Testsuite für den Crawler und MOCOGI-Extraktor.

## Wichtige Skripte

Die Skripte befinden sich im Unterordner `scripts` und werden als Modul aufgerufen:

### 1. TH Personal Crawling
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-faculties
python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
```

### 2. MOCOGI Datenextraktion
```bash
python -m th_personal_graph.scripts.extract_mocogi_data
```

### 3. Wissensgraph visualisieren
```bash
python -m th_personal_graph.scripts.visualize_knowledge_graph --filter "Informatik"
```

## Installation
Innerhalb des Hauptprojekts:
```bash
pip install -e .
```
Oder als separates Package:
```bash
cd packages/th_personal_graph
pip install -e .
```

Für detaillierte Informationen zur Nutzung und Architektur besuchen Sie bitte die [Dokumentation](https://dgaida.github.io/academic-memory-mcp/dev/packages/th-personal-graph/).
