"""A leading minus sign belongs to the expression, not to the 'calc' prefix."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from localmind.skills import SkillContext, calc

# Repo root, so the child interpreter can import localmind without a pip
# install (CI runs ``pytest`` straight from the checkout).
_REPO_ROOT = str(Path(__file__).resolve().parents[1])


@pytest.mark.parametrize(
    "query, expected",
    [
        ("calc -7 + 2", "-7 + 2 = -5"),
        ("calc -1.5*2", "-1.5*2 = -3"),
        ("calc: 2+3", "2+3 = 5"),
        ("what is -3 * -3", "-3 * -3 = 9"),
        ("calc 2-3", "2-3 = -1"),  # regression: already correct before
        ("calc - 2+3", "- 2+3 = 1"),
    ],
)
def test_leading_minus_is_kept(query: str, expected: str, context: SkillContext):
    assert calc.run(query, context) == expected


def test_leading_minus_via_cli(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALMIND_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LOCALMIND_FILE_SEARCH_DIR", str(tmp_path / "files"))
    monkeypatch.delenv("LOCALMIND_DB", raising=False)
    monkeypatch.delenv("LOCALMIND_CONFIG", raising=False)
    existing = os.environ.get("PYTHONPATH")
    monkeypatch.setenv(
        "PYTHONPATH", _REPO_ROOT + (os.pathsep + existing if existing else "")
    )
    proc = subprocess.run(
        [sys.executable, "-m", "localmind", "--once", "calc -7 + 2"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "[calc] -7 + 2 = -5"
