"""Tests for test_knowledge_graph.py."""
import pytest
from unittest.mock import MagicMock
import json
from mcp_university.metadata.store import MetadataStore
from mcp_university.knowledge_graph.engine import KnowledgeGraphEngine
from mcp_university.summarizer.engine import Summarizer

@pytest.fixture
def temp_db(tmp_path):
    """Test function docstring."""
    db_path = tmp_path / "test_university.db"
    return MetadataStore(db_path)

@pytest.fixture
def mock_summarizer():
    """Test function docstring."""
    summarizer = MagicMock(spec=Summarizer)
    return summarizer

def test_knowledge_graph_extraction(temp_db, mock_summarizer):
    """Test function docstring."""
    engine = KnowledgeGraphEngine(temp_db, mock_summarizer)

    # Mock LLM response
    mock_triplets = [
        {
            "source": "Prof. Dr. Müller",
            "target": "Informatik 1",
            "relation": "lehrt",
            "source_type": "Person",
            "target_type": "Modul",
            "properties": {"role": ["Professor"]}
        },
        {
            "source": "Max Mustermann",
            "target": "Informatik 1",
            "relation": "besucht",
            "source_type": "Person",
            "target_type": "Modul",
            "properties": {"role": ["Studierender"]}
        }
    ]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)

    user_node_id, _ = temp_db.upsert_node("Daniel Gaida", "Person", {"role": ["User"]})

    # Run first time (new edges)
    changes = engine.process_summary("Dummy summary content", user_node_id)
    assert len(changes["new_edges"]) == 2

    # Run second time with same mock response to cover line 75 (updated_edges)
    changes2 = engine.process_summary("Dummy summary content", user_node_id)
    assert len(changes2["updated_edges"]) == 2

    nodes = temp_db.get_all_nodes()
    edges = temp_db.get_all_edges()

    assert len(nodes) == 4

    node_names = [n['name'] for n in nodes]
    assert "Prof. Dr. Müller" in node_names
    assert "Informatik 1" in node_names
    assert "Max Mustermann" in node_names
    assert "Daniel Gaida" in node_names

    assert len(edges) == 2
    relations = [e['relation_type'] for e in edges]
    assert "lehrt" in relations
    assert "besucht" in relations

def test_upsert_node_properties(temp_db):
    """Test function docstring."""
    temp_db.upsert_node("Test Person", "Person", {"role": ["Studierender"]})
    node = temp_db.get_all_nodes()[0]
    assert json.loads(node['properties_json']) == {"role": ["Studierender"]}

    # Update properties
    temp_db.upsert_node("Test Person", "Person", {"role": ["Studierender", "SHK"]})
    node = temp_db.get_all_nodes()[0]
    assert json.loads(node['properties_json']) == {"role": ["Studierender", "SHK"]}

def test_dynamic_ontology_prompt(temp_db, mock_summarizer):
    """Test function docstring."""
    from mcp_university.config import OntologyConfig
    custom_ontology = OntologyConfig(
        node_types=["CustomNode"],
        edge_types=["CustomRelation"]
    )
    engine = KnowledgeGraphEngine(temp_db, mock_summarizer, ontology=custom_ontology)

    mock_summarizer._chat_request.return_value = "[]"
    engine.process_summary("Dummy", 1)

    # Get the system prompt passed to the summarizer
    args, kwargs = mock_summarizer._chat_request.call_args
    system_prompt = args[0]

    assert "Knotentypen: CustomNode" in system_prompt
    assert "Beziehungstypen: CustomRelation" in system_prompt
    assert "Nutze NUR die folgenden Knotentypen und Beziehungstypen" in system_prompt

def test_knowledge_graph_missing_triplet_fields(temp_db, mock_summarizer):
    """Test process_summary when triplet field like source, target, or relation is missing.

    Covers line: 47.
    """
    engine = KnowledgeGraphEngine(temp_db, mock_summarizer)

    # Missing source, target, or relation
    mock_triplets = [
        {"source": "", "target": "Informatik 1", "relation": "lehrt"},
        {"source": "A", "target": "", "relation": "lehrt"},
        {"source": "A", "target": "B", "relation": ""}
    ]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)

    changes = engine.process_summary("Dummy", 1)
    assert not changes["new_nodes"]
    assert not changes["new_edges"]

def test_knowledge_graph_should_add_false_and_no_edge_priorities(temp_db, mock_summarizer):
    """Test when should_add is False (replaced/ignored) and edge priorities is empty.

    Covers lines: 75 and 95.
    """
    from mcp_university.config import OntologyConfig
    # 1. Edge priorities configured to test should_add is False (priority ignored)
    ontology_with_priorities = OntologyConfig(
        node_types=["Person", "Modul"],
        edge_types=["betreut", "prüft"],
        edge_priorities={"thesis_relations": ["betreut", "prüft"]} # betreut (index 0) is ignored if prüft (index 1, higher value) exists
    )
    engine = KnowledgeGraphEngine(temp_db, mock_summarizer, ontology=ontology_with_priorities)

    # Create an initial 'prüft' edge (higher priority/index 1)
    source_id, _ = temp_db.upsert_node("Prof. A", "Person")
    target_id, _ = temp_db.upsert_node("Student B", "Person")
    temp_db.upsert_edge(source_id, target_id, "prüft")

    # Try processing a new triplet 'betreut' (lower priority/index 0)
    mock_triplets = [{
        "source": "Prof. A",
        "target": "Student B",
        "relation": "betreut",
        "source_type": "Person",
        "target_type": "Person"
    }]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)

    changes = engine.process_summary("Dummy", 1)
    # Edge was ignored, so it shouldn't be added/updated
    assert not changes["new_edges"]
    assert not changes["updated_edges"]

    # 2. Edge priorities is empty config block
    ontology_no_priorities = OntologyConfig(
        node_types=["Person"],
        edge_types=["betreut"],
        edge_priorities={}
    )
    engine_empty = KnowledgeGraphEngine(temp_db, mock_summarizer, ontology=ontology_no_priorities)
    # _handle_edge_priorities returns True directly (line 95)
    assert engine_empty._handle_edge_priorities(source_id, target_id, "betreut") is True

def test_knowledge_graph_empty_response_and_exception_handling(temp_db, mock_summarizer):
    """Test empty LLM response and invalid JSON exceptions in knowledge graph extraction.

    Covers lines: 145 and 153-156.
    """
    engine = KnowledgeGraphEngine(temp_db, mock_summarizer)

    # 1. Empty Response (line 145)
    mock_summarizer._chat_request.return_value = ""
    changes = engine.process_summary("Dummy", 1)
    assert not changes["new_nodes"]

    # 2. Response with no brackets (line 153)
    mock_summarizer._chat_request.return_value = "No triplets found."
    changes_no_brackets = engine.process_summary("Dummy", 1)
    assert not changes_no_brackets["new_nodes"]

    # 3. Exception / Invalid JSON (lines 154-156)
    mock_summarizer._chat_request.return_value = "[invalid json"
    changes = engine.process_summary("Dummy", 1)
    assert not changes["new_nodes"]
