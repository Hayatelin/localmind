"""Notes skill: add, list and search notes stored in local SQLite.

Examples that route here::

    add note buy milk
    note: call the dentist
    list notes
    search notes milk
"""

from __future__ import annotations

import re

from . import Skill, SkillContext


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
    if lowered.startswith(("search note", "find note", "search notes")):
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


SKILL = Skill(
    name="notes",
    keywords=["note", "notes"],
    run=run,
    description="Add, list and search personal notes stored in local SQLite.",
)
