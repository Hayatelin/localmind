"""Tests for skill routing and the LLM fallback path in the Assistant."""

from __future__ import annotations

from localmind.assistant import Assistant
from localmind.config import Config
from localmind.providers import MockProvider
from localmind.storage import Storage


def _assistant(config: Config) -> Assistant:
    return Assistant(
        config=config,
        storage=Storage(config.db_path),
        provider=MockProvider(),
    )


def test_routes_to_notes(config: Config):
    bot = _assistant(config)
    result = bot.handle("add note buy milk")
    assert result.skill == "notes"
    assert "buy milk" in result.reply
    bot.close()


def test_routes_to_reminders(config: Config):
    bot = _assistant(config)
    result = bot.handle("remind me to call mom at 5pm")
    assert result.skill == "reminders"
    bot.close()


def test_routes_to_calc(config: Config):
    bot = _assistant(config)
    result = bot.handle("calc 2 + 2")
    assert result.skill == "calc"
    assert result.reply.endswith("= 4")
    bot.close()


def test_falls_back_to_provider(config: Config):
    bot = _assistant(config)
    result = bot.handle("hello there")
    assert result.skill is None  # no skill matched -> provider answered
    assert isinstance(result.reply, str) and result.reply
    bot.close()


def test_history_is_recorded(config: Config):
    bot = _assistant(config)
    bot.handle("calc 1 + 1")
    history = bot.storage.list_history()
    # One user turn and one assistant turn were stored.
    roles = [h["role"] for h in history]
    assert "user" in roles and "assistant" in roles
    bot.close()


class _RecordingProvider:
    """Provider stub that records exactly what the Assistant passes in."""

    name = "recording"

    def __init__(self):
        self.calls = []

    def generate(self, prompt, history=None):
        self.calls.append((prompt, list(history or [])))
        return "ok"


def test_provider_history_excludes_current_message(config: Config):
    provider = _RecordingProvider()
    bot = Assistant(config=config, storage=Storage(config.db_path), provider=provider)
    bot.handle("calc 1 + 1")          # skill turn, stored in history
    bot.handle("tell me a joke")      # no skill -> provider fallback
    prompt, history = provider.calls[-1]
    assert prompt == "tell me a joke"
    # Only earlier turns: the current message is sent once, as ``prompt``.
    assert history == [
        {"role": "user", "content": "calc 1 + 1"},
        {"role": "assistant", "content": "1 + 1 = 2"},
    ]
    bot.close()
