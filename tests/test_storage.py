"""Tests for the SQLite storage layer, including persistence roundtrips."""

from __future__ import annotations

from localmind.storage import Storage


def test_note_roundtrip(storage: Storage):
    note_id = storage.add_note("buy milk")
    assert note_id > 0
    notes = storage.list_notes()
    assert len(notes) == 1
    assert notes[0]["text"] == "buy milk"


def test_note_search(storage: Storage):
    storage.add_note("buy milk")
    storage.add_note("call dentist")
    results = storage.search_notes("milk")
    assert len(results) == 1
    assert "milk" in results[0]["text"]
    # Case-insensitive.
    assert len(storage.search_notes("MILK")) == 1


def test_reminder_roundtrip(storage: Storage):
    rid = storage.add_reminder("call mom", due="5pm")
    rows = storage.list_reminders()
    assert len(rows) == 1
    assert rows[0]["text"] == "call mom"
    assert rows[0]["due"] == "5pm"
    assert storage.complete_reminder(rid) is True
    # After completing, it is no longer in the default (pending) list.
    assert storage.list_reminders() == []
    assert len(storage.list_reminders(include_done=True)) == 1


def test_history_roundtrip(storage: Storage):
    storage.add_history("user", "hello")
    storage.add_history("assistant", "hi there", skill=None)
    hist = storage.list_history()
    assert [h["role"] for h in hist] == ["user", "assistant"]
    assert hist[1]["content"] == "hi there"


def test_persistence_between_connections(tmp_db: str):
    """Data written by one connection is visible to a fresh one (persists)."""
    first = Storage(tmp_db)
    first.add_note("persisted note")
    first.close()

    second = Storage(tmp_db)
    notes = second.list_notes()
    second.close()

    assert len(notes) == 1
    assert notes[0]["text"] == "persisted note"
