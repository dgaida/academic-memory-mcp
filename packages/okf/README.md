# Academic OKF Sub-Package

An Open Knowledge Format (OKF) v0.2 knowledge bundle producer for the MCP University memory system.

## Overview

`academic_okf` converts PDF-based document collections into an [Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) knowledge bundle.

The generated OKF bundle contains:
- `documents/`: original source documents in Markdown (converted via LiteParse)
- `concepts/`: abstract knowledge units or topics
- `entities/`: concrete identifiable objects (organizations, persons, courses, etc.)
- `definitions/`: explicit explanations of terms
- `tables/`: structured tabular data
- `index.md`: navigation and statistics index

---

## Installation

To install this package as part of the MCP University system, install it in editable mode:

```bash
pip install -e packages/okf/
```

### Dependencies

- Python >= 3.10
- `python-frontmatter`
- `python-dotenv`
- `liteparse`
- `llm_client` (installed from Git)

---

## Configuration

Configuration is managed via the `OKFConfig` class. You can customize paths using environment variables or direct instantiation parameters:

| Parameter | Environment Variable | Default Path |
|---|---|---|
| `okf_dir` | `OKF_DIR` | `./okf` |
| `pdf_dir` | `PDF_DIR` | `./Memory` |
| `spec_file` | `OKF_SPEC_FILE` | `config/SPEC.md` |
| `secrets_file` | `OKF_SECRETS_FILE` | `config/secrets.env` |

---

## Usage

### Using the Python API

```python
from pathlib import Path
from okf.config import OKFConfig
from okf.pipeline import run_okf_pipeline

# Initialize configuration
config = OKFConfig(
    okf_dir=Path("./okf"),
    pdf_dir=Path("./Memory"),
)

# Run extraction pipeline
run_okf_pipeline(config)
```

### Running via the Command-Line Script

You can run the generator script directly from the package:

```bash
python packages/okf/src/okf/scripts/create_okf_from_memory.py
```

---

## Package Directory Structure

```
packages/okf/
├── pyproject.toml         # Sub-package project configuration
├── README.md              # Sub-package documentation
├── src/
│   └── okf/
│       ├── __init__.py    # Exports OKFConfig and run_okf_pipeline
│       ├── config.py      # Configuration class and directory setup
│       ├── parser.py      # LiteParse PDF conversion logic
│       ├── extractor.py   # LLM-based structured knowledge extraction
│       ├── writer.py      # OKF markdown writing & index.md formatting
│       ├── pipeline.py    # Main orchestration pipeline
│       └── scripts/
│           └── create_okf_from_memory.py  # User-facing CLI entry point
└── tests/                 # Unit and Integration tests
    ├── test_parser.py
    ├── test_pipeline.py
    └── test_writer.py
```

---

## Running Tests

Run the package test suite using `pytest`:

```bash
python -m pytest packages/okf/tests/
```
