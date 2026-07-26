from pathlib import Path
import subprocess
import json, re
import yaml
import frontmatter
from datetime import datetime, timezone

from llm_client import LLMClient
from dotenv import load_dotenv


# -------------------------------------------------------
# Configuration
# -------------------------------------------------------

OKF_DIR = Path("D:/TH_Koeln/PAV/okf")

PDF_DIR = OKF_DIR / ".." / "Memory"

DOCUMENT_DIR = OKF_DIR / "documents"
CONCEPT_DIR = OKF_DIR / "concepts"
ENTITY_DIR = OKF_DIR / "entities"
DEFINITION_DIR = OKF_DIR / "definitions"
TABLE_DIR = OKF_DIR / "tables"


SPEC_FILE = Path("config/SPEC.md")

load_dotenv("config/secrets.env")  # reads variables from a .env file and sets them in os.environ


client = LLMClient(api_choice="kiconnect", llm="openai-gpt-oss-120b")


def parse_pdfs_with_liteparse(
    pdf_root: Path,
    document_dir: Path
):
    """
    Recursively parse all PDFs with LiteParse
    and store Markdown files in the OKF documents directory.

    Args:
        pdf_root:
            Root directory containing PDFs

        document_dir:
            OKF documents directory
    """

    document_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    pdf_files = list(
        pdf_root.rglob("*.pdf")
    )

    if not pdf_files:
        print(
            f"No PDFs found in {pdf_root}"
        )
        return


    for pdf_file in pdf_files:

        # preserve folder structure
        relative_path = pdf_file.relative_to(
            pdf_root
        )

        md_file = (
            document_dir
            / relative_path
        ).with_suffix(".md")

        # Bereits vorhandene Markdown-Dateien überspringen
        if md_file.exists():
            print(
                f"Skipping existing: {md_file}"
            )
            continue

        md_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )


        print(
            f"Parsing: {pdf_file}"
        )


        try:
            subprocess.run(
                [
                    "lit",
                    "parse",
                    str(pdf_file),
                    "--format",
                    "markdown",
                    "-o",
                    str(md_file)
                ],
                check=True
            )

            print(
                f"Created: {md_file}"
            )


        except subprocess.CalledProcessError as e:

            print(
                f"ERROR parsing {pdf_file}: {e}"
            )


# -------------------------------------------------------
# Load OKF specification
# -------------------------------------------------------

def load_spec():

    return SPEC_FILE.read_text(
        encoding="utf-8"
    )


# -------------------------------------------------------
# LLM call wrapper
# -------------------------------------------------------

def ask_llm(system_prompt, user_prompt):

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    response = client.chat_completion(messages)

    return json.loads(response)


# -------------------------------------------------------
# Phase 1:
# Extract knowledge model
# -------------------------------------------------------

def extract_knowledge(markdown, filename, spec):

    system_prompt = """
You are an expert Knowledge Engineer specialized in the Open Knowledge Format
(OKF) version 0.2.

Your task is to analyze source documents and extract structured knowledge
artifacts that can be stored in an OKF knowledge bundle.

You must:
- strictly follow the OKF specification
- preserve provenance
- extract only information explicitly supported by the source document
- never invent facts
- return only valid JSON
- do not include Markdown fences
"""

    user_prompt = f"""
Analyze the following source document and extract OKF knowledge artifacts.

The artifacts are:

1. Concepts
----------------
Concepts are abstract knowledge units or topics.

Examples:
- Examination procedure
- Machine Learning
- Transformer Architecture
- Competency-based education

A concept is NOT a concrete named object.

Extract:
- name
- description
- related concepts if obvious


2. Entities
----------------
Entities are concrete identifiable objects.

Examples:
- Person
- Organization
- University
- Software system
- Course
- Regulation
- Product

Extract:
- name
- entity type
- description


3. Definitions
----------------
Definitions are explicit explanations of terms.

Look for patterns like:
- "X is ..."
- "X bezeichnet ..."
- "Unter X versteht man ..."
- "X refers to ..."

Extract:
- term
- definition text
- source context


4. Tables
----------------
Extract meaningful tables.

A table should only be extracted if it contains structured information
that is useful independently from the document.

Examples:
- module overview
- comparison tables
- schedules
- parameter tables

Extract:
- title
- columns
- rows


--------------------
OKF SPECIFICATION
--------------------

{spec}


--------------------
SOURCE DOCUMENT
--------------------

Filename:

{filename}


Content:

{markdown}


Return ONLY this JSON structure:

{{
  "document": {{
    "title": "",
    "description": "",
    "source_file": "{filename}"
  }},

  "concepts": [
    {{
      "name": "",
      "description": "",
      "related_concepts": []
    }}
  ],

  "entities": [
    {{
      "name": "",
      "type": "",
      "description": ""
    }}
  ],

  "definitions": [
    {{
      "term": "",
      "definition": "",
      "context": ""
    }}
  ],

  "tables": [
    {{
      "title": "",
      "description": "",
      "columns": [],
      "rows": []
    }}
  ],

  "relations": [
    {{
      "source": "",
      "relation": "",
      "target": ""
    }}
  ]
}}


Additional rules:

- Keep names concise.
- Do not duplicate the same artifact.
- Prefer fewer high-quality artifacts over many weak artifacts.
- Every extracted artifact must be traceable to the source document.
- If no artifacts of a type exist, return an empty array.
"""

    return ask_llm(
        system_prompt,
        user_prompt
    )


