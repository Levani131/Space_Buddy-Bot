"""Database manager for SpaceBuddy Telegram Bot.

Provides SQLite relational storage for users and saved APOD items conforming to 3NF.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import logging
import os
import sqlite3
from typing import Any, Generator

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database connections, schema initialization, and queries."""

    CREATE_USERS_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT NOT NULL,
        joined_at TEXT NOT NULL
    );
    """

    CREATE_SAVED_APODS_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS saved_apods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        apod_date TEXT NOT NULL,
        title TEXT NOT NULL,
        media_url TEXT NOT NULL,
        saved_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        UNIQUE (user_id, apod_date)
    );
    """

    def __init__(self, db_path: str = "space_buddy.db") -> None:
        """Initialize DatabaseManager with database file path or in-memory mode.

        Args:
            db_path: Path to the SQLite database file, or ':memory:' for transient in-memory DB.
        """
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None

        if self.db_path != ":memory:":
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        else:
            # For in-memory databases, maintain a persistent connection so tables/data persist
            self._connection = self._create_connection()

        self.init_db()

    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection.

        Enforces:
        - Row factory set to sqlite3.Row for dict-like column access
        - PRAGMA foreign_keys = ON;
        - PRAGMA journal_mode = WAL; (when not running in-memory)
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")

        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")

        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Retrieve a configured database connection.

        Returns:
            The persistent connection when db_path is ':memory:', or a new configured connection.
        """
        if self.db_path == ":memory:":
            if self._connection is None:
                self._connection = self._create_connection()
            return self._connection
        return self._create_connection()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a connection that manages atomic transaction commit/rollback and cleanup."""
        conn = self.get_connection()
        try:
            with conn:
                yield conn
        finally:
            if self.db_path != ":memory:":
                conn.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """Property returning the active connection."""
        return self.get_connection()

    @property
    def conn(self) -> sqlite3.Connection:
        """Convenience alias for self.connection."""
        return self.get_connection()

    def init_db(self) -> None:
        """Create 3NF relational tables and performance indexes using DDL if they do not already exist."""
        with self._get_connection() as conn:
            conn.execute(self.CREATE_USERS_TABLE_DDL)
            conn.execute(self.CREATE_SAVED_APODS_TABLE_DDL)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_apods_saved_at ON saved_apods (saved_at DESC);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_apods_user_date ON saved_apods (user_id, apod_date DESC);"
            )
        logger.info("Database initialized successfully with users, saved_apods tables, and indexes.")

    def create_tables(self) -> None:
        """Alias for init_db."""
        self.init_db()

    def close(self) -> None:
        """Close the persistent connection if one is maintained."""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing persistent database connection: {e}")
            finally:
                self._connection = None

    def __enter__(self) -> DatabaseManager:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    # --- CRUD & Analytical Operations ---

    def register_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str,
    ) -> None:
        """Register a user or update an existing user's details without crashing.

        Uses INSERT INTO users ... ON CONFLICT(user_id) DO UPDATE.
        """
        joined_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, username, first_name, joined_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name;
                """,
                (user_id, username, first_name, joined_at),
            )

    def add_user(
        self,
        user_id: int,
        first_name: str,
        username: str | None = None,
        joined_at: str | None = None,
    ) -> None:
        """Convenience alias for register_user."""
        self.register_user(user_id=user_id, username=username, first_name=first_name)

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        """Fetch user by Telegram user_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE user_id = ?;",
                (user_id,),
            )
            return cursor.fetchone()

    def save_apod(
        self,
        user_id: int,
        apod_date: str,
        title: str,
        media_url: str,
    ) -> bool:
        """Save an APOD bookmark for a user using INSERT OR IGNORE.

        Returns:
            True if a new row was inserted (cursor.rowcount > 0),
            False if it was a duplicate or ignored.
        """
        saved_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO saved_apods (user_id, apod_date, title, media_url, saved_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user_id, apod_date, title, media_url, saved_at),
            )
            return cursor.rowcount > 0

    def get_user_favorites(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Return the user's saved APODs ordered by apod_date DESC as a list of dictionaries."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, user_id, apod_date, title, media_url, saved_at
                FROM saved_apods
                WHERE user_id = ?
                ORDER BY apod_date DESC
                LIMIT ?;
                """,
                (user_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_saved_apods(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Alias for get_user_favorites."""
        return self.get_user_favorites(user_id=user_id, limit=limit)

    def delete_favorite(self, user_id: int, apod_date: str) -> bool:
        """Delete a specific bookmark and return True if a row was removed."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM saved_apods WHERE user_id = ? AND apod_date = ?;",
                (user_id, apod_date),
            )
            return cursor.rowcount > 0

    def delete_saved_apod(self, user_id: int, apod_date: str) -> bool:
        """Alias for delete_favorite."""
        return self.delete_favorite(user_id=user_id, apod_date=apod_date)

    def get_recent_community_saves(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return recent community APOD saves joined with users via an INNER JOIN.

        Returns list of dicts with keys: first_name, username, apod_date, title.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT u.first_name, u.username, s.apod_date, s.title
                FROM saved_apods s
                INNER JOIN users u ON s.user_id = u.user_id
                ORDER BY s.saved_at DESC, s.id DESC
                LIMIT ?;
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
