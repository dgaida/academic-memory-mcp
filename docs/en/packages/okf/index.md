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

---

## Installation, Folder Setup & Scripts

This section explains how to install the required OKF tools, set up the directory structure, and execute the generation script.

### 1. Installing `google-okf`

The `academic_okf` sub-package is built upon Google's Open Knowledge Format (OKF) specification. To install the underlying `google-okf` framework or related packages, use pip.

Run the following command in your terminal or virtual environment:

```bash
pip install google-okf
```

*(Note: Ensure you have also installed the project's editable dependencies via `pip install -e .` or using `environment.yml`.)*

### 2. Creating the OKF Folder & Memory Paths

Each email class uses its own knowledge folder (OKF). The target OKF folder must be created inside a directory specified in `classifier_memory_paths.yaml` (located at `config/classifier_memory_paths.yaml`).

Multiple email classes can share a single OKF folder, which is defined in the configuration file. For example, in `classifier_memory_paths.yaml`:

```yaml
class_paths:
  PAV_PO-Wechsel: "D:/PAV/okf"
  InformatikProjekt: "D:/PAV/okf" # Shares the same OKF folder with PAV_PO-Wechsel
```

Ensure that you create the specified target directory (e.g., `D:/PAV/okf`) before running the pipeline.

### 3. Location of the Original PDF Documents

For the pipeline to parse and convert source files, your original PDFs must be stored in a specific location:

- The original PDF documents must reside in a **parallel folder** named `Memory` situated on the same hierarchy level as the OKF directory.  
- If your OKF folder path is `D:/PAV/okf`, the original PDFs must be placed inside `D:/PAV/Memory`.  
- Within the `Memory` directory, you are allowed to have arbitrary **subfolders** to organize your PDF collections.  

Example directory layout:
```text
D:/PAV/
├── okf/       <-- Generated OKF folder (where the bundle is built)
└── Memory/    <-- Contains the original PDFs
    ├── PO-Wechsel/
    │   └── InfosPOWechselHärtefall.pdf
    └── Misc/
```

### 4. The `create_okf_from_memory` Script

To trigger the conversion and LLM knowledge extraction process, use the provided `create_okf_from_memory.py` script.

This script scans the PDF documents in the `Memory` folder, processes them through `LiteParse`, extracts structured knowledge artifacts using LLMs, and builds the finalized OKF bundle in the configured OKF path.

**Execution:**

Run the script from the repository root:

```bash
python packages/okf/src/okf/scripts/create_okf_from_memory.py
```

The script defaults to looking for configured paths, but you can override its directories using environment variables such as `OKF_DIR` and `PDF_DIR`.
