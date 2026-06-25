"""Skill plugin system for LocalMind.

A *skill* is a drop-in Python module placed in this package. Each skill module
exposes a module-level ``SKILL`` object (an instance of :class:`Skill`, or any
object with the same attributes) describing:

* ``name``     -- a short identifier, e.g. ``"notes"``.
* ``keywords`` -- trigger words/intents used for routing.
* ``run(query, context)`` -- the handler. It receives the raw user ``query`` and
  a :class:`SkillContext` (giving access to storage and config) and returns a
  string reply.

Skills are discovered automatically: any importable module in this package that
defines ``SKILL`` is loaded. To add your own skill, drop a new ``.py`` file here
(or in an external folder pointed to by ``LOCALMIND_SKILLS_DIR``) -- no core
code needs to change.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import pkgutil
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from ..config import Config
from ..storage import Storage


@dataclass
class SkillContext:
    """Everything a skill handler might need, bundled in one object."""

    storage: Storage
    config: Config


@dataclass
class Skill:
    """Metadata + handler for a single skill.

    ``score`` may be overridden by a skill to provide smarter matching; the
    default implementation counts keyword hits, giving a small bonus when a
    keyword appears at the start of the query (a strong intent signal).
    """

    name: str
    keywords: List[str]
    run: Callable[[str, SkillContext], str]
    description: str = ""
    _scorer: Optional[Callable[[str], float]] = field(default=None, repr=False)

    def score(self, query: str) -> float:
        """Return how strongly this skill matches ``query`` (0 = no match)."""
        if self._scorer is not None:
            return self._scorer(query)
        text = query.lower().strip()
        total = 0.0
        for kw in self.keywords:
            kw = kw.lower()
            # Word-boundary match so "calc" does not match "calcium".
            if re.search(rf"\b{re.escape(kw)}\b", text):
                total += 1.0
                if text.startswith(kw):
                    total += 0.5  # leading keyword = stronger intent
        return total


def _load_module_skill(module) -> Optional[Skill]:
    """Extract a ``SKILL`` object from a module, if present and valid."""
    skill = getattr(module, "SKILL", None)
    if skill is None:
        return None
    # Accept either a real Skill or any duck-typed equivalent.
    if not all(hasattr(skill, attr) for attr in ("name", "keywords", "run")):
        return None
    return skill


def load_skills(extra_dir: Optional[str] = None) -> List[Skill]:
    """Discover and return all available skills.

    Parameters
    ----------
    extra_dir:
        Optional path to a directory of additional skill modules. If omitted,
        ``LOCALMIND_SKILLS_DIR`` is consulted. This lets users keep custom
        skills outside the installed package.
    """
    skills: List[Skill] = []

    # 1. Built-in skills shipped inside this package.
    package_path = Path(__file__).parent
    for mod_info in pkgutil.iter_modules([str(package_path)]):
        if mod_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{mod_info.name}")
        skill = _load_module_skill(module)
        if skill is not None:
            skills.append(skill)

    # 2. External, user-provided skills.
    extra = extra_dir or os.environ.get("LOCALMIND_SKILLS_DIR")
    if extra:
        ext_path = Path(extra)
        if ext_path.is_dir():
            for py_file in sorted(ext_path.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                spec = importlib.util.spec_from_file_location(
                    f"localmind_ext_{py_file.stem}", py_file
                )
                if spec and spec.loader:  # pragma: no branch
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)  # type: ignore[union-attr]
                    skill = _load_module_skill(module)
                    if skill is not None:
                        skills.append(skill)

    return skills


__all__ = ["Skill", "SkillContext", "load_skills"]
