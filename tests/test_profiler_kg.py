import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import json
from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def mock_store():
    store = MagicMock()
    return store

@pytest.fixture
def profiler(mock_store):
    with patch('mcp_university.summarizer.profiler.KnowledgeGraphStore', return_value=mock_store):
        with patch('mcp_university.summarizer.profiler.LLMClientWrapper'):
            with patch('mcp_university.summarizer.profiler.MailParser'):
                p = PersonProfiler(storage_path=Path("test_profiles"))
                return p

def test_get_knowledge_graph_context(profiler, mock_store):
    email = "test@example.com"

    # Mock data
    person_node = {"id": 1, "name": "Test Person", "type": "Person", "properties_json": json.dumps({"email": email})}
    inst_node = {"id": 2, "name": "Test Institut", "type": "Institut", "properties_json": json.dumps({})}
    fac_node = {"id": 3, "name": "Test Fakultät", "type": "Fakultät", "properties_json": json.dumps({})}

    # Configure mock store
    mock_store.get_node_by_property.side_effect = lambda k, v: person_node if k == "email" and v == email else None

    def get_node_by_id(node_id):
        if node_id == 1:
            return person_node
        if node_id == 2:
            return inst_node
        if node_id == 3:
            return fac_node
        return None
    mock_store.get_node_by_id.side_effect = get_node_by_id

    def get_outgoing_edges(node_id):
        if node_id == 1:
            return [{"target_id": 2, "relation_type": "ist Element von"}]
        if node_id == 2:
            return [{"target_id": 3, "relation_type": "ist Element von"}]
        return []
    mock_store.get_outgoing_edges.side_effect = get_outgoing_edges

    context = profiler._get_knowledge_graph_context(email)

    assert "Informationen aus dem Wissensgraphen" in context
    assert "Test Person (Person)" in context
    assert "Test Institut (Institut)" in context
    assert "Test Fakultät (Fakultät)" in context
    # Check indentation (DFS might visit in different order depending on pop, but here it's linear)
    assert "- Test Person (Person)" in context
    assert "  - Test Institut (Institut)" in context
    assert "    - Test Fakultät (Fakultät)" in context

def test_profiling_prompt_includes_kg(profiler):
    email = "test@example.com"
    kg_context = "KG INFO"
    new_content = "MAIL CONTENT"
    existing_profile = ""

    prompt = profiler._get_profiling_prompt(email, new_content, existing_profile, kg_context)

    assert "KG INFO" in prompt
    assert "Hier sind die neuen E-Mails:" in prompt
    assert "MAIL CONTENT" in prompt
