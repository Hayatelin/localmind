"""Configuration loading for LocalMind.

LocalMind is configured through a small set of values that control which
language-model provider is used and where local data lives. Configuration is
resolved with the following precedence (highest first):

1. Environment variables (prefixed ``LOCALMIND_``).
2. A YAML config file (``localmind.yaml`` in the user config dir, or a path
   given by ``LOCALMIND_CONFIG``).
3. Built-in defaults.

Crucially, the default provider is ``"mock"`` -- a fully offline, rule-based
provider -- so nothing ever leaves the machine unless the user explicitly opts
in to a local OpenAI-compatible endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# User data / config directories
# ---------------------------------------------------------------------------
def user_data_dir() -> Path:
    """Return the per-user directory where LocalMind stores its database.

    Honours ``LOCALMIND_HOME`` if set (handy for tests and demos), otherwise
    picks a sensible OS-appropriate location. The directory is created if it
    does not already exist.
    """
    override = os.environ.get("LOCALMIND_HOME")
    if override:
        base = Path(override)
    elif os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home())) / "LocalMind"
    else:  # macOS / Linux
        base = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        ) / "localmind"
    base.mkdir(parents=True, exist_ok=True)
    return base


def default_config_path() -> Path:
    """Path to the YAML config file used when ``LOCALMIND_CONFIG`` is unset."""
    return user_data_dir() / "localmind.yaml"


@dataclass
class Config:
    """Resolved LocalMind configuration.

    Attributes
    ----------
    provider:
        Which LLM provider to use as the fallback when no skill matches.
        One of ``"mock"`` (offline, default) or ``"local"`` (OpenAI-compatible
        endpoint such as Ollama or LM Studio).
    local_endpoint:
        Base URL of the local OpenAI-compatible server, e.g.
        ``http://localhost:11434/v1`` (Ollama) or ``http://localhost:1234/v1``
        (LM Studio). Only used when ``provider == "local"``.
    local_model:
        Model name to request from the local endpoint.
    db_path:
        Absolute path to the SQLite database file.
    file_search_dir:
        Directory the ``file_search`` skill scans. Defaults to the user's home.
    config_path:
        Where this config was loaded from (informational, for ``localmind config``).
    """

    provider: str = "mock"
    local_endpoint: str = "http://localhost:11434/v1"
    local_model: str = "llama3"
    db_path: str = ""
    file_search_dir: str = ""
    config_path: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        """Return a plain dict (used by the ``config`` sub-command)."""
        return asdict(self)


def _read_yaml(path: Path) -> Dict[str, Any]:
    """Read a YAML file into a dict, tolerating a missing file."""
    if not path.exists():
        return {}
    import yaml  # PyYAML is a declared dependency

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping")
    return data


def load_config(config_path: Optional[str] = None) -> Config:
    """Build a :class:`Config` from defaults, a YAML file and the environment.

    Parameters
    ----------
    config_path:
        Optional explicit path to a YAML config file. If omitted, the path is
        taken from ``LOCALMIND_CONFIG`` and then from :func:`default_config_path`.
    """
    path = Path(
        config_path
        or os.environ.get("LOCALMIND_CONFIG")
        or default_config_path()
    )
    file_values = _read_yaml(path)

    data_dir = user_data_dir()
    cfg = Config(
        provider=str(file_values.get("provider", "mock")),
        local_endpoint=str(
            file_values.get("local_endpoint", "http://localhost:11434/v1")
        ),
        local_model=str(file_values.get("local_model", "llama3")),
        db_path=str(file_values.get("db_path", data_dir / "localmind.db")),
        file_search_dir=str(file_values.get("file_search_dir", Path.home())),
        config_path=str(path),
        extra={
            k: v
            for k, v in file_values.items()
            if k
            not in {
                "provider",
                "local_endpoint",
                "local_model",
                "db_path",
                "file_search_dir",
            }
        },
    )

    # Environment overrides (highest precedence).
    cfg.provider = os.environ.get("LOCALMIND_PROVIDER", cfg.provider)
    cfg.local_endpoint = os.environ.get("LOCALMIND_LOCAL_ENDPOINT", cfg.local_endpoint)
    cfg.local_model = os.environ.get("LOCALMIND_LOCAL_MODEL", cfg.local_model)
    cfg.db_path = os.environ.get("LOCALMIND_DB", cfg.db_path)
    cfg.file_search_dir = os.environ.get(
        "LOCALMIND_FILE_SEARCH_DIR", cfg.file_search_dir
    )
    return cfg
