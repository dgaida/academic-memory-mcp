"""Metadaten-Speicherung und Verwaltung."""
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

class MetadataStore:
    """Verwaltet die Metadaten-Persistenz in einer SQLite-Datenbank.

    Speichert Informationen über Dateien, Ordner, Studenten, Deadlines und Zusammenfassungen.
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
                    FOREIGN KEY(source_id) REFERENCES nodes(id),
                    FOREIGN KEY(target_id) REFERENCES nodes(id),
                    UNIQUE(source_id, target_id, relation_type)
                )
            ''')

            conn.commit()

    def upsert_file(self, path: str, file_hash: str, mtime: float, file_type: str, folder_id: Optional[int] = None) -> int:
        """Fügt eine Datei hinzu oder aktualisiert sie.

        Args:
            path (str): Absoluter Pfad zur Datei.
            file_hash (str): SHA-256 Hash des Inhalts.
            mtime (float): Letzte Änderungszeit.
            file_type (str): Dateiendung.
            folder_id (Optional[int]): ID des übergeordneten Ordners.

        Returns:
            int: Die ID des Datensatzes.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO files (path, hash, mtime, type, folder_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    hash=excluded.hash,
                    mtime=excluded.mtime,
                    type=excluded.type,
                    folder_id=excluded.folder_id
            ''', (path, file_hash, mtime, file_type, folder_id))
            conn.commit()
            return cursor.lastrowid

    def get_file(self, path: str) -> Optional[Tuple]:
        """Ruft Metadaten für eine Datei ab (Legacy-Format: Tuple).

        Args:
            path (str): Pfad der Datei.

        Returns:
            Optional[Tuple]: Datensatz der Datei oder None.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
            return cursor.fetchone()

    def get_all_files(self) -> List[Dict[str, Any]]:
        """Ruft alle Dateien ab.

        Returns:
            List[Dict[str, Any]]: Liste aller Dateien als Dictionaries.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files')
            return [dict(row) for row in cursor.fetchall()]

    def upsert_folder(self, path: str, parent_id: Optional[int] = None) -> int:
        """Fügt einen Ordner hinzu oder aktualisiert ihn.

        Args:
            path (str): Pfad zum Ordner.
            parent_id (Optional[int]): ID des übergeordneten Ordners.

        Returns:
            int: Die ID des Ordners.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO folders (path, parent_id)
                VALUES (?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    parent_id=excluded.parent_id
            ''', (path, parent_id))
            conn.commit()
            cursor.execute('SELECT id FROM folders WHERE path = ?', (path,))
            return cursor.fetchone()[0]

    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Ruft alle Ordner ab.

        Returns:
            List[Dict[str, Any]]: Liste aller Ordner als Dictionaries.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM folders')
            return [dict(row) for row in cursor.fetchall()]

    def add_summary(self, item_type: str, item_id: int, content: str) -> None:
        """Speichert eine Zusammenfassung für eine Datei oder einen Ordner.

        Args:
            item_type (str): 'file' oder 'folder'.
            item_id (int): Die ID des Zielobjekts.
            content (str): Der Text der Zusammenfassung.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO summaries (item_type, item_id, content, created_at)
                VALUES (?, ?, ?, ?)
            ''', (item_type, item_id, content, time.time()))
            conn.commit()

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """Ruft alle Zusammenfassungen ab.

        Returns:
            List[Dict[str, Any]]: Liste aller Zusammenfassungen als Dictionaries.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM summaries')
            return [dict(row) for row in cursor.fetchall()]

    def get_folder_files(self, folder_id: int) -> List[Tuple]:
        """Ruft alle Dateien in einem bestimmten Ordner ab (Legacy-Format: Tuple).

        Args:
            folder_id (int): ID des Ordners.

        Returns:
            List[Tuple]: Liste der Dateidatensätze.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE folder_id = ?', (folder_id,))
            return cursor.fetchall()

    def get_summary(self, item_type: str, item_id: int) -> Optional[str]:
        """Ruft die aktuellste Zusammenfassung für ein Objekt ab.

        Args:
            item_type (str): 'file' oder 'folder'.
            item_id (int): Die ID des Objekts.

        Returns:
            Optional[str]: Der Inhalt der Zusammenfassung oder None.
        """
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
        """Fügt einen Studenten hinzu oder aktualisiert ihn.

        Args:
            name (str): Name des Studenten.
            email (str): Email-Adresse.
            topic (str): Thema der Abschlussarbeit.
            status (str): Aktueller Status.
            folder_id (int): ID des zugehörigen Ordners.

        Returns:
            int: Die ID des Studenten.
        """
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
        """Ruft alle Studenten ab.

        Returns:
            List[Dict[str, Any]]: Liste aller Studenten als Dictionaries.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM students')
            return [dict(row) for row in cursor.fetchall()]

    def get_all_deadlines(self) -> List[Dict[str, Any]]:
        """Ruft alle Deadlines ab.

        Returns:
            List[Dict[str, Any]]: Liste aller Deadlines als Dictionaries.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM deadlines')
            return [dict(row) for row in cursor.fetchall()]

    def delete_file(self, file_id: int) -> None:
        """Löscht eine Datei und ihre Zusammenfassungen aus der Datenbank.

        Args:
            file_id (int): ID der Datei.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM summaries WHERE item_type = "file" AND item_id = ?', (file_id,))
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
            conn.commit()

    def delete_folder(self, folder_id: int) -> None:
        """Löscht einen Ordner, alle darin enthaltenen Dateien und deren Zusammenfassungen.

        Args:
            folder_id (int): ID des Ordners.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Finde alle Dateien im Ordner
            cursor.execute('SELECT id FROM files WHERE folder_id = ?', (folder_id,))
            file_ids = [row[0] for row in cursor.fetchall()]

            # Lösche alle Dateien (und deren Zusammenfassungen)
            for f_id in file_ids:
                cursor.execute('DELETE FROM summaries WHERE item_type = "file" AND item_id = ?', (f_id,))
                cursor.execute('DELETE FROM files WHERE id = ?', (f_id,))

            # Lösche Zusammenfassungen des Ordners
            cursor.execute('DELETE FROM summaries WHERE item_type = "folder" AND item_id = ?', (folder_id,))

            # Lösche den Ordner selbst
            cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
            conn.commit()

    def delete_student(self, student_id: int) -> None:
        """Löscht einen Studenten aus der Datenbank.

        Args:
            student_id (int): ID des Studenten.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()

    def delete_deadline(self, deadline_id: int) -> None:
        """Löscht eine Deadline aus der Datenbank.

        Args:
            deadline_id (int): ID der Deadline.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM deadlines WHERE id = ?', (deadline_id,))
            conn.commit()

    def delete_summary(self, summary_id: int) -> None:
        """Löscht eine Zusammenfassung aus der Datenbank.

        Args:
            summary_id (int): ID der Zusammenfassung.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM summaries WHERE id = ?', (summary_id,))
            conn.commit()

    def update_folder_summarized(self, folder_id: int) -> None:
        """Aktualisiert den Zeitstempel der letzten Zusammenfassung für einen Ordner.

        Args:
            folder_id (int): ID des Ordners.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE folders SET last_summarized = ? WHERE id = ?', (time.time(), folder_id))
            conn.commit()

    def upsert_node(self, name: str, node_type: str, properties: Dict[str, Any] = None) -> Tuple[int, bool]:
        """Fügt einen Knoten hinzu oder aktualisiert ihn.

        Args:
            name (str): Name des Knotens.
            node_type (str): Typ des Knotens (Person, Modul, Unternehmen).
            properties (Dict[str, Any]): Zusätzliche Eigenschaften.

        Returns:
            Tuple[int, bool]: Die ID des Knotens und ob er neu erstellt wurde.
        """
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

            if is_new:
                cursor.execute('SELECT id FROM nodes WHERE name = ?', (name,))
                return cursor.fetchone()[0], True
            else:
                return row[0], False

    def upsert_edge(self, source_id: int, target_id: int, relation_type: str, properties: Dict[str, Any] = None) -> Tuple[int, bool]:
        """Fügt eine Kante hinzu oder aktualisiert sie.

        Args:
            source_id (int): ID des Startknotens.
            target_id (int): ID des Zielknotens.
            relation_type (str): Typ der Beziehung.
            properties (Dict[str, Any]): Zusätzliche Eigenschaften.

        Returns:
            Tuple[int, bool]: Die ID der Kante und ob sie neu erstellt wurde.
        """
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

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Ruft alle Knoten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM nodes')
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
                           VALUES (?, ?, ?) ON CONFLICT(alias) DO
                           UPDATE SET
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

    def get_all_edges(self) -> List[Dict[str, Any]]:
        """Ruft alle Kanten ab."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM edges')
            return [dict(row) for row in cursor.fetchall()]
