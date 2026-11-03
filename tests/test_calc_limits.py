"""Calculator size limits: huge powers and float overflow return a message.

Hang protection uses ``subprocess.run(..., timeout=...)``: a runaway big-integer
power runs inside C code and cannot be interrupted by signals or threads.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from localmind.skills import SkillContext, calc

# Repo root, so child interpreters can import localmind even when it is not
# pip-installed (CI runs ``pytest`` straight from the checkout).
_REPO_ROOT = str(Path(__file__).resolve().parents[1])


def _isolate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALMIND_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LOCALMIND_FILE_SEARCH_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("LOCALMIND_DB", str(tmp_path / "lm.db"))
    existing = os.environ.get("PYTHONPATH")
    monkeypatch.setenv(
        "PYTHONPATH", _REPO_ROOT + (os.pathsep + existing if existing else "")
    )


# Times calc.run inside a fresh interpreter and prints "<seconds>\n<reply>".
_TIMED_RUN = """
import sys, time
from localmind.skills import calc
start = time.perf_counter()
reply = calc.run(sys.argv[1], None)
print(time.perf_counter() - start)
print(reply)
"""


def _timed_calc(query: str, tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    proc = subprocess.run(
        [sys.executable, "-c", _TIMED_RUN, query],
        capture_output=True,
        text=True,
        timeout=5,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    elapsed, reply = proc.stdout.split("\n", 1)
    return float(elapsed), reply.strip()


@pytest.mark.parametrize("query", ["calc 9 ** 9 ** 9", "calc 2 ** 100000000"])
def test_huge_power_returns_error_quickly(query, tmp_path, monkeypatch):
    elapsed, reply = _timed_calc(query, tmp_path, monkeypatch)
    assert elapsed < 1.0
    assert "too large" in reply


def test_huge_power_via_cli_does_not_hang(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    proc = subprocess.run(
        [sys.executable, "-m", "localmind", "--once", "calc 9 ** 9 ** 9"],
        capture_output=True,
        text=True,
        timeout=5,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("[calc] ")
    assert "too large" in proc.stdout


def test_float_overflow_returns_message(context: SkillContext):
    reply = calc.run("calc 10.0 ** 400", context)
    assert reply == "Could not evaluate '10.0 ** 400': the result is too large."


def test_repeated_multiplication_is_capped(context: SkillContext):
    big = " * ".join(["(10 ** 1000)"] * 5)
    reply = calc.run(f"calc {big}", context)
    assert "too large" in reply


@pytest.mark.parametrize(
    "query, expected",
    [
        ("calc 2 ** 10", "2 ** 10 = 1024"),
        ("calc (3 + 4) * 5", "(3 + 4) * 5 = 35"),
        ("calc 1.5 * 2.5", "1.5 * 2.5 = 3.75"),
        ("calc 2 + -7", "2 + -7 = -5"),
        ("calc (-1.5) * 2", "(-1.5) * 2 = -3"),
        ("calc (-2) ** 3", "(-2) ** 3 = -8"),
        ("calc 2 ** -2", "2 ** -2 = 0.25"),
        ("calc 1 ** 1000000000", "1 ** 1000000000 = 1"),
        ("calc 2 ** 1000 // 2 ** 999", "2 ** 1000 // 2 ** 999 = 2"),
    ],
)
def test_ordinary_arithmetic_unchanged(query, expected, context: SkillContext):
    assert calc.run(query, context) == expected
