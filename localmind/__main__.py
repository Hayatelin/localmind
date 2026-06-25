"""Entry point so the package can be run with ``python -m localmind``.

This simply delegates to :func:`localmind.cli.main`, which parses arguments and
either starts the interactive REPL or runs a single-shot/sub-command request.
"""

from .cli import main

if __name__ == "__main__":  # pragma: no cover - exercised via the CLI itself
    raise SystemExit(main())
