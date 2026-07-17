# Installation

The MCP University Memory System can be installed in several ways.

## Prerequisites

- Python 3.10 or higher  
- Ollama (for local LLM support)  
- Outlook (for working with .msg files and calendar integration under Windows)  

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


## Installation with Anaconda / Conda (Alternative)

As an alternative to the standard Python virtual environment, you can install the system using an Anaconda/Miniconda environment. The project contains a pre-configured `environment.yml` file.

### Conda Installation Process:

1. **Create Conda Environment:**  
   Create the new environment with all dependencies (including Python, PyTorch, and libraries such as Docling):
   ```bash
   conda env create -f environment.yml
   ```

2. **Activate Environment:**  
   Activate the created environment:
   ```bash
   conda activate mcp-university
   ```

3. **Install the Project in Editable Mode:**  
   To correctly register the CLI commands and Python paths, install the package in the activated Conda environment in editable mode:
   ```bash
   pip install -e .
   ```

4. **Verify Installation:**  
   Check if the installation was successful:
   ```bash
   mcp-uni --help
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
- **Models:** By default, the model [gemma4:e2b](https://ollama.com/library/gemma4) (`gemma4:e2b`) is used. You can change this in `config/models.yaml`.  


### Docling (PDF Parsing)

The system uses Docling for optimal PDF extraction. This is automatically installed as a dependency during the installation of `mcp-university` (via `pip install -e .`).
If you still need to install it separately:
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
