"""Storage.close() takes the same lock as the first open in Storage.conn."""

from __future__ import annotations

import threading
from pathlib import Path

from localmind.storage import Storage


def test_close_waits_for_conn_lock(tmp_path: Path):
    store = Storage(tmp_path / "lm.db")
    store.conn  # open a connection
    done = threading.Event()

    def closer():
        store.close()
        done.set()

    store._conn_lock.acquire()
    try:
        worker = threading.Thread(target=closer)
        worker.start()
        # While the lock is held elsewhere, close() must not finish.
        assert not done.wait(0.3)
        assert store._conn is not None
    finally:
        store._conn_lock.release()
    worker.join(5)
    assert done.is_set()
    assert store._conn is None


def test_concurrent_close_and_open_stay_consistent(tmp_path: Path):
    store = Storage(tmp_path / "lm.db")
    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def worker(index: int):
        try:
            barrier.wait()
            for _ in range(50):
                if index % 2:
                    store.close()
                else:
                    store.conn
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert not errors, errors
    # Whatever the interleaving, the store is still usable afterwards.
    assert store.conn.execute("SELECT 1").fetchone()[0] == 1
    store.close()
    assert store._conn is None


def test_close_is_still_idempotent_and_lazy(tmp_path: Path):
    db = tmp_path / "lm.db"
    store = Storage(db)
    store.close()
    store.close()
    assert not db.exists()
