import pytest
from mcp_university.metadata.store import MetadataStore

@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test.db"
    return MetadataStore(db_path)

def test_upsert_node(store):
    node_id, created = store.upsert_node("Test Node", "Person", {"email": "test@example.com"})
    assert created is True
    assert node_id > 0
    
    node_id2, created2 = store.upsert_node("Test Node", "Person", {"email": "test@example.com", "role": "admin"})
    assert node_id == node_id2
    assert created2 is False

def test_upsert_edge(store):
    id1, _ = store.upsert_node("N1", "T")
    id2, _ = store.upsert_node("N2", "T")
    
    edge_id, created = store.upsert_edge(id1, id2, "WORKS_WITH", {"since": "2020"})
    assert created is True
    assert edge_id > 0
    
    edge_id2, created2 = store.upsert_edge(id1, id2, "WORKS_WITH", {"since": "2021"})
    assert edge_id == edge_id2
    assert created2 is False

def test_get_node_by_id(store):
    node_id, _ = store.upsert_node("Node 1", "Type A")
    node = store.get_node_by_id(node_id)
    assert node['name'] == "Node 1"
    assert store.get_node_by_id(9999) is None

def test_get_node_by_property(store):
    store.upsert_node("Node P", "Type B", {"key": "val"})
    node = store.get_node_by_property("key", "val")
    assert node['name'] == "Node P"

def test_delete_node(store):
    nid, _ = store.upsert_node("To Delete", "T")
    store.delete_node(nid)
    assert store.get_node_by_id(nid) is None

def test_get_outgoing_edges(store):
    id1, _ = store.upsert_node("N1", "T")
    id2, _ = store.upsert_node("N2", "T")
    store.upsert_edge(id1, id2, "REL")
    
    edges = store.get_outgoing_edges(id1)
    assert len(edges) == 1
    assert edges[0]['target_id'] == id2

def test_student_management(store):
    sid = store.upsert_student("Student A", "s@example.com", "Topic", "Active", 1)
    assert sid > 0
    
    students = store.get_all_students()
    assert any(s['name'] == "Student A" for s in students)
    
    store.delete_student(sid)
    assert not any(s['id'] == sid for s in store.get_all_students())

def test_folder_management(store):
    fid = store.upsert_folder("path/to/folder", None)
    assert fid > 0
    
    folders = store.get_all_folders()
    assert any(f['path'] == "path/to/folder" for f in folders)
    
    store.delete_folder(fid)
    assert not any(f['id'] == fid for f in store.get_all_folders())

def test_summary_management(store):
    store.add_summary("folder", 1, "Content here")
    
    summaries = store.get_all_summaries()
    assert any(s['content'] == "Content here" for s in summaries)
    
    smid = summaries[0]['id']
    store.delete_summary(smid)
    assert not any(s['id'] == smid for s in store.get_all_summaries())

def test_alias_management(store):
    store.add_alias("Alias", "Real Name", "Category")
    name = store.resolve_canonical_name("Alias", "Category")
    assert name == "Real Name"
    
    aliases = store.get_all_aliases()
    assert any(a['alias'] == "Alias" for a in aliases)

def test_file_management(store):
    fid = store.upsert_file("test.txt", "hash1", 123.0, "text")
    assert fid > 0
    
    file_info = store.get_file("test.txt")
    assert file_info[1] == "test.txt"
    
    store.delete_file(fid)
    assert store.get_file("test.txt") is None
