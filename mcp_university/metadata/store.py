import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

class MetadataStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Files table
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

            # Folders table
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

            # Entities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT,
                    metadata_json TEXT
                )
            ''')

            # Relationships
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT,
                    source_id INTEGER,
                    target_type TEXT,
                    target_id INTEGER,
                    relation_type TEXT
                )
            ''')

            # Summaries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT, -- 'file' or 'folder'
                    item_id INTEGER,
                    content TEXT,
                    version INTEGER,
                    created_at REAL
                )
            ''')

            # Specific tables for University context
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

    def upsert_file(self, path: str, file_hash: str, mtime: float, file_type: str, folder_id: Optional[int] = None):
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

    def get_file(self, path: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
            return cursor.fetchone()

    def upsert_folder(self, path: str, parent_id: Optional[int] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO folders (path, parent_id)
                VALUES (?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    parent_id=excluded.parent_id
            ''', (path, parent_id))
            conn.commit()
            # If conflict, we need to fetch the ID manually
            cursor.execute('SELECT id FROM folders WHERE path = ?', (path,))
            return cursor.fetchone()[0]

    def add_summary(self, item_type: str, item_id: int, content: str):
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO summaries (item_type, item_id, content, created_at)
                VALUES (?, ?, ?, ?)
            ''', (item_type, item_id, content, time.time()))
            conn.commit()
