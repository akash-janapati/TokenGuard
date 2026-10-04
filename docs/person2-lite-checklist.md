# Person 2 — "P2-lite" Build Checklist

**Goal:** produce the token-savings number P3 needs, in ≤ 2 hours, with no AST / no graph / no embeddings.
**Success metric:** on the frozen demo repo, `saved_pct >= 50%` and `POST /context` returns the agreed contract.

> The expensive 20% (AST, dependency graph, summarization, semantic similarity) only moves the number from ~75% to ~82%. Skip it. Protect the number, not the technique.

---

## File layout

```text
context_engine/
  __init__.py
  config.py      # defaults (excludes, extensions, top_k, max_tokens, max_file_bytes)
  models.py      # Pydantic: ContextRequest, ContextResult, Chunk, TokenStats, Redaction
  walker.py      # repo ingestion + exclusion filtering  -> list[FileInfo]
  selector.py    # relevance scoring + top-K selection   -> list[Chunk]
  tokens.py      # TokenCounter (tiktoken, chars/4 fallback) + per-file cache
  redact.py      # regex secret scanner/redactor         -> (text, list[Redaction])
  engine.py      # ContextEngine.build() orchestration
  api.py         # FastAPI app exposing POST /context
run_demo.py      # CLI: prints the before/after table for the demo queries
```

That's 9 files; the whole thing is small. Keep each file single-purpose so if time runs out, the pipeline still runs with stubs.

---

## Module responsibilities (minimal behavior)

### `config.py`
```python
EXCLUDE_DIRS = {".git","node_modules","dist","build","out",".venv","venv","__pycache__",".next","coverage"}
EXCLUDE_EXT  = {".min.js",".map",".lock",".png",".jpg",".jpeg",".gif",".pdf",".zip",".ico",".woff",".woff2"}
CODE_EXT     = {".py",".ts",".tsx",".js",".jsx",".go",".rs",".java",".rb",".cs",".c",".cpp",".h",".md",".json",".yaml",".yml"}
TOP_K        = 8
MAX_TOKENS   = 4000
MAX_FILE_BYTES = 512 * 1024
```
All overridable per request.

### `models.py` — the frozen contract
Reuse the `ContextResult` shape from `person2-context-engine-spec.md` §2.1 verbatim: `context_text`, `selected_files`, `chunks[]`, `tokens{original,selected,saved,saved_pct}`, `redactions[]`, `stats{}`. **Do not invent new field names** — P1 and P3 already code against these.

### `walker.py`
```python
def walk_repo(repo_path: str, cfg: ContextConfig) -> list[FileInfo]
```
- `os.walk`, prune `EXCLUDE_DIRS` in-place, skip `EXCLUDE_EXT`, skip files > `MAX_FILE_BYTES`.
- Keep only `CODE_EXT` (`.md`/`.json` optional, include for demo realism).
- Record `{path, rel_path, size, mtime, text}`.
- Returns list; `stats.files_scanned = len(...)`.

### `selector.py`
```python
def select(query: str, files: list[FileInfo], cfg) -> list[Chunk]
```
Scoring (keep it dumb and explainable):
1. Tokenize query → terms (split camelCase/snake_case, lowercase, drop stopwords).
2. `path_score` = fraction of terms found in `rel_path` (e.g. `login` in `src/auth/login.ts`).
3. `content_score` = fraction of distinct terms appearing anywhere in file text.
4. `score = 0.6 * path_score + 0.4 * content_score`; tie-break by shorter path (stable, reproducible).
5. Sort desc, take `TOP_K`, but stop when `running_tokens > MAX_TOKENS`.
6. If all scores are 0 (no match): fall back to the K most recently modified code files, flagged `reason="fallback: recent"`.
- Each `Chunk` = one whole file in P2-lite (no line windows). Set `start_line=1`, `end_line=<file line count>`.
- Attach `reason` string for the demo, e.g. `"path match: login; content match: auth"`.

