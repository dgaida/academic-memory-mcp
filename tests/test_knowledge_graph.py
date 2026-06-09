import pytest
from unittest.mock import MagicMock
import json
from mcp_university.metadata.store import MetadataStore
from mcp_university.knowledge_graph.engine import KnowledgeGraphEngine
from mcp_university.summarizer.engine import Summarizer

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_university.db"
    return MetadataStore(db_path)

@pytest.fixture
def mock_summarizer():
    summarizer = MagicMock(spec=Summarizer)
    return summarizer

def test_knowledge_graph_extraction(temp_db, mock_summarizer):
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

    engine.process_summary("Dummy summary content", user_node_id)

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
    temp_db.upsert_node("Test Person", "Person", {"role": ["Studierender"]})
    node = temp_db.get_all_nodes()[0]
    assert json.loads(node['properties_json']) == {"role": ["Studierender"]}

    # Update properties
    temp_db.upsert_node("Test Person", "Person", {"role": ["Studierender", "SHK"]})
    node = temp_db.get_all_nodes()[0]
    assert json.loads(node['properties_json']) == {"role": ["Studierender", "SHK"]}
