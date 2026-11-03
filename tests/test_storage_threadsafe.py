"""Storage.conn: one connection under concurrent first access, and no
half-initialised connection after a failed schema setup."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from localmind import storage as storage_mod
from localmind.storage import Storage

N_THREADS = 8


def test_concurrent_first_access_opens_one_connection(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALMIND_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("LOCALMIND_DB", raising=False)

    calls = []
    calls_lock = threading.Lock()
    real_connect = sqlite3.connect

    def counting_connect(*args, **kwargs):
        with calls_lock:
            calls.append(args)
        # Widen the race window so an unguarded check-then-open would let
        # several threads through.
        time.sleep(0.05)
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(storage_mod.sqlite3, "connect", counting_connect)

    store = Storage(str(tmp_path / "lm.db"))
    barrier = threading.Barrier(N_THREADS)
    ids = []
    errors = []
    ids_lock = threading.Lock()

    def worker():
        try:
            barrier.wait(timeout=5)
            conn = store.conn
            with ids_lock:
                ids.append(id(conn))
        except BaseException as exc:  # surface failures in the main thread
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    try:
        assert errors == []
        assert len(ids) == N_THREADS
        assert len(set(ids)) == 1
        assert ids[0] == id(store.conn)
        assert len(calls) == 1
    finally:
        store.close()


def test_single_thread_api_unchanged(tmp_path: Path):
    store = Storage(str(tmp_path / "lm.db"))
    first = store.conn
    assert store.conn is first
    nid = store.add_note("buy milk")
    assert [r["text"] for r in store.list_notes()] == ["buy milk"]
    assert nid == 1
    store.close()
    store.close()


def test_not_a_database_raises_every_time(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALMIND_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("LOCALMIND_DB", raising=False)
    db = tmp_path / "bad.db"
    db.write_text("not a database", encoding="utf-8")
    store = Storage(str(db))

    with pytest.raises(sqlite3.DatabaseError):
        store.conn
    assert store._conn is None

    with pytest.raises(sqlite3.DatabaseError):
        store.conn
    assert store._conn is None

    store.close()  # nothing open; must not raise
    assert db.read_text(encoding="utf-8") == "not a database"


def test_schema_exists_after_first_access(tmp_path: Path):
    store = Storage(str(tmp_path / "lm.db"))
    conn = store.conn
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"notes", "reminders", "history"} <= tables
    store.close()
