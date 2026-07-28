"""Tests for test_metadata_store_extended.py."""
import pytest
from mcp_university.metadata.store import MetadataStore

@pytest.fixture
def store(tmp_path):
    """Test function docstring."""
    db_path = tmp_path / "test.db"
    return MetadataStore(db_path)

def test_upsert_node(store):
    """Test function docstring."""
    node_id, created = store.upsert_node("Test Node", "Person", {"email": "test@example.com"})
    assert created is True
    assert node_id > 0
    
    node_id2, created2 = store.upsert_node("Test Node", "Person", {"email": "test@example.com", "role": "admin"})
    assert node_id == node_id2
    assert created2 is False

def test_upsert_edge(store):
    """Test function docstring."""
    id1, _ = store.upsert_node("N1", "T")
    id2, _ = store.upsert_node("N2", "T")
    
    edge_id, created = store.upsert_edge(id1, id2, "WORKS_WITH", {"since": "2020"})
    assert created is True
    assert edge_id > 0
    
    edge_id2, created2 = store.upsert_edge(id1, id2, "WORKS_WITH", {"since": "2021"})
    assert edge_id == edge_id2
    assert created2 is False

def test_get_node_by_id(store):
    """Test function docstring."""
    node_id, _ = store.upsert_node("Node 1", "Type A")
    node = store.get_node_by_id(node_id)
    assert node['name'] == "Node 1"
    assert store.get_node_by_id(9999) is None

def test_get_node_by_property(store):
    """Test function docstring."""
    store.upsert_node("Node P", "Type B", {"key": "val"})
    node = store.get_node_by_property("key", "val")
    assert node['name'] == "Node P"

def test_delete_node(store):
    """Test function docstring."""
    nid, _ = store.upsert_node("To Delete", "T")
    store.delete_node(nid)
    assert store.get_node_by_id(nid) is None

def test_get_outgoing_edges(store):
    """Test function docstring."""
    id1, _ = store.upsert_node("N1", "T")
    id2, _ = store.upsert_node("N2", "T")
    store.upsert_edge(id1, id2, "REL")
    
    edges = store.get_outgoing_edges(id1)
    assert len(edges) == 1
    assert edges[0]['target_id'] == id2

def test_student_management(store):
    """Test function docstring."""
    sid = store.upsert_student("Student A", "s@example.com", "Topic", "Active", 1)
    assert sid > 0
    
    students = store.get_all_students()
    assert any(s['name'] == "Student A" for s in students)
    
    store.delete_student(sid)
    assert not any(s['id'] == sid for s in store.get_all_students())

def test_folder_management(store):
    """Test function docstring."""
    fid = store.upsert_folder("path/to/folder", None)
    assert fid > 0
    
    folders = store.get_all_folders()
    assert any(f['path'] == "path/to/folder" for f in folders)
    
    store.delete_folder(fid)
    assert not any(f['id'] == fid for f in store.get_all_folders())

def test_summary_management(store):
    """Test function docstring."""
    store.add_summary("folder", 1, "Content here")
    
    summaries = store.get_all_summaries()
    assert any(s['content'] == "Content here" for s in summaries)
    
    smid = summaries[0]['id']
    store.delete_summary(smid)
    assert not any(s['id'] == smid for s in store.get_all_summaries())

def test_alias_management(store):
    """Test function docstring."""
    store.add_alias("Alias", "Real Name", "Category")
    name = store.resolve_canonical_name("Alias", "Category")
    assert name == "Real Name"
    
    aliases = store.get_all_aliases()
    assert any(a['alias'] == "Alias" for a in aliases)

def test_file_management(store):
    """Test function docstring."""
    fid = store.upsert_file("test.txt", "hash1", 123.0, "text")
    assert fid > 0
    
    file_info = store.get_file("test.txt")
    assert file_info[1] == "test.txt"
    
    store.delete_file(fid)
    assert store.get_file("test.txt") is None


def test_deadlines_management(store: MetadataStore) -> None:
    """Tests get_all_deadlines and delete_deadline functions of MetadataStore.

    Args:
        store (MetadataStore): The metadata store fixture.

    Returns:
        None
    """
    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO deadlines (title, due_date, item_type, item_id) VALUES (?, ?, ?, ?)",
            ("Thesis Submission", 1700000000.0, "student", 1)
        )
        conn.commit()

    deadlines = store.get_all_deadlines()
    assert len(deadlines) == 1
    assert deadlines[0]["title"] == "Thesis Submission"

    deadline_id = deadlines[0]["id"]
    store.delete_deadline(deadline_id)

    assert len(store.get_all_deadlines()) == 0


def test_delete_edge_by_id(store: MetadataStore) -> None:
    """Tests delete_edge_by_id function of MetadataStore.

    Args:
        store (MetadataStore): The metadata store fixture.

    Returns:
        None
    """
    id1, _ = store.upsert_node("N1", "T")
    id2, _ = store.upsert_node("N2", "T")
    edge_id, created = store.upsert_edge(id1, id2, "WORKS_WITH", {"since": "2020"})
    assert created is True

    assert len(store.get_all_edges()) == 1
    store.delete_edge_by_id(edge_id)
    assert len(store.get_all_edges()) == 0
