import re
from pathlib import Path
import frontmatter

def sanitize_filename(name: str) -> str:
    """Sanitize a name to make it suitable as a filename.

    Args:
        name: Original string name.

    Returns:
        A sanitized filename ending with .md.
    """
    name = name.replace("\\", "/")
    parts = []
    for part in name.split("/"):
        part = part.lower()
        part = re.sub(r"[^a-z0-9_-]", "-", part)
        part = re.sub(r"-+", "-", part)
        parts.append(part.strip("-"))
    filename = "/".join(parts)
    if not filename.endswith(".md"):
        filename += ".md"
    return filename

def write_okf_markdown(path: Path, frontmatter_data: dict, body: str) -> None:
    """Write an OKF markdown artifact with YAML frontmatter.

    Args:
        path: Output file path.
        frontmatter_data: YAML metadata dict.
        body: Markdown body.
    """
    if path.exists():
        print(f"Already exists: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, **frontmatter_data)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")

def write_concept(concept: dict, source_file: str, concept_dir: Path) -> None:
    """Write an OKF concept file.

    Args:
        concept: Concept data dict.
        source_file: The source file name.
        concept_dir: Concept output directory.
    """
    filename = sanitize_filename(concept["name"])
    path = concept_dir / filename

    metadata = {
        "type": "concept",
        "title": concept["name"],
        "description": concept.get("description", ""),
        "sources": [
            {
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    body = f"# {concept['name']}\n\n{concept.get('description', '')}\n\n"

    if concept.get("related_concepts"):
        body += "\n## Related concepts\n\n"
        for c in concept["related_concepts"]:
            body += f"- {c}\n"

    write_okf_markdown(path, metadata, body)

def write_entity(entity: dict, source_file: str, entity_dir: Path) -> None:
    """Write an OKF entity file.

    Args:
        entity: Entity data dict.
        source_file: The source file name.
        entity_dir: Entity output directory.
    """
    filename = sanitize_filename(entity["name"])
    path = entity_dir / filename

    metadata = {
        "type": "entity",
        "entity_type": entity.get("type", "unknown"),
        "title": entity["name"],
        "sources": [
            {
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    body = f"# {entity['name']}\n\nType:\n\n{entity.get('type', '')}\n\n\n{entity.get('description', '')}\n"

    write_okf_markdown(path, metadata, body)

def write_definition(definition: dict, source_file: str, definition_dir: Path) -> None:
    """Write an OKF definition file.

    Args:
        definition: Definition data dict.
        source_file: The source file name.
        definition_dir: Definition output directory.
    """
    filename = sanitize_filename(definition["term"])
    path = definition_dir / filename

    metadata = {
        "type": "definition",
        "term": definition["term"],
        "sources": [
            {
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    body = f"# {definition['term']}\n\n{definition['definition']}\n\n\n## Context\n\n{definition.get('context', '')}\n"

    write_okf_markdown(path, metadata, body)

def write_table(table: dict, source_file: str, table_dir: Path) -> None:
    """Write an OKF table file.

    Args:
        table: Table data dict.
        source_file: The source file name.
        table_dir: Table output directory.
    """
    filename = sanitize_filename(table["title"])
    path = table_dir / filename

    metadata = {
        "type": "table",
        "title": table["title"],
        "description": table.get("description", ""),
        "sources": [
            {
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    body = f"# {table['title']}\n\n{table.get('description', '')}\n\n\n"

    columns = table.get("columns", [])
    rows = table.get("rows", [])

    if columns:
        body += "| " + " | ".join(columns) + " |\n"
        body += "| " + " | ".join(["---"] * len(columns)) + " |\n"
        for row in rows:
            body += "| " + " | ".join(str(x) for x in row) + " |\n"

    write_okf_markdown(path, metadata, body)

def create_index(okf_dir: Path, document_dir: Path, concept_dir: Path, entity_dir: Path, definition_dir: Path, table_dir: Path) -> None:
    """Create an OKF index.md containing all files in the bundle and statistics.

    Args:
        okf_dir: Path to OKF root directory.
        document_dir: Path to documents folder.
        concept_dir: Path to concepts folder.
        entity_dir: Path to entities folder.
        definition_dir: Path to definitions folder.
        table_dir: Path to tables folder.
    """
    # Aligning with OKF v0.2 spec: index.md frontmatter can only carry okf_version: "0.2" (no type: index)
    content = """---
okf_version: "0.2"
---

# Knowledge Bundle

"""

    artifact_dirs = [
        ("Documents", document_dir, "documents"),
        ("Concepts", concept_dir, "concepts"),
        ("Entities", entity_dir, "entities"),
        ("Definitions", definition_dir, "definitions"),
        ("Tables", table_dir, "tables"),
    ]

    statistics = {}

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

            if title == "Documents":
                item_title = file.stem
            else:
                doc = frontmatter.load(file)
                item_title = doc.metadata.get("title", file.stem)

            bundle_path = file.relative_to(okf_dir).as_posix()
            content += f"- [{item_title}]({bundle_path})\n"

        statistics[title.lower()] = count

    stats_content = f"""

## Statistics

- Documents: {statistics.get("documents", 0)}
- Concepts: {statistics.get("concepts", 0)}
- Entities: {statistics.get("entities", 0)}
- Definitions: {statistics.get("definitions", 0)}
- Tables: {statistics.get("tables", 0)}

"""

    content = content.replace(
        "# Knowledge Bundle\n",
        "# Knowledge Bundle\n" + stats_content
    )

    (okf_dir / "index.md").write_text(content, encoding="utf-8")
