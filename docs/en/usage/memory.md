# Memory System (Vector Databases)

The memory system of the MCP University System allows the agent to access specific domain knowledge stored in various documents (PDFs, Word, Markdown, etc.). This knowledge is divided into different classes (e.g., Bachelor Thesis, exam regulations), each of which has its own vector database.

## Updating Vector Databases

When new documents are added to the configured memory folders (defined in `config/classifier_memory_paths.yaml`), the vector databases must be updated. This is done via the CLI command `memory update`.

### CLI Usage

To scan all configured memory folders and update the vector databases, run the following command:

```bash
mcp-uni memory update
```

### Options

- `--config` / `-c`: Path to memory path configuration (default: `config/classifier_memory_paths.yaml`).  
- `--debug` / `-d`: Enables detailed debug logs during the indexing process.  

### How It Works

The script performs the following steps:  
1. **Path Resolution**: It reads the configuration and determines which folders are mapped to which vector databases.  
2. **Parsing**: All supported files (`.pdf`, `.docx`, `.md`, `.txt`, `.eml`, `.msg`, `.py`, `.ipynb`, `.json`, `.html`) are read.  
3. **Chunking**: Long texts are split into smaller segments (chunks).  
4. **Indexing**: The chunks are vectorized using the configured embedding model and stored in the Qdrant vector database under `data/memory/<ClassName>`.  

Since absolute paths are used as document IDs, running the update again will update existing documents and add new ones.

---
See also:  
- [RAG Process](rag-process.md)  
- [Document Indexing Details](indexing-details.md)  