# -------------------------------------------------------
# Phase 2:
# Create OKF concept document
# -------------------------------------------------------

def create_concept(concept, knowledge, spec):

    system_prompt = """
You create OKF version 0.2 concept documents.

You must follow the OKF specification exactly.

Return only JSON.
"""

    user_prompt = f"""
Create a single OKF concept file.

Specification:

{spec}


Concept:

{json.dumps(concept, indent=2)}


Context from source document:

{json.dumps(knowledge, indent=2)}


Return:

{{
 "filename": "",
 "frontmatter": {{
    "type": "concept",
    "title": "",
    "description": "",
    "tags": [],
    "sources": []
 }},
 "body": ""
}}
"""

    return ask_llm(
        system_prompt,
        user_prompt
    )


def sanitize_filename(name):

    name = name.replace("\\", "/")

    parts = []

    for part in name.split("/"):

        part = part.lower()

        part = re.sub(
            r"[^a-z0-9_-]",
            "-",
            part
        )

        part = re.sub(
            r"-+",
            "-",
            part
        )

        parts.append(
            part.strip("-")
        )


    filename = "/".join(parts)

    if not filename.endswith(".md"):
        filename += ".md"

    return filename


# -------------------------------------------------------
# Write OKF markdown
# -------------------------------------------------------


def write_okf_markdown(
    path: Path,
    frontmatter_data: dict,
    body: str
):
    """
    Write an OKF markdown artifact with YAML frontmatter.
    """

    if path.exists():
        print(f"Already exists: {path}")
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    post = frontmatter.Post(
        body,
        **frontmatter_data
    )

    path.write_text(
        frontmatter.dumps(post),
        encoding="utf-8"
    )


def write_concept(concept, source_file):

    filename = sanitize_filename(
        concept["name"]
    ) + ".md"

    path = CONCEPT_DIR / filename


    metadata = {
        "type": "concept",
        "title": concept["name"],
        "description": concept.get(
            "description",
            ""
        ),
        "sources": [
            {
                "path": f"documents/{source_file}"
            }
        ]
    }


    body = f"""# {concept["name"]}

{concept.get("description", "")}


"""


    if concept.get("related_concepts"):

        body += """
## Related concepts

"""

        for c in concept["related_concepts"]:
            body += f"- {c}\n"


    write_okf_markdown(
        path,
        metadata,
        body
    )


def write_entity(entity, source_file):

    filename = sanitize_filename(
        entity["name"]
    ) + ".md"

    path = ENTITY_DIR / filename


    metadata = {
        "type": "entity",
        "entity_type": entity.get(
            "type",
            "unknown"
        ),
        "title": entity["name"],
        "sources": [
            {
                "path": f"documents/{source_file}"
            }
        ]
    }


    body = f"""# {entity["name"]}

Type:

{entity.get("type", "")}


{entity.get("description", "")}
"""


    write_okf_markdown(
        path,
        metadata,
        body
    )


