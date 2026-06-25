"""The Assistant: routes user input to a skill or falls back to a provider.

Routing strategy
----------------
1. Every loaded skill is asked to ``score`` the input.
2. The highest-scoring skill above a small threshold handles it.
3. If no skill matches, the configured provider (offline mock by default)
   answers.

Every turn is persisted to the SQLite ``history`` table so LocalMind has a
durable, local memory of the conversation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import Config
from .providers import Provider, build_provider
from .skills import Skill, SkillContext, load_skills
from .storage import Storage


@dataclass
class RouteResult:
    """The outcome of routing a single user message."""

    reply: str
    skill: Optional[str]  # name of the skill used, or None if the LLM answered


class Assistant:
    """High-level orchestrator tying together skills, storage and a provider."""

    #: A skill must score at least this high to win routing.
    MATCH_THRESHOLD = 1.0

    def __init__(
        self,
        config: Optional[Config] = None,
        storage: Optional[Storage] = None,
        provider: Optional[Provider] = None,
        skills: Optional[List[Skill]] = None,
    ):
        self.config = config or Config()
        self.storage = storage or Storage(self.config.db_path)
        self.provider = provider or build_provider(self.config)
        self.skills = skills if skills is not None else load_skills()
        self._context = SkillContext(storage=self.storage, config=self.config)

    # -- routing -----------------------------------------------------------
    def best_skill(self, query: str) -> Optional[Skill]:
        """Return the highest-scoring skill above the threshold, or None."""
        best: Optional[Skill] = None
        best_score = self.MATCH_THRESHOLD - 0.0001
        for skill in self.skills:
            score = skill.score(query)
            if score > best_score:
                best, best_score = skill, score
        return best

    def handle(self, query: str, record_history: bool = True) -> RouteResult:
        """Route ``query`` and return the reply plus which skill (if any) ran."""
        query = query.strip()
        if record_history:
            self.storage.add_history("user", query)

        skill = self.best_skill(query)
        if skill is not None:
            reply = skill.run(query, self._context)
            used = skill.name
        else:
            history = self._recent_provider_history()
            reply = self.provider.generate(query, history=history)
            used = None

        if record_history:
            self.storage.add_history("assistant", reply, skill=used)
        return RouteResult(reply=reply, skill=used)

    def _recent_provider_history(self, limit: int = 10) -> List[dict]:
        """Build a short OpenAI-style message list from stored history."""
        rows = self.storage.list_history(limit=limit)
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self.storage.close()
