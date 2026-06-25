"""Tests for each built-in skill's core behaviour."""

from __future__ import annotations

from pathlib import Path

from localmind.skills import SkillContext
from localmind.skills import calc, file_search, notes, reminders


def test_notes_add_and_list(context: SkillContext):
    reply = notes.run("add note buy milk", context)
    assert "buy milk" in reply
    listed = notes.run("list notes", context)
    assert "buy milk" in listed


def test_notes_search(context: SkillContext):
    notes.run("add note buy milk", context)
    notes.run("add note call dentist", context)
    reply = notes.run("search notes milk", context)
    assert "milk" in reply
    assert "dentist" not in reply


def test_reminders_add_and_list(context: SkillContext):
    reply = reminders.run("remind me to call mom at 5pm", context)
    assert "call mom" in reply
    assert "5pm" in reply
    listed = reminders.run("list reminders", context)
    assert "call mom" in listed
    assert "5pm" in listed


def test_calc_basic(context: SkillContext):
    assert calc.run("calc 2 + 2 * 3", context) == "2 + 2 * 3 = 8"
    assert calc.run("what is 12 / 4", context) == "12 / 4 = 3"


def test_calc_is_safe(context: SkillContext):
    # Names / attribute access must be rejected, never executed.
    reply = calc.run("calc __import__('os').system('echo hi')", context)
    assert "safe arithmetic" in reply.lower() or "could not" in reply.lower()


def test_calc_functions(context: SkillContext):
    assert calc.run("calc sqrt(16)", context) == "sqrt(16) = 4"
    assert calc.run("calc max(3, 7, 2)", context) == "max(3, 7, 2) = 7"


def test_file_search_by_name(context: SkillContext, tmp_path: Path):
    (tmp_path / "report.txt").write_text("hello world", encoding="utf-8")
    (tmp_path / "other.txt").write_text("nothing", encoding="utf-8")
    reply = file_search.run("find report", context)
    assert "report.txt" in reply
    assert "other.txt" not in reply


def test_file_search_by_content(context: SkillContext, tmp_path: Path):
    (tmp_path / "doc.txt").write_text("the budget is large", encoding="utf-8")
    reply = file_search.run("grep budget", context)
    assert "doc.txt" in reply
    assert "budget" in reply
