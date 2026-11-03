"""A due time is only taken from a whitelisted form at the end of the message."""

from __future__ import annotations

import pytest

from localmind.skills import SkillContext, reminders
from localmind.skills.reminders import _parse_reminder


@pytest.mark.parametrize(
    "query, body",
    [
        ("remind me to look at the report", "look at the report"),
        ("remind me to sit by the window", "sit by the window"),
        ("remind me to pay on the bill", "pay on the bill"),
        # Due-like text followed by more words is not a due time.
        ("remind me to call at 5pm about taxes", "call at 5pm about taxes"),
    ],
)
def test_ordinary_prepositions_are_not_due_times(query, body):
    assert _parse_reminder(query) == (body, None)


def test_last_at_wins():
    assert _parse_reminder("remind me to meet at the park at 5pm") == (
        "meet at the park",
        "5pm",
    )


@pytest.mark.parametrize(
    "query, body, due",
    [
        # 12-hour clock
        ("remind me to call mom at 5pm", "call mom", "5pm"),
        ("remind me to call mom at 10:30 am", "call mom", "10:30 am"),
        # 24-hour HH:MM
        ("remind me to start the build at 17:30", "start the build", "17:30"),
        # YYYY-MM-DD
        ("remind me to renew passport by 2026-12-01", "renew passport", "2026-12-01"),
        # weekday names and three-letter abbreviations, any case
        ("reminder: submit taxes by friday", "submit taxes", "friday"),
        ("remind me to water plants on Mon", "water plants", "Mon"),
        ("remind me to pay rent due SUNDAY", "pay rent", "SUNDAY"),
        # today / tomorrow / tonight / noon / midnight
        ("remind me to buy bread today", "buy bread today", None),
        ("remind me to buy bread by today", "buy bread", "today"),
        ("remind me to email Bob tomorrow", "email Bob tomorrow", None),
        ("remind me to email Bob by tomorrow", "email Bob", "tomorrow"),
        ("remind me to lock the door at tonight", "lock the door", "tonight"),
        ("remind me to eat lunch at noon", "eat lunch", "noon"),
        ("remind me to back up at midnight", "back up", "midnight"),
    ],
)
def test_whitelisted_due_forms(query, body, due):
    assert _parse_reminder(query) == (body, due)


@pytest.mark.parametrize(
    "query",
    [
        "remind me to meet at 25:00",  # not a valid HH:MM
        "remind me to read at chapter 5",
        "remind me to ship on friday-ish",
        "remind me to read on the train",
    ],
)
def test_non_whitelisted_tail_is_kept_in_body(query):
    body, due = _parse_reminder(query)
    assert due is None
    assert body == query[len("remind me to "):]


def test_run_stores_whole_text_when_no_due(context: SkillContext):
    reply = reminders.run("remind me to look at the report", context)
    assert reply == "Reminder #1 set: look at the report"
    row = context.storage.list_reminders()[0]
    assert row["text"] == "look at the report"
    assert row["due"] is None