> Whole-file chunks are fine. Line-window chunking can be added later by splitting `text` into 200-line pieces; don't build it now.

### `tokens.py`
```python
class TokenCounter:
    def count(self, text: str) -> int: ...   # tiktoken cl100k_base, else ceil(len/4)
def count_repo_tokens(files, counter) -> int
```
- Try `import tiktoken` once at startup; if missing, use the char heuristic and set `counter` label accordingly.
- Cache `(path, mtime, size) -> token_count` in a module-level dict so repeated demo runs are instant.

### `redact.py`
```python
def redact(text: str, counter) -> tuple[str, list[Redaction]]
```
Five high-precision rules only:
- `(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*["']?([^\s"']+)`
- `sk-[A-Za-z0-9]{16,}`
- `ghp_[A-Za-z0-9]{20,}`
- `AKIA[0-9A-Z]{16}`
- `-----BEGIN[^-]*PRIVATE KEY-----`
Replace the **value** with `[REDACTED]`, keep the key name. Record `{file, line, rule, preview}` where `preview` is itself redacted. Run on the final `context_text` bytes only.

### `engine.py`
```python
class ContextEngine:
    def build(self, req: ContextRequest) -> ContextResult
```
Pipeline: `walk → select → assemble context_text → redact → count → build stats`. Enforce the hard `MAX_TOKENS` cap after assembly. Assemble each file as:
```text
// file: src/auth/login.ts
<content>
```
Keep the file header even when truncating.

### `api.py`
Thin FastAPI wrapper: `POST /context` → `engine.build(...)`. Nothing else. Person 1 calls this.

### `run_demo.py`
CLI that runs 3 fixed queries against the frozen repo and prints the P3-ready table (see §3). This is your personal verification harness — build it early so you can measure continuously.

---

## 2-hour schedule

| Clock | Task | Done when |
|---|---|---|
| 0:00–0:15 | `config.py` + `models.py` + `__init__` | Imports work, contract fields locked |
| 0:15–0:45 | `walker.py` | Prints file list, skips `node_modules`/`.git`, counts `files_scanned` |
| 0:45–1:05 | `tokens.py` | `count_repo_tokens()` prints total for the frozen repo |
| 1:05–1:35 | `selector.py` | "Why is login failing?" returns `login.ts`/`auth.ts` in top-K |
| 1:35–1:50 | `engine.py` assembly + cap + `redact.py` | `context_text` ≤ cap, fake `API_KEY` shows `[REDACTED]` |
| 1:50–2:00 | `api.py` + `run_demo.py`, record numbers | P1 can `curl /context`; savings table captured |

**Cut order if behind:** `.gitignore` support → `.md/.json` inclusion → content_score (use path only) → redaction (stub returns empty list). **Never cut:** walker exclusions, selection, hard cap, token counting.

---

## Acceptance checks

- [ ] `POST /context` returns exactly the agreed `ContextResult` schema.
- [ ] `context_text` never exceeds `max_tokens`.
- [ ] `saved_pct >= 50%` on the frozen demo repo.
- [ ] Fake `API_KEY="abc123"` appears as `API_KEY="[REDACTED]"` in output, with a `redactions` entry.
- [ ] Same inputs → identical output (deterministic).
- [ ] One query with all-zero relevance falls back gracefully (non-empty result).
- [ ] `files_scanned`, `files_considered`, `files_selected`, `duration_ms` all populated for P3.

---

## Handoff to P3

Person 3 needs only these fields, nested inside P1's `/chat` response:
```json
"tokens": {"original": 12500, "selected": 3100, "saved": 9400, "saved_pct": 75.2},
"redactions": [{"file": "auth.ts", "line": 14, "rule": "api_key"}],
"selected_files": ["src/auth/login.ts", "src/auth/auth.ts"],
"stats": {"files_scanned": 214, "files_selected": 3, "duration_ms": 412}
```
Confirm with P3 in the first 15 minutes that these names match their dashboard bindings. No direct P2↔P3 calls.
