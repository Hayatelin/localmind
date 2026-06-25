"""LocalMind: a privacy-first, local AI assistant gateway.

All data stays on the user's machine. LocalMind routes user input to drop-in
"skills" (Python plugins) and only falls back to a language-model provider when
no skill matches. The default provider is a fully offline, rule-based "mock"
provider, so the whole project runs end-to-end with no API key and no internet.

Public version string is exposed as ``localmind.__version__``.
"""

__version__ = "0.1.0"
__author__ = "VictorLin"
__all__ = ["__version__", "__author__"]
