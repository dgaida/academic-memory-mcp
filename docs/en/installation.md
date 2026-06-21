# Installation

The MCP University Memory System can be installed in several ways.

## Standard Installation (User)

For normal use, we recommend installing in a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

pip install .
```

## Developer Installation (Editable)

If you want to work on the code or test the latest changes directly:

```bash
pip install -e .
```

### Additional Developer Dependencies

For testing and documentation generation:

```bash
pip install pytest pytest-asyncio mkdocs-material mkdocs-static-i18n mkdocstrings[python] interrogate git-cliff mike
```


## GPU Support (Optional)

A GPU can be used for training and running the transformer models. For this, the corresponding version of PyTorch must be installed.

### NVIDIA GPU (CUDA)
Visit [pytorch.org](https://pytorch.org/get-started/locally/) to get the appropriate installation command for your CUDA version. Example for CUDA 12.1:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Apple Silicon (MPS)
On Macs with M1/M2/M3 chips, the GPU (Metal Performance Shaders) is automatically supported if a current PyTorch version is installed.

## System Dependencies

### Ollama (LLM Backend)

The system requires a running Ollama instance.  
- **Download:** [ollama.com](https://ollama.com)  
- **Models:** By default, `gemma2:2b` is used. You can change this in `config/models.yaml`.  


### Docling (PDF Parsing)

The system uses Docling for optimal PDF extraction.
```bash
pip install "docling"
```
Ensure that the necessary model weights for Docling are initialized (usually happens automatically on the first run).

## Verify Installation

Check if the CLI tool was installed correctly:

```bash
mcp-uni --help
```

### qmd (Search Backend)
`qmd` is required for high-quality hybrid search. It is a Node.js-based tool that must be installed globally.

**Prerequisites:**  
- Node.js >= 22 or Bun >= 1.0.0  

**Installation:**
```bash
npm install -g @tobilu/qmd
# or
bun install -g @tobilu/qmd
```

If `qmd` is not found, the system will automatically fall back to a native Python search implementation (Qdrant + BM25), but features like LLM re-ranking and query expansion will be unavailable.
