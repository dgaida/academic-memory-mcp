"""Metadaten-Speicherung und Verwaltung."""
import sqlite3
import time
from pathlib import Path
from typing import Optional

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
                    name TEXT,
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

    def get_file(self, path: str) -> Optional[tuple]:
        """Ruft Metadaten für eine Datei ab.

        Args:
            path (str): Pfad der Datei.

        Returns:
            Optional[tuple]: Datensatz der Datei oder None.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
            return cursor.fetchone()

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

    def get_folder_files(self, folder_id: int) -> list:
        """Ruft alle Dateien in einem bestimmten Ordner ab.

        Args:
            folder_id (int): ID des Ordners.

        Returns:
            list: Liste der Dateidatensätze.
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

    def update_folder_summarized(self, folder_id: int) -> None:
        """Aktualisiert den Zeitstempel der letzten Zusammenfassung für einen Ordner.

        Args:
            folder_id (int): ID des Ordners.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE folders SET last_summarized = ? WHERE id = ?', (time.time(), folder_id))
            conn.commit()
