"""Shared pytest fixtures for the LocalMind test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from localmind.config import Config
from localmind.skills import SkillContext, load_skills
from localmind.storage import Storage


@pytest.fixture()
def tmp_db(tmp_path: Path) -> str:
    """Return a path to a fresh, throwaway SQLite database file."""
    return str(tmp_path / "test.db")


@pytest.fixture()
def storage(tmp_db: str) -> Storage:
    """A Storage instance backed by a temporary database."""
    store = Storage(tmp_db)
    yield store
    store.close()


@pytest.fixture()
def config(tmp_db: str, tmp_path: Path) -> Config:
    """A Config pointing the file_search skill at the temp directory."""
    return Config(
        provider="mock",
        db_path=tmp_db,
        file_search_dir=str(tmp_path),
        config_path=str(tmp_path / "localmind.yaml"),
    )


@pytest.fixture()
def context(storage: Storage, config: Config) -> SkillContext:
    """A SkillContext wired to the temp storage and config."""
    return SkillContext(storage=storage, config=config)


@pytest.fixture()
def skills():
    """All discovered built-in skills."""
    return load_skills()
