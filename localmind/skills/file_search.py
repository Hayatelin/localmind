"""File search skill: find files by name or text content in a local directory.

The directory scanned is taken from configuration (``file_search_dir`` /
``LOCALMIND_FILE_SEARCH_DIR``) and defaults to the user's home directory. Nothing
leaves the machine; this is a plain local filesystem walk.

Examples that route here::

    find report.pdf
    search files invoice
    grep budget       (searches file contents for 'budget')
"""

from __future__ import annotations

import re
from pathlib import Path

from . import Skill, SkillContext

# File extensions we are willing to scan the *contents* of (text-like only).
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv", ".log",
    ".html", ".css", ".js", ".ini", ".cfg", ".toml", ".rst",
}

_MAX_RESULTS = 20
_MAX_FILES_SCANNED = 5000  # safety bound so huge trees stay responsive
_MAX_BYTES_PER_FILE = 1_000_000  # skip reading very large files for content


def _extract_term(query: str):
    """Return (term, content_mode) parsed from the user's query."""
    text = query.strip()
    content_mode = False
    if re.match(r"^\s*grep\b", text, flags=re.I):
        content_mode = True
    term = re.sub(
        r"^\s*(search\s+files?|find\s+files?|find|search|locate|grep)\s*[:\-]?\s*",
        "",
        text,
        flags=re.I,
    ).strip()
    # An explicit "in files"/"content" hint also enables content search.
    if re.search(r"\b(in\s+files?|content|contents|inside)\b", term, flags=re.I):
        content_mode = True
        term = re.sub(r"\b(in\s+files?|content|contents|inside)\b", "", term, flags=re.I).strip()
    return term, content_mode


def _search_filenames(root: Path, term: str):
    """Yield paths whose filename contains ``term`` (case-insensitive)."""
    low = term.lower()
    scanned = 0
    for path in root.rglob("*"):
        scanned += 1
        if scanned > _MAX_FILES_SCANNED:
            break
        if path.is_file() and low in path.name.lower():
            yield path


def _search_contents(root: Path, term: str):
    """Yield (path, line) for text files whose contents contain ``term``."""
    low = term.lower()
    scanned = 0
    for path in root.rglob("*"):
        scanned += 1
        if scanned > _MAX_FILES_SCANNED:
            break
        if not path.is_file() or path.suffix.lower() not in _TEXT_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > _MAX_BYTES_PER_FILE:
                continue
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    if low in line.lower():
                        yield path, line.strip()
                        break
        except (OSError, UnicodeDecodeError):
            continue


def run(query: str, context: SkillContext) -> str:
    """Handle a file-search request and return a human-readable reply."""
    root = Path(context.config.file_search_dir).expanduser()
    term, content_mode = _extract_term(query)

    if not term:
        return "What should I search for? e.g. 'find report.pdf' or 'grep budget'."
    if not root.is_dir():
        return f"Configured search directory does not exist: {root}"

    results = []
    if content_mode:
        for path, line in _search_contents(root, term):
            results.append(f"  {path}  ->  {line[:80]}")
            if len(results) >= _MAX_RESULTS:
                break
        header = f"Files containing '{term}' under {root}:"
    else:
        for path in _search_filenames(root, term):
            results.append(f"  {path}")
            if len(results) >= _MAX_RESULTS:
                break
        header = f"Files named like '{term}' under {root}:"

    if not results:
        return f"No matches for '{term}' under {root}."
    return "\n".join([header, *results])


SKILL = Skill(
    name="file_search",
    keywords=["find", "search files", "locate", "grep", "file"],
    run=run,
    description="Search a configured local directory by filename or text content.",
)
