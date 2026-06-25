"""Command-line interface for LocalMind.

Provides:

* an interactive REPL (``python -m localmind`` with no args),
* single-shot mode (``--once "add note buy milk"``),
* ``skills``  -- list loaded skills,
* ``config``  -- show the config path and resolved values.

Argument parsing uses the standard-library :mod:`argparse`.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .assistant import Assistant
from .config import load_config


def _build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with sub-commands."""
    parser = argparse.ArgumentParser(
        prog="localmind",
        description="LocalMind: a privacy-first, local AI assistant gateway. "
        "All data stays on your machine.",
    )
    parser.add_argument(
        "--version", action="version", version=f"LocalMind {__version__}"
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to a YAML config file (defaults to the user config dir).",
    )
    parser.add_argument(
        "--once",
        metavar="TEXT",
        help="Run a single message, print the reply and exit (non-interactive).",
    )

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("skills", help="List loaded skills and their trigger keywords.")
    sub.add_parser("config", help="Show the config file path and resolved values.")
    sub.add_parser("chat", help="Start the interactive chat REPL (the default).")
    return parser


def _cmd_skills(assistant: Assistant) -> int:
    """Print the loaded skills."""
    if not assistant.skills:
        print("No skills loaded.")
        return 0
    print("Loaded skills:")
    for skill in assistant.skills:
        kws = ", ".join(skill.keywords)
        print(f"  - {skill.name}: {skill.description}")
        print(f"      keywords: {kws}")
    return 0


def _cmd_config(assistant: Assistant) -> int:
    """Print the resolved configuration."""
    cfg = assistant.config
    print(f"Config file : {cfg.config_path}")
    print(f"Provider    : {cfg.provider}")
    print(f"Local endpoint: {cfg.local_endpoint}")
    print(f"Local model : {cfg.local_model}")
    print(f"Database    : {cfg.db_path}")
    print(f"File search dir: {cfg.file_search_dir}")
    if cfg.extra:
        print(f"Extra       : {cfg.extra}")
    return 0


def _run_once(assistant: Assistant, text: str) -> int:
    """Handle a single message and print the reply."""
    result = assistant.handle(text)
    tag = f"[{result.skill}] " if result.skill else ""
    print(f"{tag}{result.reply}")
    return 0


def _repl(assistant: Assistant) -> int:
    """Run the interactive chat loop until the user exits."""
    print(
        f"LocalMind {__version__} -- offline, private assistant. "
        f"Provider: {assistant.config.provider}."
    )
    print("Type your message. Commands: /skills, /config, /quit\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in {"/quit", "/exit", "/q"}:
            break
        if text == "/skills":
            _cmd_skills(assistant)
            continue
        if text == "/config":
            _cmd_config(assistant)
            continue
        result = assistant.handle(text)
        tag = f"[{result.skill}] " if result.skill else ""
        print(f"bot> {tag}{result.reply}\n")
    print("Bye -- your data stayed on this machine.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)
    assistant = Assistant(config=config)

    try:
        if args.command == "skills":
            return _cmd_skills(assistant)
        if args.command == "config":
            return _cmd_config(assistant)
        if args.once is not None:
            return _run_once(assistant, args.once)
        # Default (no sub-command, or explicit 'chat'): interactive REPL.
        return _repl(assistant)
    finally:
        assistant.close()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
