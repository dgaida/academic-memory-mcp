"""Knowledge Graph storage and management."""
import logging
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class KnowledgeGraphStore:
    """Manages the Knowledge Graph persistence in a SQLite database.

    Stores nodes, aliases, and edges.
    """

    def __init__(self, db_path: Path) -> None:
        """Initializes the KnowledgeGraphStore and creates the database if not exists.

        Args:
            db_path (Path): Path to the SQLite database file.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a new SQLite connection.

        Returns:
            sqlite3.Connection: The database connection.
        """
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initializes the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Migration: nodes table
            cursor.execute("PRAGMA table_info(nodes)")
            cols = [c[1] for c in cursor.fetchall()]
            if cols:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes'")
                res = cursor.fetchone()
                if res and "UNIQUE(name, type)" not in res[0]:
                    logger.info("Migrating nodes table to composite unique constraint...")
                    cursor.execute("ALTER TABLE nodes RENAME TO nodes_old")
                    cursor.execute('''
                        CREATE TABLE nodes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            type TEXT,
                            properties_json TEXT,
                            UNIQUE(name, type)
                        )
                    ''')
                    cursor.execute("INSERT INTO nodes (id, name, type, properties_json) SELECT id, name, type, properties_json FROM nodes_old")
                    cursor.execute("DROP TABLE nodes_old")

            # Migration: aliases table
            cursor.execute("PRAGMA table_info(aliases)")
            cols = [c[1] for c in cursor.fetchall()]
            if cols:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='aliases'")
                res = cursor.fetchone()
                if res and "UNIQUE(alias, category)" not in res[0]:
                    logger.info("Migrating aliases table to composite unique constraint...")
                    cursor.execute("ALTER TABLE aliases RENAME TO aliases_old")
                    cursor.execute('''
                       CREATE TABLE aliases (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           alias TEXT,
                           canonical_name TEXT,
                           category TEXT,
                           UNIQUE(alias, category)
                       )
                    ''')
                    cursor.execute("INSERT INTO aliases (id, alias, canonical_name, category) SELECT id, alias, canonical_name, category FROM aliases_old")
                    cursor.execute("DROP TABLE aliases_old")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT,
                    properties_json TEXT,
                    UNIQUE(name, type)
                )
            ''')

            cursor.execute('''
               CREATE TABLE IF NOT EXISTS aliases (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   alias TEXT,
                   canonical_name TEXT,
                   category TEXT,
                   UNIQUE(alias, category)
               )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER,
                    target_id INTEGER,
                    relation_type TEXT,
                    properties_json TEXT,
                    FOREIGN KEY(source_id) REFERENCES nodes(id),
                    FOREIGN KEY(target_id) REFERENCES nodes(id),
                    UNIQUE(source_id, target_id, relation_type)
                )
            ''')

            conn.commit()

    def upsert_node(self, name: str, node_type: str, properties: Dict[str, Any] = None) -> Tuple[int, bool]:
        """Fügt einen Knoten hinzu oder aktualisiert ihn."""
        props_json = json.dumps(properties or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM nodes WHERE name = ? AND type = ?', (name, node_type))
            row = cursor.fetchone()
            is_new = row is None

            cursor.execute('''
                INSERT INTO nodes (name, type, properties_json)
                VALUES (?, ?, ?)
                ON CONFLICT(name, type) DO UPDATE SET
                    type=excluded.type,
                    properties_json=excluded.properties_json
            ''', (name, node_type, props_json))
            conn.commit()

            if is_new:
                cursor.execute('SELECT id FROM nodes WHERE name = ? AND type = ?', (name, node_type))
                return cursor.fetchone()[0], True
            else:
                return row[0], False

    def upsert_edge(self, source_id: int, target_id: int, relation_type: str, properties: Dict[str, Any] = None) -> Tuple[int, bool]:
        """Fügt eine Kante hinzu oder aktualisiert sie."""
        props_json = json.dumps(properties or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM edges
                WHERE source_id = ? AND target_id = ? AND relation_type = ?
            ''', (source_id, target_id, relation_type))
            row = cursor.fetchone()
            is_new = row is None

            cursor.execute('''
                INSERT INTO edges (source_id, target_id, relation_type, properties_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relation_type) DO UPDATE SET
                    properties_json=excluded.properties_json
            ''', (source_id, target_id, relation_type, props_json))
            conn.commit()

            if is_new:
                cursor.execute('''
                    SELECT id FROM edges
                    WHERE source_id = ? AND target_id = ? AND relation_type = ?
                ''', (source_id, target_id, relation_type))
                return cursor.fetchone()[0], True
            else:
                return row[0], False

    def get_node_by_id(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Ruft einen Knoten anhand seiner ID ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM nodes WHERE id = ?', (node_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_node_by_property(self, key: str, value: Any) -> Optional[Dict[str, Any]]:
        """Sucht einen Knoten basierend auf einer Eigenschaft in properties_json."""
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

    def add_alias(self, alias: str, canonical_name: str, category: str) -> None:
        """Fügt ein Alias für einen kanonischen Namen hinzu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO aliases (alias, canonical_name, category)
                           VALUES (?, ?, ?) ON CONFLICT(alias, category) DO
                           UPDATE SET
                               canonical_name=excluded.canonical_name,
                               category=excluded.category
                           ''', (alias, canonical_name, category))
            conn.commit()

    def resolve_canonical_name(self, name: str, category: str) -> str:
        """Löst einen Namen über die Aliases-Tabelle auf."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT canonical_name
                           FROM aliases
                           WHERE alias = ?
                             AND category = ?
                           ''', (name, category))
            row = cursor.fetchone()
            return row[0] if row else name

    def get_all_aliases(self) -> List[Dict[str, Any]]:
        """Ruft alle Aliase ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM aliases')
            return [dict(row) for row in cursor.fetchall()]

    def get_outgoing_edges(self, node_id: int) -> List[Dict[str, Any]]:
        """Ruft alle ausgehenden Kanten eines Knotens ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM edges WHERE source_id = ?', (node_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_edges(self) -> List[Dict[str, Any]]:
        """Ruft alle Kanten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM edges')
            return [dict(row) for row in cursor.fetchall()]

    def get_edges_between_nodes(self, source_id: int, target_id: int) -> List[Dict[str, Any]]:
        """Ruft alle Kanten zwischen zwei Knoten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM edges
                WHERE source_id = ? AND target_id = ?
            ''', (source_id, target_id))
            return [dict(row) for row in cursor.fetchall()]


    def delete_node(self, node_id: int) -> None:
        """Löscht einen Knoten und alle zugehörigen Kanten."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Kanten löschen
            cursor.execute('DELETE FROM edges WHERE source_id = ? OR target_id = ?', (node_id, node_id))
            # Knoten löschen
            cursor.execute('DELETE FROM nodes WHERE id = ?', (node_id,))
            conn.commit()


    def delete_edge_by_id(self, edge_id: int) -> None:
        """Löscht eine Kante anhand ihrer ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM edges WHERE id = ?', (edge_id,))
            conn.commit()

    def delete_edge(self, source_id: int, target_id: int, relation_type: str) -> None:
        """Löscht eine spezifische Kante zwischen zwei Knoten."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM edges
                WHERE source_id = ? AND target_id = ? AND relation_type = ?
            ''', (source_id, target_id, relation_type))
            conn.commit()
