# Open Knowledge Format (OKF) Package

The `academic_okf` sub-package converts PDF-based document collections into an [Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) knowledge bundle.

The goal is not only to convert documents into Markdown, but to transform unstructured documents into a structured, provenance-aware knowledge base.

The generated OKF bundle contains:

- Original source documents  
- Extracted concepts  
- Extracted entities  
- Extracted definitions  
- Extracted tables  
- An index for navigation  

The resulting knowledge base can be used as a foundation for Retrieval Augmented Generation (RAG), AI agents, semantic search, knowledge graphs, and institutional knowledge management.

---

## Processing Pipeline

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

## Generated OKF Structure

Example output structure:

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

## Artifact Types

### documents
The `documents` folder contains the original Markdown representation of the source PDFs. The conversion is performed by LiteParse.
These files are the primary sources and provide provenance for all extracted knowledge artifacts.

### concepts
Concepts represent abstract knowledge units (e.g., *Examination supervision*, *Machine learning*, *Transformer architecture*).

### entities
Entities represent concrete identifiable objects (e.g., organizations, persons, software systems, courses, regulations).

### definitions
Definitions represent explicit explanations of terms extracted from documents (e.g., *Module*, *Learning outcome*).

### tables
Tables contain structured information extracted from documents (e.g., module catalogs, comparison tables, schedules).

---

## Configuration

Configuration is managed via the `OKFConfig` class, which handles:  
- Paths configuration (OKF output directory, source PDF directory, specification file).  
- Loading credentials from env/secrets.  
- Registering and managing the `LLMClient`.  

### Example Configuration

```python
from pathlib import Path
from okf.config import OKFConfig
from okf.pipeline import run_okf_pipeline

config = OKFConfig(
    okf_dir=Path("./my_okf_bundle"),
    pdf_dir=Path("./my_pdfs"),
    spec_file=Path("config/SPEC.md")
)

# Run full extraction pipeline
run_okf_pipeline(config)
```

---

## LLM Knowledge Extraction

The extraction process uses the `llm_client` package. The LLM receives:  
- The OKF specification  
- The source Markdown document  
- Extraction instructions  

and returns structured JSON containing concepts, entities, definitions, tables, and relations, ensuring provenance mapping and strict alignment with the OKF v0.2 specification.

### Provenance & Spec Alignment (v0.2)
Every generated artifact references its source document under `sources` using the REQUIRED `resource` attribute with bundle-relative paths (e.g., `/documents/examination-guidelines.md`).
The generated `index.md` is fully compliant with the OKF v0.2 specification, containing only the permitted `okf_version: "0.2"` in its frontmatter.
