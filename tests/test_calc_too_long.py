"""Very long or deeply nested expressions return a message, not RecursionError."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from localmind.assistant import Assistant
from localmind.config import Config
from localmind.providers import MockProvider
from localmind.skills import calc
from localmind.storage import Storage

_TOO_LONG = "That expression is too long to calculate"


@pytest.mark.parametrize("terms", [1200, 5000])
def test_long_sum_returns_message(terms: int):
    reply = calc.run("calc " + " + ".join(["1"] * terms), None)
    assert reply.startswith(_TOO_LONG), reply


@pytest.mark.parametrize(
    "expression",
    [
        "-" * 3000 + "1",  # RecursionError while evaluating
        "-" * 6000 + "1",  # parser stack overflow (MemoryError)
        "+-" * 2988 + "1",  # parser stack overflow (MemoryError)
        "**".join(["1"] * 2989),  # parser stack overflow (MemoryError)
    ],
    ids=["minus-3000", "minus-6000", "plus-minus-2988", "pow-chain-2989"],
)
def test_deep_expressions_return_message(expression: str):
    assert len(expression) <= calc._MAX_EXPRESSION_CHARS
    reply = calc.run("calc " + expression, None)
    assert reply.startswith(_TOO_LONG), reply


def test_over_length_limit_is_rejected_before_parsing(monkeypatch):
    # 300,000 terms crashes ast.parse on Python 3.9, so it must never reach it.
    class _NoParseAst:
        """calc's view of ``ast`` with ``parse`` disabled (other names pass through)."""

        def __getattr__(self, name):
            if name == "parse":
                raise AssertionError("ast.parse must not be called")
            return getattr(ast, name)

    # Patch only calc's reference, not the global ast module pytest also uses.
    monkeypatch.setattr(calc, "ast", _NoParseAst())
    reply = calc.run("calc " + "+".join(["1"] * 300_000), None)
    assert reply.startswith(_TOO_LONG), reply
    assert str(calc._MAX_EXPRESSION_CHARS) in reply


def test_expression_at_length_limit_still_parses():
    # A float literal exactly at the limit: long, but not deep.
    expression = "0." + "0" * (calc._MAX_EXPRESSION_CHARS - 3) + "1"
    assert len(expression) == calc._MAX_EXPRESSION_CHARS
    reply = calc.run("calc " + expression, None)
    assert reply.endswith(" = 0"), reply[-40:]


def test_one_over_length_limit_is_rejected():
    expression = "0." + "0" * (calc._MAX_EXPRESSION_CHARS - 2) + "1"
    reply = calc.run("calc " + expression, None)
    assert reply.startswith(_TOO_LONG), reply[:80]


def test_safe_eval_raises_value_error_subclass():
    with pytest.raises(ValueError) as info:
        calc.safe_eval(" + ".join(["1"] * 1200))
    assert not isinstance(info.value, RecursionError)
    assert type(info.value).__name__ == "_TooLong"


def test_moderate_sum_still_computes():
    assert calc.run("calc " + " + ".join(["1"] * 300), None).endswith("= 300")


def test_short_expressions_unchanged():
    assert calc.run("calc 2 + 2 * 3", None) == "2 + 2 * 3 = 8"
    assert calc.run("calc -7 + 2", None) == "-7 + 2 = -5"


def test_long_sum_through_assistant(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALMIND_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LOCALMIND_FILE_SEARCH_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("LOCALMIND_DB", str(tmp_path / "lm.db"))
    monkeypatch.delenv("LOCALMIND_SKILLS_DIR", raising=False)
    (tmp_path / "files").mkdir()
    config = Config(
        provider="mock",
        db_path=str(tmp_path / "lm.db"),
        file_search_dir=str(tmp_path / "files"),
    )
    bot = Assistant(config=config, storage=Storage(config.db_path), provider=MockProvider())
    try:
        result = bot.handle("calc " + " + ".join(["1"] * 1200))
        assert result.skill == "calc"
        assert result.reply.startswith(_TOO_LONG), result.reply
    finally:
        bot.close()
