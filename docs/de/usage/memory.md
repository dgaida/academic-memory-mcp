# Memory-System (Vektordatenbanken)

Das Memory-System des MCP University Systems ermöglicht es dem Agenten, auf spezifisches Fachwissen zuzugreifen, das in verschiedenen Dokumenten (PDFs, Word, Markdown etc.) gespeichert ist. Dieses Wissen ist in verschiedene Klassen unterteilt (z.B. Bachelor Thesis, Prüfungsordnungen), die jeweils ihre eigene Vektordatenbank besitzen.

## Aktualisierung der Vektordatenbanken

Wenn neue Dokumente in die konfigurierten Memory-Ordner (definiert in `config/classifier_memory_paths.yaml`) hinzugefügt werden, müssen die Vektordatenbanken aktualisiert werden. Dies geschieht über das CLI-Kommando `memory update`.

### Nutzung über das CLI

Um alle konfigurierten Memory-Ordner zu scannen und die Vektordatenbanken zu aktualisieren, führen Sie folgenden Befehl aus:

```bash
mcp-uni memory update
```

### Optionen

- `--config` / `-c`: Pfad zur Speicherpfad-Konfiguration (Standard: `config/classifier_memory_paths.yaml`).  
- `--debug` / `-d`: Aktiviert detaillierte Debug-Logs während des Indexierungsprozesses.  

### Funktionsweise

Das Skript führt folgende Schritte aus:  
1. **Pfad-Auflösung**: Es liest die Konfiguration und bestimmt, welche Ordner welchen Vektordatenbanken zugeordnet sind.  
2. **Parsing**: Alle unterstützten Dateien (`.pdf`, `.docx`, `.md`, `.txt`, `.eml`, `.msg`, `.py`, `.ipynb`, `.json`, `.html`) werden eingelesen.  
3. **Chunking**: Lange Texte werden in kleinere Abschnitte (Chunks) unterteilt.  
4. **Indizierung**: Die Chunks werden mittels des konfigurierten Embedding-Modells vektorisiert und in der Qdrant-Vektordatenbank unter `data/memory/<Klassenname>` gespeichert.  

Da absolute Pfade als Dokument-IDs verwendet werden, führt ein erneuter Lauf dazu, dass bestehende Dokumente aktualisiert und neue Dokumente hinzugefügt werden.

---
Siehe auch:  
- [RAG-Prozess](rag-process.md)  
- [Indizierung von Dokumenten](indexing-details.md)  
