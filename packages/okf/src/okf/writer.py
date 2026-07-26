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
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            post = frontmatter.load(path)
            existing_sources = post.metadata.get("sources", [])
            new_sources = frontmatter_data.get("sources", [])

            # Keep track of existing resources
            existing_resources = {s.get("resource") for s in existing_sources if "resource" in s}
            existing_ids = {s.get("id") for s in existing_sources if "id" in s}

            merged_sources = list(existing_sources)
            added_any = False

            for ns in new_sources:
                res = ns.get("resource")
                if res not in existing_resources:
                    # Generate a unique ID if there is a collision
                    orig_id = ns.get("id")
                    candidate_id = orig_id
                    counter = 2
                    while candidate_id in existing_ids:
                        candidate_id = f"{orig_id}-{counter}"
                        counter += 1

                    new_source_entry = dict(ns)
                    new_source_entry["id"] = candidate_id
                    existing_ids.add(candidate_id)

                    merged_sources.append(new_source_entry)
                    added_any = True

            if added_any:
                post.metadata["sources"] = merged_sources
                path.write_text(frontmatter.dumps(post), encoding="utf-8")
                print(f"Merged new sources into: {path}")
            else:
                print(f"Already exists with same source resources: {path}")
            return
        except Exception as e:
            print(f"ERROR reading/merging {path}: {e}")
            # Fall back to overwriting or return? Let's return to avoid overwriting or continue as is.
            return

    post = frontmatter.Post(body, **frontmatter_data)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")

from datetime import datetime, timezone

def write_concept(concept: dict, source_file: str, concept_dir: Path, generated_by: str = None) -> None:
    """Write an OKF concept file.

    Args:
        concept: Concept data dict.
        source_file: The source file name.
        concept_dir: Concept output directory.
        generated_by: The generator agent string.
    """
    filename = sanitize_filename(concept["name"])
    path = concept_dir / filename
    source_id = Path(source_file).stem

    metadata = {
        "type": "Concept",
        "title": concept["name"],
        "description": concept.get("description", ""),
        "sources": [
            {
                "id": source_id,
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    if generated_by:
        metadata["generated"] = {
            "by": generated_by,
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

    body = f"# {concept['name']}\n\n{concept.get('description', '')}\n\n"

    if concept.get("related_concepts"):
        body += "\n## Related concepts\n\n"
        for c in concept["related_concepts"]:
            target = sanitize_filename(c)
            body += f"- [{c}](/concepts/{target})\n"

    write_okf_markdown(path, metadata, body)

def write_entity(entity: dict, source_file: str, entity_dir: Path, generated_by: str = None) -> None:
    """Write an OKF entity file.

    Args:
        entity: Entity data dict.
        source_file: The source file name.
        entity_dir: Entity output directory.
        generated_by: The generator agent string.
    """
    filename = sanitize_filename(entity["name"])
    path = entity_dir / filename
    source_id = Path(source_file).stem

    metadata = {
        "type": "Entity",
        "entity_type": entity.get("type", "unknown"),
        "title": entity["name"],
        "sources": [
            {
                "id": source_id,
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    if generated_by:
        metadata["generated"] = {
            "by": generated_by,
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

    body = f"# {entity['name']}\n\nType:\n\n{entity.get('type', '')}\n\n\n{entity.get('description', '')}\n"

    write_okf_markdown(path, metadata, body)

def write_definition(definition: dict, source_file: str, definition_dir: Path, generated_by: str = None) -> None:
    """Write an OKF definition file.

    Args:
        definition: Definition data dict.
        source_file: The source file name.
        definition_dir: Definition output directory.
        generated_by: The generator agent string.
    """
    filename = sanitize_filename(definition["term"])
    path = definition_dir / filename
    source_id = Path(source_file).stem

    metadata = {
        "type": "Definition",
        "term": definition["term"],
        "sources": [
            {
                "id": source_id,
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    if generated_by:
        metadata["generated"] = {
            "by": generated_by,
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

    body = (
        f"# {definition['term']}\n\n"
        f"{definition['definition']}[^{source_id}]\n\n\n"
        f"## Context\n\n{definition.get('context', '')}\n\n"
        f"[^{source_id}]: {source_file}\n"
    )

    write_okf_markdown(path, metadata, body)

def write_table(table: dict, source_file: str, table_dir: Path, generated_by: str = None) -> None:
    """Write an OKF table file.

    Args:
        table: Table data dict.
        source_file: The source file name.
        table_dir: Table output directory.
        generated_by: The generator agent string.
    """
    filename = sanitize_filename(table["title"])
    path = table_dir / filename
    source_id = Path(source_file).stem

    metadata = {
        "type": "Table",
        "title": table["title"],
        "description": table.get("description", ""),
        "sources": [
            {
                "id": source_id,
                "resource": f"/documents/{source_file}"
            }
        ]
    }

    if generated_by:
        metadata["generated"] = {
            "by": generated_by,
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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

            doc = frontmatter.load(file)
            item_title = doc.metadata.get("title", file.stem)

            description = doc.metadata.get("description", "")
            suffix = f" - {description}" if description else ""

            bundle_path = file.relative_to(okf_dir).as_posix()
            content += f"- [{item_title}]({bundle_path}){suffix}\n"

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
