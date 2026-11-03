"""The SQLite file is created only when something actually reads or writes it."""

from __future__ import annotations

from pathlib import Path

import pytest

from localmind import cli
from localmind.storage import Storage


@pytest.fixture()
def home(tmp_path: Path, monkeypatch) -> Path:
    home = tmp_path / "home"
    monkeypatch.setenv("LOCALMIND_HOME", str(home))
    monkeypatch.setenv("LOCALMIND_FILE_SEARCH_DIR", str(tmp_path / "files"))
    monkeypatch.delenv("LOCALMIND_DB", raising=False)
    monkeypatch.delenv("LOCALMIND_CONFIG", raising=False)
    monkeypatch.delenv("LOCALMIND_PROVIDER", raising=False)
    monkeypatch.delenv("LOCALMIND_SKILLS_DIR", raising=False)
    return home


def test_config_and_skills_do_not_create_db(home: Path, capsys):
    assert cli.main(["config"]) == 0
    assert cli.main(["skills"]) == 0
    assert not (home / "localmind.db").exists()

    assert cli.main(["--once", "add note x"]) == 0
    assert "Saved note #1: x" in capsys.readouterr().out
    assert (home / "localmind.db").exists()


def test_config_reports_db_path_without_creating_it(home: Path, capsys):
    cli.main(["config"])
    out = capsys.readouterr().out
    assert str(home / "localmind.db") in out
    assert not (home / "localmind.db").exists()


def test_storage_opens_on_first_use(tmp_path: Path):
    db = tmp_path / "sub" / "lm.db"
    store = Storage(str(db))
    assert not db.exists()
    store.add_note("x")
    assert db.exists()
    store.close()


def test_close_without_use_is_safe(tmp_path: Path):
    db = tmp_path / "lm.db"
    store = Storage(str(db))
    store.close()
    store.close()
    assert not db.exists()


def test_context_manager_without_use(tmp_path: Path):
    db = tmp_path / "lm.db"
    with Storage(str(db)):
        pass
    assert not db.exists()
