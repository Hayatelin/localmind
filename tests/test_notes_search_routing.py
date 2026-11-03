"""'find note(s) <term>' goes to the notes skill; 'find <filename>' does not."""

from __future__ import annotations

from pathlib import Path

import pytest

from localmind.assistant import Assistant
from localmind.config import Config
from localmind.providers import MockProvider
from localmind.skills import SkillContext, notes
from localmind.storage import Storage


@pytest.fixture()
def bot(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALMIND_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LOCALMIND_FILE_SEARCH_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("LOCALMIND_DB", str(tmp_path / "lm.db"))
    monkeypatch.delenv("LOCALMIND_SKILLS_DIR", raising=False)
    files = tmp_path / "files"
    files.mkdir()
    (files / "notes.txt").write_text("x", encoding="utf-8")
    (files / "notebook.md").write_text("x", encoding="utf-8")
    config = Config(
        provider="mock",
        db_path=str(tmp_path / "lm.db"),
        file_search_dir=str(files),
    )
    assistant = Assistant(
        config=config, storage=Storage(config.db_path), provider=MockProvider()
    )
    assistant.handle("add note buy milk")
    yield assistant
    assistant.close()


@pytest.mark.parametrize("query", ["find notes milk", "find note milk"])
def test_find_notes_term_routes_to_notes(bot: Assistant, query: str):
    result = bot.handle(query)
    assert result.skill == "notes"
    assert "Notes matching 'milk':" in result.reply
    assert "buy milk" in result.reply


def test_find_notes_txt_stays_with_file_search(bot: Assistant):
    result = bot.handle("find notes.txt")
    assert result.skill == "file_search"
    assert "notes.txt" in result.reply


def test_find_notebook_stays_with_file_search(bot: Assistant):
    result = bot.handle("find notebook")
    assert result.skill == "file_search"
    assert "notebook.md" in result.reply


def test_search_notes_still_routes_to_notes(bot: Assistant):
    result = bot.handle("search notes milk")
    assert result.skill == "notes"
    assert "buy milk" in result.reply


def test_find_report_still_routes_to_file_search(bot: Assistant):
    assert bot.handle("find report.txt").skill == "file_search"


def test_notes_run_does_not_treat_notebook_as_search(context: SkillContext):
    """notes.run must not read 'find notebook' as a search for 'book'."""
    context.storage.add_note("my book list")
    reply = notes.run("find notebook", context)
    assert "Notes matching" not in reply


def test_notes_run_search_prefix_without_term(context: SkillContext):
    reply = notes.run("search notes", context)
    assert reply == "What should I search your notes for? e.g. 'search notes milk'."
