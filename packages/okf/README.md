# md2okf - PDF/Markdown to Open Knowledge Format (OKF) Producer

## Overview

`create_okf_from_memory` converts PDF-based document collections into an
[Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
knowledge bundle.

The goal is not only to convert documents into Markdown, but to transform
unstructured documents into a structured, provenance-aware knowledge base.

The generated OKF bundle contains:

- original source documents
- extracted concepts
- extracted entities
- extracted definitions
- extracted tables
- an index for navigation

The resulting knowledge base can be used as a foundation for:

- Retrieval Augmented Generation (RAG)
- AI agents
- semantic search
- knowledge graphs
- institutional knowledge management


---

# Open Knowledge Format (OKF)

The **Open Knowledge Format (OKF)** is an open format for representing
knowledge as a collection of Markdown files with YAML frontmatter.

An OKF knowledge bundle combines:

- human-readable Markdown documents
- machine-readable metadata
- explicit relationships between knowledge artifacts
- provenance information linking generated knowledge back to source documents


The official OKF repository and specification are maintained by Google Cloud
Knowledge Catalog:

## Official OKF repository

https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf


## OKF specification

https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md


---

# Processing Pipeline

The complete processing workflow is:

```
PDF documents
      |
      v
+-------------+
|  LiteParse  |
+-------------+
      |
      v
Markdown source documents
      |
      v
+----------------+
| LLM Extraction |
+----------------+
      |
      +----------------+
      |                |
      v                v

 documents/       Knowledge artifacts

                  concepts/
                  entities/
                  definitions/
                  tables/

      |
      v

 index.md
```

---

# Generated OKF Structure

Example output:

```
my_okf/

├── index.md

├── documents/
│   ├── examination-guidelines.md
│   └── regulations.md

├── concepts/
│   ├── examination-supervision.md
│   └── competency-based-learning.md

├── entities/
│   ├── th-koeln.md
│   └── examination-office.md

├── definitions/
│   └── examination-supervision.md

└── tables/
    └── examination-aids.md
```

---

# Artifact Types

## documents

The `documents` folder contains the original Markdown representation of the
source PDFs.

The conversion is performed by LiteParse.

Example:

```
documents/examination-guidelines.md
```

These files are the primary sources and provide provenance for all extracted
knowledge artifacts.

---

## concepts

Concepts represent abstract knowledge units.

Examples:

- Examination supervision
- Machine learning
- Transformer architecture
- Competency-based education


Example:

```
concepts/examination-supervision.md
```

---

## entities

Entities represent concrete identifiable objects.

Examples:

- organizations
- persons
- software systems
- courses
- regulations


Example:

```
entities/examination-office.md
```

---

## definitions

Definitions represent explicit explanations of terms extracted from documents.

Examples:

- Module
- Examination supervision
- Learning outcome


Example:

```
definitions/module.md
```

---

## tables

Tables contain structured information extracted from documents.

Examples:

- module catalogs
- comparison tables
- schedules
- parameter lists


Example:

```
tables/module-overview.md
```

---

# Requirements

The project requires:

- Python >= 3.12
- Conda environment (recommended)
- LiteParse
- llm_client


Recommended environment:

```bash
conda create -n okf python=3.13
conda activate okf
```

Install dependencies:

```bash
pip install python-frontmatter
pip install python-dotenv
pip install liteparse
```

Install the LLM client:

```bash
pip install git+https://github.com/dgaida/llm_client.git
```

---

# Configuration

API keys are stored outside the source code.

Example `config/secrets.env`:

```env
OPENAI_API_KEY=your_api_key
```

The configuration is loaded using:

```python
from dotenv import load_dotenv

load_dotenv(
    "config/secrets.env"
)
```

---

# Input Data

PDF files are stored in a source directory.

Example:

```
pdfs/

├── regulations/
│   └── examination.pdf

└── guidelines/
    └── supervision.pdf
```

The folder structure is preserved when creating Markdown documents:

```
okf/documents/

├── regulations/
│   └── examination.md

└── guidelines/
    └── supervision.md
```

Existing Markdown files are not regenerated.

---

# Running create_okf_from_memory

Execute:

```bash
python create_okf_from_memory.py
```

The script performs the following steps:

1. Recursively searches PDF files
2. Converts PDFs to Markdown using LiteParse
3. Stores Markdown sources in `documents/`
4. Sends documents to the LLM extraction pipeline
5. Generates OKF artifacts:

   - concepts
   - entities
   - definitions
   - tables

6. Creates `index.md`

---

# LLM Knowledge Extraction

The extraction process uses the
`llm_client` package.

Example:

```python
from llm_client import LLMClient

client = LLMClient()

messages = [
    {
        "role": "system",
        "content":
        "You are an expert knowledge engineer."
    },
    {
        "role": "user",
        "content":
        "Extract OKF knowledge artifacts."
    }
]

response = client.chat_completion(messages)
```

The LLM receives:

- the OKF specification
- the source Markdown document
- extraction instructions

and returns structured JSON containing:

- concepts
- entities
- definitions
- tables
- relations

---

# Provenance

Every generated artifact references its source document.

Example:

```yaml
sources:
  - path: documents/examination-guidelines.md
```

This ensures that generated knowledge remains traceable back to the
original source material.

---

# Index Generation

The generated `index.md` contains:

- links to all knowledge artifacts
- artifact statistics
- navigation structure


Example:

```markdown
## Statistics

- Documents: 120
- Concepts: 450
- Entities: 320
- Definitions: 80
- Tables: 15
```

---

# Current Limitations

The current implementation provides:

- PDF ingestion
- Markdown generation
- LLM-based knowledge extraction
- OKF artifact generation
- index creation


Planned improvements:

- OKF schema validation
- duplicate detection
- entity resolution
- artifact merging
- relationship graph generation
- incremental knowledge updates


---

# References

## Open Knowledge Format (OKF)

Google Cloud Knowledge Catalog:

https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf


## OKF Specification

https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md


## LiteParse

LlamaIndex LiteParse:

https://github.com/run-llama/liteparse


## llm_client

Documentation:

https://dgaida.github.io/llm_client/dev/


---

# License

This project is intended for research and educational purposes.
