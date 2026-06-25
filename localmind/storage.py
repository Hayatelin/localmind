"""SQLite persistence layer for LocalMind.

Everything LocalMind remembers -- notes, reminders and chat history -- lives in
a single SQLite database file on the user's machine. There is no server and no
network access; this module is a thin, well-typed wrapper around the standard
library :mod:`sqlite3`.

The :class:`Storage` class owns one connection and creates its schema lazily on
first use, so callers can simply do::

    store = Storage(path)
    store.add_note("buy milk")
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


def _utcnow() -> str:
    """Return an ISO-8601 UTC timestamp string (used for created/updated cols)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Storage:
    """A small persistence facade over a single SQLite database file."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        # Ensure the parent directory exists (e.g. first run on a fresh machine).
        parent = Path(self.db_path).parent
        if str(parent):
            parent.mkdir(parents=True, exist_ok=True)
        # ``check_same_thread=False`` keeps the simple CLI usable from tests;
        # LocalMind never shares a connection across threads concurrently.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    # -- lifecycle ---------------------------------------------------------
    def _create_schema(self) -> None:
        """Create all tables if they do not yet exist (idempotent)."""
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT    NOT NULL,
                due         TEXT,
                created_at  TEXT    NOT NULL,
                done        INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                role        TEXT    NOT NULL,   -- 'user' or 'assistant'
                content     TEXT    NOT NULL,
                skill       TEXT,               -- which skill handled it, if any
                created_at  TEXT    NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        """Close the underlying connection."""
        self.conn.close()

    # -- context manager support ------------------------------------------
    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # -- notes -------------------------------------------------------------
    def add_note(self, text: str) -> int:
        """Insert a note and return its new row id."""
        cur = self.conn.execute(
            "INSERT INTO notes (text, created_at) VALUES (?, ?)",
            (text, _utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_notes(self, limit: int = 100) -> List[sqlite3.Row]:
        """Return the most recent notes, newest first."""
        return list(
            self.conn.execute(
                "SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)
            )
        )

    def search_notes(self, term: str, limit: int = 100) -> List[sqlite3.Row]:
        """Return notes whose text contains ``term`` (case-insensitive)."""
        like = f"%{term}%"
        return list(
            self.conn.execute(
                "SELECT * FROM notes WHERE text LIKE ? COLLATE NOCASE "
                "ORDER BY id DESC LIMIT ?",
                (like, limit),
            )
        )

    # -- reminders ---------------------------------------------------------
    def add_reminder(self, text: str, due: Optional[str] = None) -> int:
        """Insert a reminder (optionally with a free-form due string)."""
        cur = self.conn.execute(
            "INSERT INTO reminders (text, due, created_at) VALUES (?, ?, ?)",
            (text, due, _utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_reminders(self, include_done: bool = False) -> List[sqlite3.Row]:
        """Return reminders, pending first; optionally include completed ones."""
        if include_done:
            sql = "SELECT * FROM reminders ORDER BY done ASC, id DESC"
            params: Iterable = ()
        else:
            sql = "SELECT * FROM reminders WHERE done = 0 ORDER BY id DESC"
            params = ()
        return list(self.conn.execute(sql, params))

    def complete_reminder(self, reminder_id: int) -> bool:
        """Mark a reminder done; return ``True`` if a row was updated."""
        cur = self.conn.execute(
            "UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    # -- chat history ------------------------------------------------------
    def add_history(self, role: str, content: str, skill: Optional[str] = None) -> int:
        """Append a chat turn to the persistent history/memory table."""
        cur = self.conn.execute(
            "INSERT INTO history (role, content, skill, created_at) "
            "VALUES (?, ?, ?, ?)",
            (role, content, skill, _utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_history(self, limit: int = 50) -> List[sqlite3.Row]:
        """Return the most recent chat turns, oldest first within the window."""
        rows = list(
            self.conn.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
            )
        )
        return list(reversed(rows))
