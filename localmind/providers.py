"""Language-model providers for LocalMind's fallback path.

A *provider* is only consulted when no skill claims the user's input. LocalMind
ships with two providers:

* :class:`MockProvider` -- a deterministic, rule-based "LLM" that needs no
  network and no API key. This is the default, which is what lets the whole
  project run fully offline out of the box.
* :class:`LocalEndpointProvider` -- talks to a local OpenAI-compatible server
  such as Ollama (``http://localhost:11434/v1``) or LM Studio
  (``http://localhost:1234/v1``). ``requests`` is imported lazily so it is only
  needed if the user actually opts in to this provider.

No provider in this module ever contacts a cloud service. The local endpoint is
the user's own machine.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Protocol

from .config import Config


class Provider(Protocol):
    """Structural type all providers satisfy."""

    name: str

    def generate(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Return a reply for ``prompt`` given optional prior chat ``history``."""
        ...


class MockProvider:
    """Offline, rule-based provider.

    It recognises a few conversational patterns (greetings, identity, help,
    simple "what is" questions) and otherwise echoes a friendly, honest message
    explaining that it is the offline provider. The goal is not to be smart but
    to make LocalMind fully usable with zero setup.
    """

    name = "mock"

    #: Ordered (regex, response) rules. First match wins.
    _RULES = [
        (
            r"\b(hi|hello|hey|yo|hiya)\b",
            "Hello! I'm LocalMind running fully offline. Ask me to take a note, "
            "set a reminder, do some math, or search your files.",
        ),
        (
            r"\b(who are you|what are you|your name)\b",
            "I'm LocalMind, a privacy-first local assistant. I run on your "
            "machine and never send your data to the cloud.",
        ),
        (
            r"\b(help|what can you do|commands)\b",
            "I can route to skills: notes, reminders, file search and a "
            "calculator. Try 'add note buy milk', 'remind me to call mom', "
            "'calc 2+2' or 'find report.pdf'.",
        ),
        (
            r"\b(thanks|thank you|thx)\b",
            "You're welcome!",
        ),
        (
            r"\b(bye|goodbye|exit|quit)\b",
            "Goodbye! Your data stays right here on this machine.",
        ),
    ]

    def generate(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        text = prompt.strip().lower()
        for pattern, response in self._RULES:
            if re.search(pattern, text):
                return response
        # Lightweight "what is X" handler so simple questions get a useful reply.
        match = re.match(r"(?:what is|define)\s+(.+)", text)
        if match:
            topic = match.group(1).strip(" ?.")
            return (
                f"I'm the offline mock provider, so I don't have a knowledge base "
                f"to explain '{topic}'. Point LocalMind at a local model "
                f"(Ollama / LM Studio) for richer answers -- see the README."
            )
        return (
            "I'm the offline mock provider and didn't match a skill for that. "
            "Configure a local model (provider: local) for free-form answers, "
            "or try a skill like 'add note ...', 'remind me ...', or 'calc ...'."
        )


class LocalEndpointProvider:
    """Provider backed by a local OpenAI-compatible chat-completions endpoint.

    Works with Ollama, LM Studio and similar servers. The HTTP call uses
    ``requests``, imported lazily inside :meth:`generate` so the dependency is
    only required when this provider is actually used.
    """

    name = "local"

    def __init__(self, endpoint: str, model: str, timeout: float = 60.0):
        # Normalise so we always end up with ".../v1/chat/completions".
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        import requests  # lazy import: only needed for the local provider

        messages: List[Dict[str, str]] = list(history or [])
        messages.append({"role": "user", "content": prompt})

        url = f"{self.endpoint}/chat/completions"
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            return (
                f"[local provider error] Could not reach {url}: {exc}. "
                "Is your local model server (Ollama / LM Studio) running? "
                "LocalMind still works offline with provider: mock."
            )


def build_provider(config: Config) -> Provider:
    """Instantiate the provider named in ``config`` (defaults to mock)."""
    if config.provider == "local":
        return LocalEndpointProvider(config.local_endpoint, config.local_model)
    # Any unknown value falls back to the safe, offline mock provider.
    return MockProvider()
