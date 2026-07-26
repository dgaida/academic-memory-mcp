import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
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

def find_duplicate_file(
    directory: Path,
    item: Dict[str, Any],
    item_type: str,
    config: Optional[Any] = None
) -> Optional[Path]:
    """Find a duplicate file in the given directory.

    Checks for duplicate files using three stages of similarity:
    1. Exact filename match based on the sanitized item name.
    2. Case-insensitive and whitespace-normalized name/term/title match against all existing files.
    3. LLM-based duplicate or alias detection using the provided OKFConfig client.

    Args:
        directory: The directory path where the files are stored.
        item: The dictionary representing the item (concept, entity, definition, table).
        item_type: The string type of the item ('Concept', 'Entity', 'Definition', 'Table').
        config: The optional OKFConfig configuration instance.

    Returns:
        The Path to the duplicate file if found, otherwise None.
    """
    if not directory.exists():
        return None

    # Determine names/titles and descriptions based on item type
    new_name = ""
    new_description = ""
    if item_type == "Concept":
        new_name = item.get("name", "")
        new_description = item.get("description", "")
    elif item_type == "Entity":
        new_name = item.get("name", "")
        new_description = item.get("description", "")
    elif item_type == "Definition":
        new_name = item.get("term", "")
        new_description = item.get("definition", "")
    elif item_type == "Table":
        new_name = item.get("title", "")
        new_description = item.get("description", "")

    if not new_name:
        return None

    # Stage 1: Exact sanitized filename match
    sanitized_filename_str = sanitize_filename(new_name)
    exact_match_path = directory / sanitized_filename_str
    if exact_match_path.exists():
        return exact_match_path

    # Stage 2: Normalized title match
    def normalize_string_for_comparison(input_string: str) -> str:
        """Normalize a string by lowercasing, stripping, and removing non-alphanumeric characters."""
        input_string = input_string.lower().strip()
        input_string = re.sub(r"[^a-z0-9]", "", input_string)
        return input_string

    normalized_new_name = normalize_string_for_comparison(new_name)

    existing_markdown_files = list(directory.glob("*.md"))
    loaded_existing_files = []

    for file_path in existing_markdown_files:
        try:
            post = frontmatter.load(file_path)
            existing_type = post.metadata.get("type", "")
            existing_title = ""
            existing_description = ""

            if existing_type == "Concept":
                existing_title = post.metadata.get("title", "")
                existing_description = post.metadata.get("description", "")
            elif existing_type == "Entity":
                existing_title = post.metadata.get("title", "")
                existing_description = post.metadata.get("description", "")
            elif existing_type == "Definition":
                existing_title = post.metadata.get("term", "")
                existing_description = post.content
            elif existing_type == "Table":
                existing_title = post.metadata.get("title", "")
                existing_description = post.metadata.get("description", "")
            else:
                existing_title = post.metadata.get("title", file_path.stem)
                existing_description = post.metadata.get("description", "")

            # Store loaded file information for possible LLM stage
            loaded_existing_files.append({
                "path": file_path,
                "title": existing_title,
                "description": existing_description,
                "filename": file_path.name
            })

            if existing_title and normalize_string_for_comparison(existing_title) == normalized_new_name:
                print(f"Normalized match found: '{new_name}' matches existing file '{file_path.name}' with title '{existing_title}'")
                return file_path

        except Exception as exception_error:
            print(f"Error loading {file_path} for duplicate check: {exception_error}")

    # Stage 3: LLM-based duplicate / alias check
    if config and getattr(config, "client", None) and loaded_existing_files:
        try:
            system_prompt = (
                "You are an expert Knowledge Graph deduplication assistant.\n"
                "Your task is to determine if a newly extracted artifact is a duplicate or near-duplicate of an existing artifact in the database, even if it has a different name, alias, translation, plural/singular variation, or slight wording difference.\n"
                "Return ONLY the exact filename of the matching existing artifact, or return 'None' if there is no duplicate."
            )

            # Format the list of existing artifacts
            existing_artifacts_text = ""
            for loaded_file in loaded_existing_files:
                existing_artifacts_text += (
                    f"- Filename: {loaded_file['filename']}\n"
                    f"  Title/Name: {loaded_file['title']}\n"
                    f"  Description: {loaded_file['description']}\n\n"
                )

            user_prompt = (
                f"New Artifact:\n"
                f"- Type: {item_type}\n"
                f"- Name/Title: {new_name}\n"
                f"- Description: {new_description}\n\n"
                f"Existing Artifacts in Database:\n"
                f"{existing_artifacts_text}"
                f"Determine if the new artifact refers to the same concept, entity, table, or definition as one of the existing artifacts. "
                f"Even if they have different names (e.g. 'TH Köln' vs 'Technische Hochschule Köln', 'Prüfungsordnung' vs 'Modulprüfungsordnung', 'Daniel Gaida' vs 'Prof. Dr. Daniel Gaida', singular/plural variations, synonyms, or English/German translations), if they refer to the same thing, they are duplicates.\n\n"
                f"Return ONLY the filename of the duplicate from the list (e.g. 'th-k-ln.md'), or 'None' if it is a new/different artifact. Do not write any other explanation, markdown formatting, or preamble."
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            llm_response = config.client.chat_completion(messages)
            cleaned_llm_response = llm_response.strip().replace("`", "").strip()

            if cleaned_llm_response and cleaned_llm_response != "None":
                # Verify that cleaned_llm_response is actually one of the filenames
                for loaded_file in loaded_existing_files:
                    if loaded_file["filename"] == cleaned_llm_response:
                        print(f"LLM duplicate check matched: '{new_name}' -> '{loaded_file['title']}' ({loaded_file['filename']})")
                        return loaded_file["path"]
        except Exception as exception_error:
            print(f"Error during LLM duplicate check: {exception_error}")

    return None

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

def write_concept(concept: Dict[str, Any], source_file: str, concept_dir: Path, generated_by: Optional[str] = None, config: Optional[Any] = None) -> None:
    """Write an OKF concept file.

    Args:
        concept: Concept data dict.
        source_file: The source file name.
        concept_dir: Concept output directory.
        generated_by: The generator agent string.
        config: The optional OKFConfig configuration instance.
    """
    filename = sanitize_filename(concept["name"])

    # Check for duplicates or near-duplicates
    duplicate_path = find_duplicate_file(concept_dir, concept, "Concept", config)
    if duplicate_path:
        path = duplicate_path
    else:
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

def write_entity(entity: Dict[str, Any], source_file: str, entity_dir: Path, generated_by: Optional[str] = None, config: Optional[Any] = None) -> None:
    """Write an OKF entity file.

    Args:
        entity: Entity data dict.
        source_file: The source file name.
        entity_dir: Entity output directory.
        generated_by: The generator agent string.
        config: The optional OKFConfig configuration instance.
    """
    filename = sanitize_filename(entity["name"])

    # Check for duplicates or near-duplicates
    duplicate_path = find_duplicate_file(entity_dir, entity, "Entity", config)
    if duplicate_path:
        path = duplicate_path
    else:
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

def write_definition(definition: Dict[str, Any], source_file: str, definition_dir: Path, generated_by: Optional[str] = None, config: Optional[Any] = None) -> None:
    """Write an OKF definition file.

    Args:
        definition: Definition data dict.
        source_file: The source file name.
        definition_dir: Definition output directory.
        generated_by: The generator agent string.
        config: The optional OKFConfig configuration instance.
    """
    filename = sanitize_filename(definition["term"])

    # Check for duplicates or near-duplicates
    duplicate_path = find_duplicate_file(definition_dir, definition, "Definition", config)
    if duplicate_path:
        path = duplicate_path
    else:
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

def write_table(table: Dict[str, Any], source_file: str, table_dir: Path, generated_by: Optional[str] = None, config: Optional[Any] = None) -> None:
    """Write an OKF table file.

    Args:
        table: Table data dict.
        source_file: The source file name.
        table_dir: Table output directory.
        generated_by: The generator agent string.
        config: The optional OKFConfig configuration instance.
    """
    filename = sanitize_filename(table["title"])

    # Check for duplicates or near-duplicates
    duplicate_path = find_duplicate_file(table_dir, table, "Table", config)
    if duplicate_path:
        path = duplicate_path
    else:
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
