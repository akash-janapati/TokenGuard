"""Context optimizer - owned by Person 2. See optimizer/README.md for the contract.

The router imports exactly these two functions from this package. Keep their signatures;
put the real work in other modules inside optimizer/ (ingest, relevance, compress, redact...).
While a function raises NotImplementedError, the router uses its built-in fallback.
"""
from typing import Optional, Tuple

from app.contracts import ContextResult
from app.tokens import count_tokens  # use this counter so both sides agree on token numbers


def optimize_context(prompt: str, repo_path: Optional[str], code: str = "", token_budget: int = 3000) -> ContextResult:
    """Pick the code relevant to `prompt`, compress it, redact secrets, stay within `token_budget`.

    prompt:       the user's request, e.g. "Fix the login bug"
    repo_path:    absolute path to the project, or None
    code:         code the user selected in the editor ("" if none) - always relevant, include it first
    token_budget: hard limit for count_tokens(result.context)
    """
    raise NotImplementedError


def redact_text(text: str) -> Tuple[str, int]:
    """Optional: mask secrets in free text (used on the prompt). Returns (redacted_text, secrets_found)."""
    raise NotImplementedError
