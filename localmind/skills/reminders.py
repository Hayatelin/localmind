"""Reminders skill: add and list reminders (with an optional due time).

Examples that route here::

    remind me to call mom at 5pm
    reminder: submit taxes by friday
    list reminders

Due times are stored as free-form text (whatever follows ``at``/``by``/``on``).
LocalMind does not schedule OS notifications -- it keeps a durable, local list
you can review any time. This keeps the project dependency-free and offline.
"""

from __future__ import annotations

import re

from . import Skill, SkillContext

# Matches a trailing "... at 5pm" / "... by friday" / "... on monday" clause.
_DUE_RE = re.compile(r"\b(?:at|by|on|due)\s+(.+)$", re.I)


def _parse_reminder(text: str):
    """Split a reminder request into (body, due) where due may be None."""
    body = text.strip()
    # Remove a leading 'remind me to' / 'reminder' style prefix.
    body = re.sub(
        r"^\s*(add\s+reminder|new\s+reminder|reminder|remind\s+me\s+to|remind\s+me|remind)\s*[:\-]?\s*",
        "",
        body,
        flags=re.I,
    ).strip()

    due = None
    match = _DUE_RE.search(body)
    if match:
        due = match.group(1).strip()
        body = body[: match.start()].strip()
    return body, due


def run(query: str, context: SkillContext) -> str:
    """Handle a reminder request and return a human-readable reply."""
    store = context.storage
    text = query.strip()
    lowered = text.lower()

    # --- list -----------------------------------------------------------
    if lowered.startswith(("list reminder", "show reminder", "list reminders")) or lowered in {
        "reminders",
    }:
        rows = store.list_reminders()
        if not rows:
            return "You have no reminders. Try 'remind me to call mom at 5pm'."
        lines = ["Your reminders:"]
        for r in rows:
            due = f" (due: {r['due']})" if r["due"] else ""
            lines.append(f"  [{r['id']}] {r['text']}{due}")
        return "\n".join(lines)

    # --- add (default) --------------------------------------------------
    body, due = _parse_reminder(text)
    if not body:
        return "What should I remind you about? e.g. 'remind me to call mom at 5pm'."
    reminder_id = store.add_reminder(body, due)
    due_part = f" (due: {due})" if due else ""
    return f"Reminder #{reminder_id} set: {body}{due_part}"


SKILL = Skill(
    name="reminders",
    keywords=["remind", "reminder", "reminders"],
    run=run,
    description="Add and list reminders with an optional due time, in local SQLite.",
)
