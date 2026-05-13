# Konfiguration

Das System wird über YAML-Dateien im Verzeichnis `config/` gesteuert.

## folders.yaml

Definiert, welche Verzeichnisse überwacht werden und welche Dateien ein- oder ausgeschlossen werden sollen.

| Option | Beschreibung | Standard |
|---|---|---|
| `folders` | Liste der absoluten Pfade zu den zu indizierenden Ordnern. | `[]` |
| `exclude_patterns` | Liste von Glob-Mustern für auszuschließende Dateien/Ordner. | `[.git, node_modules, ...]` |
| `supported_extensions` | Liste der zu verarbeitenden Dateiendungen. | `[.pdf, .docx, .md, .txt, ...]` |

**Beispiel:**
```yaml
folders:
  - /home/user/documents/university
exclude_patterns:
  - "**/tmp/*"
```

## models.yaml

Konfiguriert die verwendeten KI-Modelle für LLM, Embeddings und Reranking.

### LLM (Ollama)
| Option | Beschreibung | Standard |
|---|---|---|
| `model` | Name des Modells in Ollama. | `gemma2:2b` |
| `temperature` | Kreativität des Modells (0 = deterministisch). | `0.0` |
| `base_url` | URL zum Ollama-Server. | `http://localhost:11434` |

### Embeddings
| Option | Beschreibung | Standard |
|---|---|---|
| `model` | HuggingFace Modellname für Vektoren. | `BAAI/bge-m3` |

**Beispiel:**
```yaml
llm:
  model: "llama3:8b"
  temperature: 0.1
embeddings:
  model: "BAAI/bge-m3"
```

## Umgebungsvariablen

Einige Einstellungen können über Umgebungsvariablen überschrieben werden:

*   `DEBUG`: Aktiviert detailliertes Logging (True/False).
*   `CONFIG_DIR`: Pfad zum Konfigurationsverzeichnis (Standard: `./config`).
