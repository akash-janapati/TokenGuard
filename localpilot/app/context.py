"""Context optimizer adapter: the integration point with Person 2.

Person 2 develops in `localpilot/optimizer/` and exposes:
    optimize_context(prompt, repo_path, code, token_budget) -> ContextResult   (required)
    redact_text(text) -> (redacted_text, count)                                (optional)

This module calls their implementation when it is ready and falls back to the naive
keyword-based version below when it isn't (not implemented yet, or it raised), so the
router never breaks because of the optimizer.
"""
import logging
import os
import re
from typing import List, Optional, Tuple

from .contracts import ContextResult
from .tokens import count_tokens

log = logging.getLogger("localpilot.context")

SOURCE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".c", ".h",
               ".rb", ".php", ".cs", ".kt", ".swift", ".sql", ".yaml", ".yml", ".json", ".md"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".next", ".idea", ".vscode"}
MAX_FILE_BYTES = 200_000
STOPWORDS = {"the", "a", "an", "in", "on", "of", "to", "and", "or", "is", "this", "that", "fix", "my", "it", "for", "with", "code"}

try:
    import optimizer as _person2
except ImportError:
    _person2 = None


def load_repo(repo_path: str) -> List[Tuple[str, str]]:
    files = []
    for root, dirs, names in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = os.path.join(root, name)
            if os.path.splitext(name)[1] not in SOURCE_EXTS or os.path.getsize(path) > MAX_FILE_BYTES:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    files.append((os.path.relpath(path, repo_path), f.read()))
            except (UnicodeDecodeError, OSError):
                continue
    return files


def repo_stats(repo_path: Optional[str]) -> Tuple[int, int]:
    """(total_tokens, num_files) of a repo, used by the analyzer before any routing decision."""
    if not repo_path or not os.path.isdir(repo_path):
        return 0, 0
    files = load_repo(repo_path)
    return sum(count_tokens(f"# {p}\n{c}") for p, c in files), len(files)


def _render(files: List[Tuple[str, str]]) -> str:
    return "\n\n".join(f"# File: {path}\n{content}" for path, content in files)


def _fallback_optimize(prompt: str, repo_path: Optional[str], code: str, token_budget: int) -> ContextResult:
    """Naive keyword relevance, no compression, no redaction."""
    files = load_repo(repo_path) if repo_path and os.path.isdir(repo_path) else []
    full = (code + "\n\n" + _render(files)).strip()
    original_tokens = count_tokens(full)

    terms = {t for t in re.findall(r"[a-zA-Z_]{3,}", prompt.lower()) if t not in STOPWORDS}

    def relevance(item: Tuple[str, str]) -> int:
        path, content = item
        text = (path + " " + content).lower()
        return sum(text.count(t) for t in terms) + 20 * sum(t in path.lower() for t in terms)

    selected, used = [], count_tokens(code)
    for path, content in sorted(files, key=relevance, reverse=True):
        if relevance((path, content)) == 0:
            break
        t = count_tokens(f"# File: {path}\n{content}")
        if used + t > token_budget:
            continue
        selected.append((path, content))
        used += t

    context = (code + "\n\n" + _render(selected)).strip()
    return ContextResult(
        context=context,
        original_tokens=original_tokens,
        optimized_tokens=count_tokens(context),
        files_selected=[p for p, _ in selected],
    )


def optimize_context(prompt: str, repo_path: Optional[str], code: str = "", token_budget: int = 3000) -> ContextResult:
    if _person2 is not None:
        try:
            result = _person2.optimize_context(prompt, repo_path, code=code, token_budget=token_budget)
            if not isinstance(result, ContextResult):
                raise TypeError(f"expected ContextResult, got {type(result).__name__}")
            return result
        except NotImplementedError:
            pass  # Person 2's module exists but isn't ready yet
        except Exception:
            log.exception("Person 2 optimizer failed; using fallback")
    return _fallback_optimize(prompt, repo_path, code, token_budget)


def redact_text(text: str) -> Tuple[str, int]:
    """Mask secrets in free text (the prompt). No-op until Person 2 provides it."""
    fn = getattr(_person2, "redact_text", None)
    if fn is not None:
        try:
            return fn(text)
        except NotImplementedError:
            pass
        except Exception:
            log.exception("Person 2 redact_text failed; sending prompt unredacted")
    return text, 0
