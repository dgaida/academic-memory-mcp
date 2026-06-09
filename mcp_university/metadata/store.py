"""Metadaten-Speicherung und Verwaltung."""
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

class MetadataStore:
    """Verwaltet die Metadaten-Persistenz in einer SQLite-Datenbank.

    Speichert Informationen über Dateien, Ordner, Studenten, Deadlines, Zusammenfassungen und Aliase.
    """

    def __init__(self, db_path: Path):
        """Initialisiert den MetadataStore und erstellt die Datenbank falls nicht vorhanden.

        Args:
            db_path (Path): Pfad zur SQLite-Datenbankdatei.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Erstellt eine neue SQLite-Verbindung.

        Returns:
            sqlite3.Connection: Die Datenbankverbindung.
        """
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initialisiert das Datenbankschema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    hash TEXT,
                    mtime REAL,
                    type TEXT,
                    last_indexed REAL,
                    folder_id INTEGER,
                    FOREIGN KEY(folder_id) REFERENCES folders(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    parent_id INTEGER,
                    identity_json TEXT,
                    last_summarized REAL,
                    FOREIGN KEY(parent_id) REFERENCES folders(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT,
                    item_id INTEGER,
                    content TEXT,
                    version INTEGER,
                    created_at REAL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    email TEXT,
                    thesis_topic TEXT,
                    status TEXT,
                    folder_id INTEGER,
                    FOREIGN KEY(folder_id) REFERENCES folders(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deadlines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    due_date REAL,
                    item_type TEXT,
                    item_id INTEGER
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    type TEXT,
                    properties_json TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER,
                    target_id INTEGER,
                    relation_type TEXT,
                    properties_json TEXT,
                    UNIQUE(source_id, target_id, relation_type),
                    FOREIGN KEY(source_id) REFERENCES nodes(id),
                    FOREIGN KEY(target_id) REFERENCES nodes(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alias TEXT UNIQUE,
                    canonical_name TEXT,
                    category TEXT
                )
            ''')
            conn.commit()

    def upsert_file(self, path: str, file_hash: str, mtime: float, file_type: str, folder_id: int = None) -> int:
        """Fügt eine Datei hinzu oder aktualisiert sie."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO files (path, hash, mtime, type, last_indexed, folder_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    hash=excluded.hash,
                    mtime=excluded.mtime,
                    type=excluded.type,
                    last_indexed=excluded.last_indexed,
                    folder_id=COALESCE(excluded.folder_id, files.folder_id)
            ''', (path, file_hash, mtime, file_type, time.time(), folder_id))
            conn.commit()
            cursor.execute('SELECT id FROM files WHERE path = ?', (path,))
            return cursor.fetchone()[0]

    def upsert_folder(self, path: str, parent_id: int = None, identity: Dict[str, Any] = None) -> int:
        """Fügt einen Ordner hinzu oder aktualisiert ihn."""
        identity_json = json.dumps(identity or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO folders (path, parent_id, identity_json)
                VALUES (?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    parent_id=excluded.parent_id,
                    identity_json=excluded.identity_json
            ''', (path, parent_id, identity_json))
            conn.commit()
            cursor.execute('SELECT id FROM folders WHERE path = ?', (path,))
            return cursor.fetchone()[0]

    def add_summary(self, item_type: str, item_id: int, content: str) -> int:
        """Fügt eine neue Zusammenfassung hinzu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(version) FROM summaries WHERE item_type = ? AND item_id = ?', (item_type, item_id))
            row = cursor.fetchone()
            version = (row[0] or 0) + 1

            cursor.execute('''
                INSERT INTO summaries (item_type, item_id, content, version, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_type, item_id, content, version, time.time()))
            conn.commit()
            return cursor.lastrowid

    def get_file_by_path(self, path: str) -> Optional[Tuple]:
        """Ruft eine Datei anhand ihres Pfades ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
            return cursor.fetchone()

    def get_file(self, path: str) -> Optional[Tuple]:
        """Alias für get_file_by_path für Abwärtskompatibilität."""
        return self.get_file_by_path(path)

    def get_folder_by_path(self, path: str) -> Optional[Tuple]:
        """Ruft einen Ordner anhand seines Pfades ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM folders WHERE path = ?', (path,))
            return cursor.fetchone()

    def get_files_in_folder(self, folder_id: int) -> List[Tuple]:
        """Ruft alle Dateien in einem Ordner ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE folder_id = ?', (folder_id,))
            return cursor.fetchall()

    def get_folder_files(self, folder_id: int) -> List[Tuple]:
        """Alias für get_files_in_folder für Abwärtskompatibilität."""
        return self.get_files_in_folder(folder_id)

    def get_all_files(self) -> List[Tuple]:
        """Ruft alle Dateien ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files')
            return cursor.fetchall()

    def get_all_folders(self) -> List[Tuple]:
        """Ruft alle Ordner ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM folders')
            return cursor.fetchall()

    def get_summary(self, item_type: str, item_id: int) -> Optional[str]:
        """Ruft die aktuellste Zusammenfassung für ein Objekt ab."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT content FROM summaries
                WHERE item_type = ? AND item_id = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (item_type, item_id))
            row = cursor.fetchone()
            return row[0] if row else None

    def upsert_student(self, name: str, email: str = None, topic: str = None, status: str = None, folder_id: int = None) -> int:
        """Fügt einen Studenten hinzu oder aktualisiert ihn."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO students (name, email, thesis_topic, status, folder_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    email=COALESCE(excluded.email, students.email),
                    thesis_topic=COALESCE(excluded.thesis_topic, students.thesis_topic),
                    status=COALESCE(excluded.status, students.status),
                    folder_id=COALESCE(excluded.folder_id, students.folder_id)
            """, (name, email, topic, status, folder_id))
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
        """Löscht einen Ordner und dessen Inhalte."""
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

    def update_folder_summarized(self, folder_id: int) -> None:
        """Aktualisiert den Zeitstempel der letzten Zusammenfassung."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE folders SET last_summarized = ? WHERE id = ?', (time.time(), folder_id))
            conn.commit()

    def upsert_node(self, name: str, node_type: str, properties: Dict[str, Any] = None) -> Tuple[int, bool]:
        """Fügt einen Knoten hinzu oder aktualisiert ihn."""
        props_json = json.dumps(properties or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM nodes WHERE name = ?', (name,))
            row = cursor.fetchone()
            is_new = row is None

            cursor.execute('''
                INSERT INTO nodes (name, type, properties_json)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    type=excluded.type,
                    properties_json=excluded.properties_json
            ''', (name, node_type, props_json))
            conn.commit()

            cursor.execute('SELECT id FROM nodes WHERE name = ?', (name,))
            return cursor.fetchone()[0], is_new

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

            cursor.execute('''
                SELECT id FROM edges
                WHERE source_id = ? AND target_id = ? AND relation_type = ?
            ''', (source_id, target_id, relation_type))
            return cursor.fetchone()[0], is_new

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

    def add_alias(self, alias: str, canonical_name: str, category: str) -> None:
        """Fügt ein Alias für einen kanonischen Namen hinzu.

        Args:
            alias (str): Die alternative Schreibweise.
            canonical_name (str): Der bevorzugte/eindeutige Name.
            category (str): 'Person' oder 'Modul'.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO aliases (alias, canonical_name, category)
                VALUES (?, ?, ?)
                ON CONFLICT(alias) DO UPDATE SET
                    canonical_name=excluded.canonical_name,
                    category=excluded.category
            ''', (alias, canonical_name, category))
            conn.commit()

    def resolve_canonical_name(self, name: str, category: str) -> str:
        """Löst einen Namen über die Aliases-Tabelle auf.

        Args:
            name (str): Der aufzulösende Name.
            category (str): Die Kategorie ('Person', 'Modul').

        Returns:
            str: Der kanonische Name oder der ursprüngliche Name, falls kein Alias existiert.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT canonical_name FROM aliases
                WHERE alias = ? AND category = ?
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
