"""Tests for test_edge_replacement.py."""
"""Tests für die Kanten-Ersetzungslogik im Wissensgraphen."""
import pytest
from unittest.mock import MagicMock
import json
from mcp_university.metadata.store import MetadataStore
from mcp_university.knowledge_graph.engine import KnowledgeGraphEngine
from mcp_university.summarizer.engine import Summarizer
from mcp_university.config import OntologyConfig

@pytest.fixture
def temp_db(tmp_path):
    """Erstellt eine temporäre Datenbank für Tests."""
    db_path = tmp_path / "test_university.db"
    return MetadataStore(db_path)

@pytest.fixture
def mock_summarizer():
    """Erstellt einen Mock-Summarizer."""
    summarizer = MagicMock(spec=Summarizer)
    return summarizer

def test_edge_replacement_logic(temp_db, mock_summarizer) -> None:
    """Tests test_edge_replacement_logic."""
    """Testet, ob Kanten mit niedrigerer Priorität durch solche mit höherer ersetzt werden."""
    ontology = OntologyConfig(
        node_types=["Person", "Modul"],
        edge_types=[
            "hat Bachelorarbeit angefragt",
            "schreibt Bachelorarbeit",
            "hat Bachelorarbeit abgeschlossen"
        ],
        edge_priorities={
            "Bachelorarbeit": [
                "hat Bachelorarbeit angefragt",
                "schreibt Bachelorarbeit",
                "hat Bachelorarbeit abgeschlossen"
            ]
        }
    )
    engine = KnowledgeGraphEngine(temp_db, mock_summarizer, ontology=ontology)

    # 1. Add "angefragt"
    mock_triplets = [{
        "source": "Max", "target": "Thema", "relation": "hat Bachelorarbeit angefragt",
        "source_type": "Person", "target_type": "Person"
    }]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)
    engine.process_summary("Summary 1", 1)

    edges = temp_db.get_all_edges()
    assert len(edges) == 1
    assert edges[0]['relation_type'] == "hat Bachelorarbeit angefragt"

    # 2. Add "schreibt" -> should replace "angefragt"
    mock_triplets = [{
        "source": "Max", "target": "Thema", "relation": "schreibt Bachelorarbeit",
        "source_type": "Person", "target_type": "Person"
    }]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)
    engine.process_summary("Summary 2", 1)

    edges = temp_db.get_all_edges()
    assert len(edges) == 1
    assert edges[0]['relation_type'] == "schreibt Bachelorarbeit"

    # 3. Add "abgeschlossen" -> should replace "schreibt"
    mock_triplets = [{
        "source": "Max", "target": "Thema", "relation": "hat Bachelorarbeit abgeschlossen",
        "source_type": "Person", "target_type": "Person"
    }]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)
    engine.process_summary("Summary 3", 1)

    edges = temp_db.get_all_edges()
    assert len(edges) == 1
    assert edges[0]['relation_type'] == "hat Bachelorarbeit abgeschlossen"

def test_edge_downgrade_ignored(temp_db, mock_summarizer) -> None:
    """Tests test_edge_downgrade_ignored."""
    """Testet, ob Kanten mit niedrigerer Priorität ignoriert werden, wenn eine höhere existiert."""
    ontology = OntologyConfig(
        node_types=["Person"],
        edge_types=["Low", "High"],
        edge_priorities={"Cat": ["Low", "High"]}
    )
    engine = KnowledgeGraphEngine(temp_db, mock_summarizer, ontology=ontology)

    # Add High priority edge
    mock_triplets = [{"source": "A", "target": "B", "relation": "High"}]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)
    engine.process_summary("S1", 1)

    # Try to add Low priority edge
    mock_triplets = [{"source": "A", "target": "B", "relation": "Low"}]
    mock_summarizer._chat_request.return_value = json.dumps(mock_triplets)
    engine.process_summary("S2", 1)

    edges = temp_db.get_all_edges()
    assert len(edges) == 1
    assert edges[0]['relation_type'] == "High"
