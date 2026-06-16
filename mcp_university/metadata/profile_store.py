"""Storage for tracking emails used in person profiles."""
import logging
import sqlite3
from pathlib import Path
from typing import List, Set

logger = logging.getLogger(__name__)

class ProfileStore:
    """Manages the tracking of emails used to generate person profiles."""

    def __init__(self, db_path: Path) -> None:
        """Initializes the ProfileStore.

        Args:
            db_path (Path): Path to the SQLite database.
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profile_emails (
                    email_address TEXT,
                    filename TEXT,
                    UNIQUE(email_address, filename)
                )
            ''')
            conn.commit()

    def add_processed_emails(self, email_address: str, filenames: List[str]) -> None:
        """Adds filenames to the list of processed emails for a person.

        Args:
            email_address (str): The person's email address.
            filenames (List[str]): List of email filenames (no path).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for filename in filenames:
                cursor.execute('''
                    INSERT OR IGNORE INTO profile_emails (email_address, filename)
                    VALUES (?, ?)
                ''', (email_address.lower(), filename))
            conn.commit()

    def get_processed_filenames(self, email_address: str) -> Set[str]:
        """Returns a set of filenames already processed for a person.

        Args:
            email_address (str): The person's email address.

        Returns:
            Set[str]: Set of filenames.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT filename FROM profile_emails WHERE email_address = ?
            ''', (email_address.lower(),))
            return {row[0] for row in cursor.fetchall()}
