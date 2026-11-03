"""Notes skill: add, list and search notes stored in local SQLite.

Examples that route here::

    add note buy milk
    note: call the dentist
    list notes
    search notes milk
    find notes milk
"""

from __future__ import annotations

import re

from . import Skill, SkillContext

#: "search note(s)" / "find note(s)" as whole words, e.g. not "find notebook".
_SEARCH_PREFIX = re.compile(r"^\s*(?:search|find)\s+notes?(?=\s|$)", re.I)
#: The same prefix followed by a search term. Used for routing, so that
#: "find notes milk" goes to this skill while "find notes.txt" or
#: "find notebook" stays with file_search.
_SEARCH_WITH_TERM = re.compile(r"^\s*(?:search|find)\s+notes?\s+\S", re.I)
#: Extra routing score for a notes search. file_search scores a leading
#: "find" at 1.5, so without this "find notes milk" would go to file_search.
_SEARCH_BONUS = 2.0


def _strip_prefix(query: str) -> str:
    """Remove a leading 'add note'/'note' style prefix and return the body."""
    text = query.strip()
    text = re.sub(r"^\s*(add\s+note|new\s+note|note)\s*[:\-]?\s*", "", text, flags=re.I)
    return text.strip()


def run(query: str, context: SkillContext) -> str:
    """Handle a notes request and return a human-readable reply."""
    store = context.storage
    text = query.strip()
    lowered = text.lower()

    # --- search ---------------------------------------------------------
    if _SEARCH_PREFIX.match(text):
        term = re.sub(r"^\s*(search|find)\s+notes?\s*", "", text, flags=re.I).strip()
        if not term:
            return "What should I search your notes for? e.g. 'search notes milk'."
        rows = store.search_notes(term)
        if not rows:
            return f"No notes match '{term}'."
        lines = [f"Notes matching '{term}':"]
        lines += [f"  [{r['id']}] {r['text']}" for r in rows]
        return "\n".join(lines)

    # --- list -----------------------------------------------------------
    if lowered.startswith(("list note", "show note", "list notes", "show notes")) or lowered in {
        "notes",
    }:
        rows = store.list_notes()
        if not rows:
            return "You have no notes yet. Try 'add note buy milk'."
        lines = ["Your notes:"]
        lines += [f"  [{r['id']}] {r['text']}" for r in rows]
        return "\n".join(lines)

    # --- add (default) --------------------------------------------------
    body = _strip_prefix(text)
    if not body:
        return "What would you like to note? e.g. 'add note buy milk'."
    note_id = store.add_note(body)
    return f"Saved note #{note_id}: {body}"


_KEYWORDS = ["note", "notes"]
_DESCRIPTION = "Add, list and search personal notes stored in local SQLite."
# Plain keyword scorer, reused by ``_score`` below.
_KEYWORD_SKILL = Skill(name="notes", keywords=_KEYWORDS, run=run)


def _score(query: str) -> float:
    """Keyword score, plus a bonus for 'find/search note(s) <term>'."""
    score = _KEYWORD_SKILL.score(query)
    if _SEARCH_WITH_TERM.match(query):
        score += _SEARCH_BONUS
    return score


SKILL = Skill(
    name="notes",
    keywords=_KEYWORDS,
    run=run,
    description=_DESCRIPTION,
    _scorer=_score,
)
