import sqlite3
import pytest
from mcp_university.metadata.store import MetadataStore

def test_nodes_migration(tmp_path):
    db_path = tmp_path / "test_migration.db"
    # Create old schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT, type TEXT, properties_json TEXT)")
    cursor.execute("INSERT INTO nodes (name, type, properties_json) VALUES ('Test', 'Person', '{}')")
    conn.commit()
    conn.close()
    
    # Initialize store which triggers migration
    store = MetadataStore(db_path)
    
    # Verify new schema has UNIQUE(name, type)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes'")
    sql = cursor.fetchone()[0]
    assert "UNIQUE(name, type)" in sql
    conn.close()

def test_aliases_migration(tmp_path):
    db_path = tmp_path / "test_alias_migration.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE aliases (id INTEGER PRIMARY KEY, alias TEXT, canonical_name TEXT, category TEXT)")
    conn.commit()
    conn.close()
    
    MetadataStore(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='aliases'")
    sql = cursor.fetchone()[0]
    assert "UNIQUE(alias, category)" in sql
    conn.close()
