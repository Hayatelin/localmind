"""Reminders skill: add and list reminders (with an optional due time).

Examples that route here::

    remind me to call mom at 5pm
    reminder: submit taxes by friday
    list reminders

A due time is recognised only when the message *ends* with ``at``/``by``/
``on``/``due`` followed by one of these forms: a 12-hour time (``5pm``,
``10:30 am``), a 24-hour ``HH:MM`` time, a ``YYYY-MM-DD`` date, a weekday name
or three-letter abbreviation, or ``today``/``tomorrow``/``tonight``/``noon``/
``midnight``. Anything else (``look at the report``) stays in the reminder text.
The due part is stored as text, exactly as typed.
LocalMind does not schedule OS notifications -- it keeps a durable, local list
you can review any time. This keeps the project dependency-free and offline.
"""

from __future__ import annotations

import re

from . import Skill, SkillContext

# Due-time forms accepted after at/by/on/due. Nothing else counts as a due time.
_DUE_FORMS = (
    r"\d{1,2}(?::\d\d)?\s*(?:am|pm)"  # 12-hour: 5pm, 10:30 am
    r"|(?:[01]\d|2[0-3]):[0-5]\d"  # 24-hour HH:MM: 17:30
    r"|\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD
    r"|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|mon|tue|wed|thu|fri|sat|sun"
    r"|today|tomorrow|tonight|noon|midnight"
)
# Matches a trailing "... at 5pm" / "... by friday" / "... on 2026-11-10" clause.
# Anchored at the end, so with several at/by/on the last one is used.
_DUE_RE = re.compile(rf"\b(?:at|by|on|due)\s+({_DUE_FORMS})\s*$", re.I)


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
