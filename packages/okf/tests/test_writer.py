import tempfile
from pathlib import Path
import frontmatter
from okf.writer import (
    sanitize_filename,
    write_concept,
    write_entity,
    write_definition,
    write_table,
    create_index
)

def test_sanitize_filename():
    assert sanitize_filename("My Concept") == "my-concept.md"
    assert sanitize_filename("A\\B/C") == "a/b/c.md"
    assert sanitize_filename("Some_Special@Chars!") == "some_special-chars.md"

def test_write_concept():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        concept = {
            "name": "Supervised Learning",
            "description": "A type of machine learning",
            "related_concepts": ["Unsupervised Learning", "Reinforcement Learning"]
        }
        write_concept(concept, "regulations.md", tmp_path)

        expected_file = tmp_path / "supervised-learning.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "concept"
        assert post.metadata["title"] == "Supervised Learning"
        assert post.metadata["sources"][0]["resource"] == "/documents/regulations.md"
        assert "Unsupervised Learning" in post.content

def test_write_entity():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        entity = {
            "name": "TH Köln",
            "type": "University",
            "description": "Technical University of Cologne"
        }
        write_entity(entity, "regulations.md", tmp_path)

        expected_file = tmp_path / "th-k-ln.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "entity"
        assert post.metadata["entity_type"] == "University"
        assert post.metadata["sources"][0]["resource"] == "/documents/regulations.md"

def test_write_definition():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        definition = {
            "term": "Module",
            "definition": "A unit of study consisting of lectures, seminars, etc.",
            "context": "According to § 5 of the regulations"
        }
        write_definition(definition, "regulations.md", tmp_path)

        expected_file = tmp_path / "module.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "definition"
        assert post.metadata["term"] == "Module"
        assert "A unit of study" in post.content
        assert "According to § 5" in post.content

def test_write_table():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        table = {
            "title": "Module Overview",
            "description": "List of all modules in the course",
            "columns": ["ID", "Name", "ECTS"],
            "rows": [
                ["M1", "Math", 5],
                ["M2", "CS", 6]
            ]
        }
        write_table(table, "regulations.md", tmp_path)

        expected_file = tmp_path / "module-overview.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "table"
        assert post.metadata["title"] == "Module Overview"
        assert "| ID | Name | ECTS |" in post.content
        assert "| M1 | Math | 5 |" in post.content

def test_create_index():
    with tempfile.TemporaryDirectory() as tmpdir:
        okf_dir = Path(tmpdir)
        doc_dir = okf_dir / "documents"
        concept_dir = okf_dir / "concepts"
        entity_dir = okf_dir / "entities"
        definition_dir = okf_dir / "definitions"
        table_dir = okf_dir / "tables"

        doc_dir.mkdir()
        concept_dir.mkdir()

        # Write dummy files
        (doc_dir / "source1.md").write_text("# Source Title", encoding="utf-8")
        write_concept({"name": "Concept 1", "description": "Desc 1"}, "source1.md", concept_dir)

        create_index(okf_dir, doc_dir, concept_dir, entity_dir, definition_dir, table_dir)

        index_file = okf_dir / "index.md"
        assert index_file.exists()

        post = frontmatter.load(index_file)
        assert post.metadata == {"okf_version": "0.2"}  # No type: index in frontmatter
        assert "- [source1](documents/source1.md)" in post.content
        assert "- [Concept 1](concepts/concept-1.md)" in post.content
        assert "Documents: 1" in post.content
        assert "Concepts: 1" in post.content
        assert "Entities: 0" in post.content
