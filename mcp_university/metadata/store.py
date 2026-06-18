"""Metadaten-Speicherung und Verwaltung für lokale Dateien und studentische Beziehungen."""
import logging
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class MetadataStore:
    """Verwaltet Metadaten und studentische Verbindungen in einer SQLite-Datenbank."""

    def __init__(self, db_path: Path) -> None:
        """Initialisiert den MetadataStore."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Erstellt eine neue SQLite-Verbindung."""
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initialisiert das Datenbankschema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT UNIQUE, hash TEXT, mtime REAL, type TEXT, last_indexed REAL, folder_id INTEGER)')
            cursor.execute('CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT UNIQUE, parent_id INTEGER, identity_json TEXT, last_summarized REAL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS summaries (id INTEGER PRIMARY KEY AUTOINCREMENT, item_type TEXT, item_id INTEGER, content TEXT, version INTEGER, created_at REAL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, email TEXT, thesis_topic TEXT, status TEXT, folder_id INTEGER)')
            cursor.execute('CREATE TABLE IF NOT EXISTS deadlines (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, due_date REAL, item_type TEXT, item_id INTEGER)')
            cursor.execute('CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, properties_json TEXT, UNIQUE(name, type))')
            cursor.execute('CREATE TABLE IF NOT EXISTS aliases (id INTEGER PRIMARY KEY AUTOINCREMENT, alias TEXT, canonical_name TEXT, category TEXT, UNIQUE(alias, category))')
            cursor.execute('CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER, target_id INTEGER, relation_type TEXT, properties_json TEXT, UNIQUE(source_id, target_id, relation_type))')
            conn.commit()

    def upsert_file(self, path: str, file_hash: str, mtime: float, file_type: str, folder_id: Optional[int] = None) -> int:
        """Fügt eine Datei hinzu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO files (path, hash, mtime, type, folder_id) VALUES (?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET hash=excluded.hash, mtime=excluded.mtime, type=excluded.type, folder_id=excluded.folder_id', (path, file_hash, mtime, file_type, folder_id))
            conn.commit()
            return cursor.lastrowid

    def get_file(self, path: str) -> Optional[Tuple]:
        """Ruft Metadaten ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
            return cursor.fetchone()

    def get_all_files(self) -> List[Dict[str, Any]]:
        """Ruft alle Dateien ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files')
            return [dict(row) for row in cursor.fetchall()]

    def upsert_folder(self, path: str, parent_id: Optional[int] = None) -> int:
        """Fügt Ordner hinzu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO folders (path, parent_id) VALUES (?, ?) ON CONFLICT(path) DO UPDATE SET parent_id=excluded.parent_id', (path, parent_id))
            conn.commit()
            cursor.execute('SELECT id FROM folders WHERE path = ?', (path,))
            return cursor.fetchone()[0]

    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Ruft alle Ordner ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM folders')
            return [dict(row) for row in cursor.fetchall()]

    def add_summary(self, item_type: str, item_id: int, content: str) -> None:
        """Speichert Zusammenfassung."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO summaries (item_type, item_id, content, created_at) VALUES (?, ?, ?, ?)', (item_type, item_id, content, time.time()))
            conn.commit()

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """Ruft alle Zusammenfassungen ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM summaries')
            return [dict(row) for row in cursor.fetchall()]

    def get_folder_files(self, folder_id: int) -> List[Tuple]:
        """Ruft Dateien in Ordner ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE folder_id = ?', (folder_id,))
            return cursor.fetchall()

    def get_summary(self, item_type: str, item_id: int) -> Optional[str]:
        """Ruft aktuellste Zusammenfassung ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT content FROM summaries WHERE item_type = ? AND item_id = ? ORDER BY created_at DESC LIMIT 1', (item_type, item_id))
            row = cursor.fetchone()
            return row[0] if row else None

    def upsert_student(self, name: str, email: str = None, topic: str = None, status: str = None, folder_id: int = None) -> int:
        """Fügt Studenten hinzu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO students (name, email, thesis_topic, status, folder_id) VALUES (?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET email=COALESCE(excluded.email, students.email), thesis_topic=COALESCE(excluded.thesis_topic, students.thesis_topic), status=COALESCE(excluded.status, students.status), folder_id=COALESCE(excluded.folder_id, students.folder_id)", (name, email, topic, status, folder_id))
            conn.commit()
            cursor.execute("SELECT id FROM students WHERE name = ?", (name,))
            return cursor.fetchone()[0]

    def get_all_students(self) -> List[Dict[str, Any]]:
        """Ruft alle Studenten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM students')
            return [dict(row) for row in cursor.fetchall()]

    def get_all_deadlines(self) -> List[Dict[str, Any]]:
        """Ruft alle Deadlines ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM deadlines')
            return [dict(row) for row in cursor.fetchall()]

    def delete_file(self, file_id: int) -> None:
        """Löscht eine Datei."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM summaries WHERE item_type = "file" AND item_id = ?', (file_id,))
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
            conn.commit()

    def delete_folder(self, folder_id: int) -> None:
        """Löscht einen Ordner und alle Dateien."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM files WHERE folder_id = ?', (folder_id,))
            file_ids = [row[0] for row in cursor.fetchall()]
            for f_id in file_ids:
                cursor.execute('DELETE FROM summaries WHERE item_type = "file" AND item_id = ?', (f_id,))
                cursor.execute('DELETE FROM files WHERE id = ?', (f_id,))
            cursor.execute('DELETE FROM summaries WHERE item_type = "folder" AND item_id = ?', (folder_id,))
            cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
            conn.commit()

    def delete_student(self, student_id: int) -> None:
        """Löscht einen Studenten."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()

    def upsert_node(self, name: str, node_type: str, properties: Dict[str, Any] = None) -> Tuple[int, bool]:
        """Fügt Knoten hinzu."""
        props_json = json.dumps(properties or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM nodes WHERE name = ? AND type = ?', (name, node_type))
            row = cursor.fetchone()
            is_new = row is None
            cursor.execute('INSERT INTO nodes (name, type, properties_json) VALUES (?, ?, ?) ON CONFLICT(name, type) DO UPDATE SET properties_json=excluded.properties_json', (name, node_type, props_json))
            conn.commit()
            if is_new:
                cursor.execute('SELECT id FROM nodes WHERE name = ? AND type = ?', (name, node_type))
                return cursor.fetchone()[0], True
            return row[0], False

    def upsert_edge(self, source_id: int, target_id: int, relation_type: str, properties: Dict[str, Any] = None) -> Tuple[int, bool]:
        """Fügt Kante hinzu."""
        props_json = json.dumps(properties or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = ?', (source_id, target_id, relation_type))
            row = cursor.fetchone()
            is_new = row is None
            cursor.execute('INSERT INTO edges (source_id, target_id, relation_type, properties_json) VALUES (?, ?, ?, ?) ON CONFLICT(source_id, target_id, relation_type) DO UPDATE SET properties_json=excluded.properties_json', (source_id, target_id, relation_type, props_json))
            conn.commit()
            if is_new:
                cursor.execute('SELECT id FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = ?', (source_id, target_id, relation_type))
                return cursor.fetchone()[0], True
            return row[0], False

    def get_node_by_id(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Ruft Knoten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM nodes WHERE id = ?', (node_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_node_by_property(self, key: str, value: Any) -> Optional[Dict[str, Any]]:
        """Sucht Knoten."""
        all_nodes = self.get_all_nodes()
        for node in all_nodes:
            props = json.loads(node.get('properties_json', '{}'))
            if props.get(key) == value:
                return node
        return None

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Ruft alle Knoten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM nodes')
            return [dict(row) for row in cursor.fetchall()]

    def get_all_edges(self) -> List[Dict[str, Any]]:
        """Ruft alle Kanten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM edges')
            return [dict(row) for row in cursor.fetchall()]

    def get_outgoing_edges(self, node_id: int) -> List[Dict[str, Any]]:
        """Ruft ausgehende Kanten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM edges WHERE source_id = ?', (node_id,))
            return [dict(row) for row in cursor.fetchall()]

    def resolve_canonical_name(self, name: str, category: str) -> str:
        """Löst Alias auf."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT canonical_name FROM aliases WHERE alias = ? AND category = ?', (name, category))
            row = cursor.fetchone()
            return row[0] if row else name

    def add_alias(self, alias: str, canonical_name: str, category: str) -> None:
        """Fügt Alias hinzu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO aliases (alias, canonical_name, category) VALUES (?, ?, ?) ON CONFLICT(alias, category) DO UPDATE SET canonical_name=excluded.canonical_name', (alias, canonical_name, category))
            conn.commit()

    def delete_node(self, node_id: int) -> None:
        """Löscht Knoten."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM edges WHERE source_id = ? OR target_id = ?', (node_id, node_id))
            cursor.execute('DELETE FROM nodes WHERE id = ?', (node_id,))
            conn.commit()

    def delete_edge(self, source_id: int, target_id: int, relation_type: str) -> None:
        """Löscht Kante."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = ?', (source_id, target_id, relation_type))
            conn.commit()

    def get_edges_between_nodes(self, source_id: int, target_id: int) -> List[Dict[str, Any]]:
        """Ruft Kanten zwischen Knoten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM edges WHERE source_id = ? AND target_id = ?', (source_id, target_id))
            return [dict(row) for row in cursor.fetchall()]