def write_definition(definition, source_file):

    filename = sanitize_filename(
        definition["term"]
    ) + ".md"


    path = DEFINITION_DIR / filename


    metadata = {
        "type": "definition",
        "term": definition["term"],
        "sources": [
            {
                "path": f"documents/{source_file}"
            }
        ]
    }


    body = f"""# {definition["term"]}

{definition["definition"]}


## Context

{definition.get("context", "")}
"""


    write_okf_markdown(
        path,
        metadata,
        body
    )


def write_table(table, source_file):

    filename = sanitize_filename(
        table["title"]
    ) + ".md"


    path = TABLE_DIR / filename


    metadata = {
        "type": "table",
        "title": table["title"],
        "description": table.get(
            "description",
            ""
        ),
        "sources": [
            {
                "path": f"documents/{source_file}"
            }
        ]
    }


    body = f"""# {table["title"]}

{table.get("description", "")}


"""


    # Markdown table erzeugen

    columns = table.get(
        "columns",
        []
    )

    rows = table.get(
        "rows",
        []
    )


    if columns:

        body += "| " + " | ".join(columns) + " |\n"
        body += "| " + " | ".join(
            ["---"] * len(columns)
        ) + " |\n"


        for row in rows:
            body += (
                "| "
                + " | ".join(
                    str(x) for x in row
                )
                + " |\n"
            )


    write_okf_markdown(
        path,
        metadata,
        body
    )


# -------------------------------------------------------
# Create index
# -------------------------------------------------------

def create_index():

    content = """---
type: index
okf_version: "0.2"
---

# Knowledge Bundle

"""


    # Verzeichnisse und Bezeichnungen
    artifact_dirs = [
        ("Documents", DOCUMENT_DIR, "documents"),
        ("Concepts", CONCEPT_DIR, "concepts"),
        ("Entities", ENTITY_DIR, "entities"),
        ("Definitions", DEFINITION_DIR, "definitions"),
        ("Tables", TABLE_DIR, "tables"),
    ]


    statistics = {}


    # Statistik und Inhaltsverzeichnis erzeugen
    for title, directory, relative_path in artifact_dirs:

        count = 0

        content += f"\n## {title}\n\n"


        if not directory.exists():
            content += "_No entries found._\n"
            statistics[title.lower()] = 0
            continue


        for file in directory.rglob("*.md"):

            count += 1

            print(file)


            # Documents können auch einfach gelistet werden
            if title == "Documents":

                item_title = file.stem

            else:

                doc = frontmatter.load(file)

                item_title = doc.metadata.get(
                    "title",
                    file.stem
                )


            # korrekter relativer OKF-Pfad
            bundle_path = file.relative_to(
                OKF_DIR
            ).as_posix()


            content += (
                f"- [{item_title}]"
                f"({bundle_path})\n"
            )


        statistics[title.lower()] = count


    # Statistik-Sektion ergänzen
    stats_content = f"""

## Statistics

- Documents: {statistics.get("documents", 0)}
- Concepts: {statistics.get("concepts", 0)}
- Entities: {statistics.get("entities", 0)}
- Definitions: {statistics.get("definitions", 0)}
- Tables: {statistics.get("tables", 0)}

"""


    # Statistik direkt nach dem Header einfügen
    content = content.replace(
        "# Knowledge Bundle\n",
        "# Knowledge Bundle\n" + stats_content
    )


    (OKF_DIR / "index.md").write_text(
        content,
        encoding="utf-8"
    )


# -------------------------------------------------------
# Main pipeline
# -------------------------------------------------------

def main():

    CONCEPT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    ENTITY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    parse_pdfs_with_liteparse(
        PDF_DIR,
        DOCUMENT_DIR
    )

    spec = load_spec()


    for md_file in DOCUMENT_DIR.rglob("*.md"):

        print(
            "Processing:",
            md_file.name
        )


        markdown = md_file.read_text(
            encoding="utf-8"
        )


        # Phase 1
        knowledge = extract_knowledge(
            markdown,
            md_file.name,
            spec
        )


        # Phase 2
        for concept in knowledge["concepts"]:
            write_concept(
                concept,
                md_file.name
            )

        for entity in knowledge["entities"]:
            write_entity(
                entity,
                md_file.name
            )

        for definition in knowledge["definitions"]:
            write_definition(
                definition,
                md_file.name
            )

        for table in knowledge["tables"]:
            write_table(
                table,
                md_file.name
            )


    create_index()


if __name__ == "__main__":
    main()
