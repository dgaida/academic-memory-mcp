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
        write_concept(concept, "regulations.md", tmp_path, "test-agent/v1")

        expected_file = tmp_path / "supervised-learning.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "Concept"
        assert post.metadata["title"] == "Supervised Learning"
        assert post.metadata["sources"][0]["id"] == "regulations"
        assert post.metadata["sources"][0]["resource"] == "/documents/regulations.md"
        assert post.metadata["generated"]["by"] == "test-agent/v1"
        assert "[- [Unsupervised Learning](/concepts/unsupervised-learning.md)]" in post.content or "unsupervised-learning.md" in post.content

def test_write_entity():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        entity = {
            "name": "TH Köln",
            "type": "University",
            "description": "Technical University of Cologne"
        }
        write_entity(entity, "regulations.md", tmp_path, "test-agent/v1")

        expected_file = tmp_path / "th-k-ln.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "Entity"
        assert post.metadata["entity_type"] == "University"
        assert post.metadata["sources"][0]["id"] == "regulations"
        assert post.metadata["sources"][0]["resource"] == "/documents/regulations.md"
        assert post.metadata["generated"]["by"] == "test-agent/v1"

def test_write_definition():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        definition = {
            "term": "Module",
            "definition": "A unit of study consisting of lectures, seminars, etc.",
            "context": "According to § 5 of the regulations"
        }
        write_definition(definition, "regulations.md", tmp_path, "test-agent/v1")

        expected_file = tmp_path / "module.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "Definition"
        assert post.metadata["term"] == "Module"
        assert post.metadata["sources"][0]["id"] == "regulations"
        assert post.metadata["sources"][0]["resource"] == "/documents/regulations.md"
        assert post.metadata["generated"]["by"] == "test-agent/v1"
        assert "A unit of study consisting of lectures, seminars, etc.[^regulations]" in post.content
        assert "[^regulations]: regulations.md" in post.content

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
        write_table(table, "regulations.md", tmp_path, "test-agent/v1")

        expected_file = tmp_path / "module-overview.md"
        assert expected_file.exists()

        post = frontmatter.load(expected_file)
        assert post.metadata["type"] == "Table"
        assert post.metadata["title"] == "Module Overview"
        assert post.metadata["sources"][0]["id"] == "regulations"
        assert post.metadata["sources"][0]["resource"] == "/documents/regulations.md"
        assert post.metadata["generated"]["by"] == "test-agent/v1"
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

        # Write dummy files with parsed-looking frontmatter
        doc_file = doc_dir / "source1.md"
        doc_post = frontmatter.Post("Some doc", type="Reference", title="Doc Title", description="Doc Desc")
        doc_file.write_text(frontmatter.dumps(doc_post), encoding="utf-8")

        write_concept({"name": "Concept 1", "description": "Desc 1"}, "source1.md", concept_dir)

        create_index(okf_dir, doc_dir, concept_dir, entity_dir, definition_dir, table_dir)

        index_file = okf_dir / "index.md"
        assert index_file.exists()

        post = frontmatter.load(index_file)
        assert post.metadata == {"okf_version": "0.2"}  # No type: index in frontmatter
        assert "- [Doc Title](documents/source1.md) - Doc Desc" in post.content
        assert "- [Concept 1](concepts/concept-1.md) - Desc 1" in post.content
        assert "Documents: 1" in post.content
        assert "Concepts: 1" in post.content
        assert "Entities: 0" in post.content

def test_merge_duplicate_sources():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        concept = {
            "name": "Shared Concept",
            "description": "Defined twice"
        }

        # Write first time
        write_concept(concept, "source1.md", tmp_path)
        expected_file = tmp_path / "shared-concept.md"
        assert expected_file.exists()

        post1 = frontmatter.load(expected_file)
        assert len(post1.metadata["sources"]) == 1
        assert post1.metadata["sources"][0]["id"] == "source1"
        assert post1.metadata["sources"][0]["resource"] == "/documents/source1.md"

        # Write second time with same source_file - should not duplicate
        write_concept(concept, "source1.md", tmp_path)
        post2 = frontmatter.load(expected_file)
        assert len(post2.metadata["sources"]) == 1

        # Write third time with different source_file - should merge and handle suffix for id conflict
        write_concept(concept, "source1.md", tmp_path) # same source file & resource, won't add
        # Actually let's use a source file with same stem but in subdirectory to trigger ID collision with different resource
        write_concept(concept, "subdir/source1.md", tmp_path)
        post3 = frontmatter.load(expected_file)
        assert len(post3.metadata["sources"]) == 2
        assert post3.metadata["sources"][0]["id"] == "source1"
        assert post3.metadata["sources"][1]["id"] == "source1-2"
        assert post3.metadata["sources"][1]["resource"] == "/documents/subdir/source1.md"
