# Configuration

The system is controlled via YAML files in the `config/` directory.

## folders.yaml

Defines which directories are monitored and which files should be included or excluded.

| Option | Description | Default |
|---|---|---|
| `folders` | List of absolute paths to the folders to be indexed. | `[]` |
| `exclude_patterns` | List of glob patterns for files/folders to exclude. | `[.git, node_modules, ...]` |
| `supported_extensions` | List of file extensions to process. | `[.pdf, .docx, .md, .txt, ...]` |

**Example:**
```yaml
folders:
  - /home/user/documents/university
exclude_patterns:
  - "**/tmp/*"
```

## models.yaml

Configures the AI models used for LLM, embeddings, and reranking.

### LLM (Ollama)
| Option | Description | Default |
|---|---|---|
| `model` | Name of the model in Ollama. | `gemma2:2b` |
| `temperature` | Creativity of the model (0 = deterministic). | `0.0` |
| `base_url` | URL to the Ollama server. | `http://localhost:11434` |

### Embeddings
| Option | Description | Default |
|---|---|---|
| `model` | HuggingFace model name for vectors. | `BAAI/bge-m3` |

**Example:**
```yaml
llm:
  model: "llama3:8b"
  temperature: 0.1
embeddings:
  model: "BAAI/bge-m3"
```

## Environment Variables

Some settings can be overridden via environment variables:

*   `DEBUG`: Enables detailed logging (True/False).
*   `CONFIG_DIR`: Path to the configuration directory (Default: `./config`).
