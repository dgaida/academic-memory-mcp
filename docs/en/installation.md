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

## System Dependencies

### Ollama (LLM Backend)

The system requires a running Ollama instance.
- **Download:** [ollama.com](https://ollama.com)
- **Models:** By default, `gemma2:2b` is used. You can change this in `config/models.yaml`.


### MinerU (PDF Parsing)

The system uses MinerU for optimal PDF extraction.
```bash
pip install "magic-pdf[full]"
```
Ensure that the necessary model weights for MinerU are initialized (usually happens automatically on the first run).

## Verify Installation

Check if the CLI tool was installed correctly:

```bash
mcp-uni --help
```
