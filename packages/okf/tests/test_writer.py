import tempfile
from pathlib import Path
import frontmatter
from okf.writer import (
    sanitize_filename,
    write_concept,
    write_entity,
    write_definition,
    write_table,
    create_index,
    find_duplicate_file
)

class MockLLMClient:
    """Mock LLM client to return specific responses for testing duplicate detection."""

    def __init__(self, response_text: str) -> None:
        """Initialize mock LLM client.

        Args:
            response_text: The string response to return from chat_completion.
        """
        self.response_text = response_text
        self.last_messages = None

    def chat_completion(self, messages: list) -> str:
        """Mock chat_completion method.

        Args:
            messages: List of message dictionaries.

        Returns:
            The configured mock response text.
        """
        self.last_messages = messages
        return self.response_text

class MockConfig:
    """Mock configuration containing the mock LLM client."""

    def __init__(self, client: MockLLMClient) -> None:
        """Initialize mock configuration.

        Args:
            client: The mock LLM client instance.
        """
        self.client = client

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

def test_duplicate_case_insensitive_normalized():
    """Verify that normalized title matching works across case/spacing differences."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        concept1 = {
            "name": "Machine Learning",
            "description": "First definition"
        }
        # Write the first one
        write_concept(concept1, "doc1.md", tmp_path)
        expected_file = tmp_path / "machine-learning.md"
        assert expected_file.exists()

        concept2 = {
            "name": "  machine   learning  ",
            "description": "Second definition with slight variation in spacing and case"
        }
        # Write the second one - should detect as duplicate and merge sources
        write_concept(concept2, "doc2.md", tmp_path)

        # Verify that only machine-learning.md exists and has both sources
        files = list(tmp_path.glob("*.md"))
        assert len(files) == 1
        assert files[0].name == "machine-learning.md"

        post = frontmatter.load(files[0])
        assert len(post.metadata["sources"]) == 2
        assert post.metadata["sources"][0]["id"] == "doc1"
        assert post.metadata["sources"][1]["id"] == "doc2"

def test_duplicate_llm_alias_match():
    """Verify that LLM-based duplicate check detects aliases/synonyms and merges correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Write the original entity
        entity1 = {
            "name": "Technische Hochschule Köln",
            "type": "University",
            "description": "A university in Cologne."
        }
        write_entity(entity1, "doc1.md", tmp_path)
        expected_file = tmp_path / "technische-hochschule-k-ln.md"
        assert expected_file.exists()

        # 2. Prepare new entity representing the same institution under an alias
        entity2 = {
            "name": "TH Köln",
            "type": "University",
            "description": "THK is a public university."
        }

        # Setup mock LLM client to return the matching filename
        mock_client = MockLLMClient("technische-hochschule-k-ln.md")
        mock_config = MockConfig(mock_client)

        # 3. Write with config so LLM-based duplicate check is used
        write_entity(entity2, "doc2.md", tmp_path, config=mock_config)

        # 4. Verify that no new file is created, and the existing one is extended
        files = list(tmp_path.glob("*.md"))
        assert len(files) == 1
        assert files[0].name == "technische-hochschule-k-ln.md"

        post = frontmatter.load(files[0])
        assert len(post.metadata["sources"]) == 2
        assert post.metadata["sources"][0]["id"] == "doc1"
        assert post.metadata["sources"][1]["id"] == "doc2"

        # Check that the mock LLM was indeed called with the correct messages
        assert mock_client.last_messages is not None
        assert "Technische Hochschule Köln" in mock_client.last_messages[1]["content"]
        assert "TH Köln" in mock_client.last_messages[1]["content"]

def test_duplicate_llm_no_match():
    """Verify that when the LLM returns 'None', a new file is created normally."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Write the original concept
        concept1 = {
            "name": "Supervised Learning",
            "description": "Learning with labeled data."
        }
        write_concept(concept1, "doc1.md", tmp_path)
        assert (tmp_path / "supervised-learning.md").exists()

        # 2. Write a different concept
        concept2 = {
            "name": "Unsupervised Learning",
            "description": "Learning without labeled data."
        }

        mock_client = MockLLMClient("None")
        mock_config = MockConfig(mock_client)

        write_concept(concept2, "doc2.md", tmp_path, config=mock_config)

        # 3. Verify both files exist
        assert (tmp_path / "supervised-learning.md").exists()
        assert (tmp_path / "unsupervised-learning.md").exists()

        post1 = frontmatter.load(tmp_path / "supervised-learning.md")
        assert len(post1.metadata["sources"]) == 1

        post2 = frontmatter.load(tmp_path / "unsupervised-learning.md")
        assert len(post2.metadata["sources"]) == 1
