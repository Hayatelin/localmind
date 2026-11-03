"""Tests that pin down behaviour documented in README.md.

Covers the custom-skill example (a module in ``LOCALMIND_SKILLS_DIR``) and the
config precedence (environment > YAML file > defaults).
"""

from __future__ import annotations

from pathlib import Path

from localmind.assistant import Assistant
from localmind.config import load_config
from localmind.skills import load_skills
from localmind.storage import Storage

WEATHER_SKILL = '''
from localmind.skills import Skill, SkillContext

def run(query: str, context: SkillContext) -> str:
    return "It's always sunny inside your own machine."

SKILL = Skill(
    name="weather",
    keywords=["weather", "forecast"],
    run=run,
    description="A toy weather skill.",
)
'''

README_YAML = """\
provider: mock
local_endpoint: http://localhost:11434/v1
local_model: llama3
file_search_dir: /home/you/Documents
"""

ENV_VARS = (
    "LOCALMIND_CONFIG",
    "LOCALMIND_HOME",
    "LOCALMIND_PROVIDER",
    "LOCALMIND_LOCAL_ENDPOINT",
    "LOCALMIND_LOCAL_MODEL",
    "LOCALMIND_DB",
    "LOCALMIND_FILE_SEARCH_DIR",
    "LOCALMIND_SKILLS_DIR",
)


def _clear_env(monkeypatch, home: Path) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LOCALMIND_HOME", str(home))


def test_custom_skill_from_skills_dir_loads_and_routes(tmp_path, monkeypatch):
    _clear_env(monkeypatch, tmp_path / "home")
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "weather.py").write_text(WEATHER_SKILL, encoding="utf-8")
    monkeypatch.setenv("LOCALMIND_SKILLS_DIR", str(skills_dir))

    names = [s.name for s in load_skills()]
    assert "weather" in names
    assert names[-1] == "weather"  # external skills load after built-ins

    storage = Storage(str(tmp_path / "lm.db"))
    try:
        result = Assistant(storage=storage).handle("weather")
    finally:
        storage.close()
    assert result.skill == "weather"
    assert result.reply == "It's always sunny inside your own machine."


def test_yaml_config_values_are_read(tmp_path, monkeypatch):
    _clear_env(monkeypatch, tmp_path / "home")
    cfg_file = tmp_path / "localmind.yaml"
    cfg_file.write_text(README_YAML, encoding="utf-8")
    monkeypatch.setenv("LOCALMIND_CONFIG", str(cfg_file))

    cfg = load_config()
    assert cfg.config_path == str(cfg_file)
    assert cfg.provider == "mock"
    assert cfg.local_endpoint == "http://localhost:11434/v1"
    assert cfg.local_model == "llama3"
    assert cfg.file_search_dir == "/home/you/Documents"
    assert cfg.db_path == str(tmp_path / "home" / "localmind.db")


def test_environment_overrides_yaml(tmp_path, monkeypatch):
    _clear_env(monkeypatch, tmp_path / "home")
    cfg_file = tmp_path / "localmind.yaml"
    cfg_file.write_text(README_YAML, encoding="utf-8")
    monkeypatch.setenv("LOCALMIND_CONFIG", str(cfg_file))
    monkeypatch.setenv("LOCALMIND_LOCAL_ENDPOINT", "http://localhost:1234/v1")
    monkeypatch.setenv("LOCALMIND_LOCAL_MODEL", "other-model")
    monkeypatch.setenv("LOCALMIND_DB", str(tmp_path / "custom.db"))
    monkeypatch.setenv("LOCALMIND_FILE_SEARCH_DIR", str(tmp_path))

    cfg = load_config()
    assert cfg.local_endpoint == "http://localhost:1234/v1"
    assert cfg.local_model == "other-model"
    assert cfg.db_path == str(tmp_path / "custom.db")
    assert cfg.file_search_dir == str(tmp_path)


def test_defaults_without_config_file(tmp_path, monkeypatch):
    home = tmp_path / "home"
    _clear_env(monkeypatch, home)

    cfg = load_config()
    assert cfg.config_path == str(home / "localmind.yaml")
    assert cfg.provider == "mock"
    assert cfg.local_endpoint == "http://localhost:11434/v1"
    assert cfg.db_path == str(home / "localmind.db")
