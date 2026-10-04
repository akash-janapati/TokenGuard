# Person 2 Spec — Context & Token Optimization Engine

**Owner:** Person 2
**Module name:** Context Engine
**One-line goal:** Given a coding query and a repository, send the cloud LLM the **minimum context** needed to answer, and prove the token savings.

**Success criterion:**
> Take a realistic repository and demonstrate **50–80% context/token reduction** while retaining enough information for the LLM to solve the task.

**Primary metric:** `tokens_saved_pct = 1 - selected_tokens / original_tokens`

**Explicitly out of scope (do NOT build):** GraphRAG, Neo4j, embeddings/vector DBs, sophisticated parsing, full type inference. Heuristics + AST/file relationships are enough.

---

## 1. Position in the system

```text
Person 1 Orchestrator (/chat)
        │
        │  1. receives user query + repo path
        ▼
┌───────────────────────────────┐
│   PERSON 2: CONTEXT ENGINE     │
│                               │
│  ingest → chunk → score →     │
│  select → compress → redact → │
│  count tokens → return        │
└───────────────┬───────────────┘
                │  context_text + metadata
                ▼
Person 1 Smart Router  ──►  Local LLM / Cloud LLM
                │
                │  metadata (tokens, redactions, files)
                ▼
Person 3 Analytics Dashboard
```

Person 2 is a **pure function**: `(query, repo, budget) -> (context, metadata)`. It does not call any LLM and does not make routing decisions. This keeps the boundary clean.

---

## 2. Interface contract

### 2.1 HTTP endpoint (preferred — Person 1 calls this)

```text
POST /context
```

Request:

```json
{
  "query": "Why is login failing?",
  "repo_path": "/abs/path/to/repo",
  "task_type": "debug",
  "max_tokens": 4000,
  "top_k": 8,
  "include_globs": ["src/**/*.ts"],
  "exclude_globs": [],
  "redact_secrets": true
}
```

Response:

```json
{
  "context_text": "// file: src/auth/login.ts\n...(redacted code)...",
  "selected_files": ["src/auth/login.ts", "src/auth/auth.ts", "src/services/userService.ts"],
  "chunks": [
    {
      "file": "src/auth/login.ts",
      "start_line": 12,
      "end_line": 88,
      "score": 0.91,
      "reason": "identifier match: login; import-neighbor of auth.ts"
    }
  ],
  "tokens": {
    "original": 12500,
    "selected": 3100,
    "saved": 9400,
    "saved_pct": 75.2
  },
  "redactions": [
    { "file": "src/auth/auth.ts", "line": 14, "rule": "api_key", "preview": "API_KEY=\"[REDACTED]\"" }
  ],
  "stats": {
    "files_scanned": 214,
    "files_considered": 37,
    "files_selected": 3,
    "duration_ms": 412
  }
}
```

`task_type` (optional): `explain | debug | refactor | test | general` — changes scoring weights only, never required.

### 2.2 Python module interface (for in-process use)

```python
class ContextEngine:
    def __init__(self, token_counter: TokenCounter, config: ContextConfig): ...
    def build(self, query: str, repo_path: str, budget_tokens: int) -> ContextResult: ...
```

`ContextResult` mirrors the response JSON above. Both transports return the same object; the HTTP layer is a thin wrapper.

### 2.3 Guarantees Person 1 can rely on

- Output is **always non-empty**: if scoring fails, fall back to the N highest-priority files.
- Output **never exceeds `max_tokens`** (hard cap, enforced after compression). If even the top file exceeds it, truncate with a `// [truncated]` marker.
- `context_text` is **safe to send to cloud** when `redact_secrets=true`.
- The function is **deterministic** for the same inputs (stable sort; tie-break by path) so demos are reproducible.

### 2.4 Data Person 3 needs

Person 3 reads only the metadata: `tokens`, `redactions`, `selected_files`, `stats`. No new endpoint needed — Person 1 forwards these fields in its `/chat` response, or Person 3 subscribes to the same call.

---

## 3. Pipeline stages

```text
repo_path
   │
   ▼
[1] Ingest & filter      walk files, apply excludes, drop generated/vendored
   │
   ▼
[2] Chunk                file-level + function/class-level (AST), fallback line windows
   │
   ▼
[3] Score relevance      lexical + path + import-neighborhood signals
   │
   ▼
[4] Expand dependencies  (if time) pull direct importers/imports of top files
   │
   ▼
[5] Select under budget  greedy by score density until max_tokens
   │
   ▼
[6] Compress             strip comments/blank lines, dedupe, clamp long chunks
   │
   ▼
[7] Detect & redact      regex secret scanner over selected text
   │
   ▼
[8] Count & report       original vs selected tokens, stats, redactions
```

### Stage details

**[1] Ingest & filter**
- Walk `repo_path` recursively.
- Always exclude: `.git/`, `node_modules/`, `dist/`, `build/`, `out/`, `.venv/`, `venv/`, `__pycache__/`, `*.min.js`, `*.map`, lockfiles, binary/media extensions.
- Honor `.gitignore` (via `pathspec`, lightweight) plus request `exclude_globs`.
- Cap file size (e.g. skip files > 512 KB) and count `files_scanned` for stats.
- Language detection by extension; only text/code files enter chunking.

**[2] Chunk**
- Primary unit: **function/class blocks** parsed with Python `ast` for `.py`.
- For other languages (TS/JS/etc.), use a lightweight brace/`//` heuristics or line windows; **do not** block on tree-sitter if it slows you down.
- Keep a file-level header chunk (imports + top-of-file) so the LLM knows dependencies.
- Store `{file, start_line, end_line, symbol, content, tokens}`.

**[3] Score relevance**
Lexical signal (main, cheap):
- Extract query identifiers/keywords (split camelCase/snake_case, drop stopwords).
- Score a chunk by term frequency of query terms in code + symbol names + file path.
- Bonus if the file path contains a query term (e.g. query "login" → `login.ts`).

Structural signal:
- Recency (mtime) small bonus.
- Import-neighborhood: files directly imported by / importing a high-scoring file get a secondary bonus.

Task weighting (`task_type`):
- `debug` favors error-handling / matched symbols; `test` favors target + its test file; `refactor` favors the symbol's call sites. Keep weights as a small table, default all 1.0.

Normalize scores to `0..1`; attach a human-readable `reason` for the demo.

**[4] Dependency expansion (stretch)**
- Build a file → imports map (regex for `import`/`require`).
- One-hop expansion around top-K files, re-scored with a discount factor (e.g. ×0.5). Stop after one hop to bound cost.

**[5] Selection under budget**
- Sort by `score` (stable tie-break by path).
- Greedily add chunks while `running_tokens <= max_tokens`.
- Prefer whole symbols; if a chunk doesn't fit, either skip or truncate — configurable.
- Reserve a small overhead budget for wrapper text/headers.

**[6] Compression**
- Strip comments and blank lines (language-aware light pass).
- Deduplicate identical/near-identical chunks.
- Clamp any single chunk to a max (e.g. 200 lines) with head/tail kept.
- Optional: local model summarization of long bodies — **stretch only**; must not add latency in the critical path.

**[7] Secret detection & redaction**
Regex rules (curated, high-precision to avoid false positives):
- `api key`, `secret`, `token`, `password`, `passwd`, `private_key`, `-----BEGIN * PRIVATE KEY-----`
- Common vendor prefixes: `sk-`, `ghp_`, `AKIA`, `AIza`, `xox[baprs]-`
- `.env`-style `KEY=value` lines.

Behavior: replace value with `[REDACTED]`, keep the key name, record a `redactions` entry with file/line/rule/preview (preview must itself be redacted). Run **after** compression, on the exact bytes that would be sent.

**[8] Count & report**
- `original` = tokens of the **whole filtered repo** (measure once, cache by repo hash + mtimes).
- `selected` = tokens of `context_text` after compression and redaction.
- Cache `original` per repo state so repeated demos are fast and consistent.

---

## 4. Token counting

- Interface: `TokenCounter.count(text: str) -> int`.
- Default impl: `tiktoken` `cl100k_base` (close enough; label as *approximate*).
- Fallback impl (no dependency): `ceil(len(text) / 4)` characters heuristic.
- **Important:** cloud tokenizer may differ by model. Report the counter used (`counter: "tiktoken/cl100k_base"`) so Person 3 can label the dashboard honestly.
- Cache token counts for unchanged files keyed by `(path, mtime, size)`.

---

## 5. Configuration defaults

```text
max_tokens         4000
top_k              8
max_file_bytes     524288        # skip larger files
max_chunk_lines    200
skip_comments      true
expand_deps        true          # one hop
redact_secrets     true
token_counter      tiktoken/cl100k_base
```

All overridable per-request; defaults chosen so the demo "just works".

---

## 6. Time-boxed 6-hour plan

| Time | Deliverable | Check |
|---|---|---|
| 0:00–0:45 | Repo walker + exclusion rules + language detection | Prints file list, skips `node_modules`/`.git` |
| 0:45–1:30 | Chunking (Python AST + fallback line windows) | Emits `{file, lines, tokens}` chunks |
| 1:30–2:30 | **Token counting for original vs selected** | Prints `original / selected / saved %` |
| 2:30–3:45 | Relevance scoring + budget selection | "Why is login failing?" picks auth files |
| 3:45–4:30 | Compression (strip comments, dedupe, clamp) | Selected tokens drop further, code still valid |
| 4:30–5:15 | Secret redaction + `redactions` metadata | Fake `API_KEY` shows as `[REDACTED]` |
| 5:15–6:00 | Wire `POST /context`, freeze demo repo, record numbers | Person 1 can call it; numbers reproducible |

**Cut order if behind:** dependency expansion → comment stripping → AST chunking (fall back to line windows). **Never cut:** token counting, selection, Budget cap, redaction.

---

## 7. Demo script (the proof)

Freeze one small-but-real repo (e.g. an auth sample app). Run three queries and capture the table:

```text
Query                  Original   Selected   Saved
─────────────────────────────────────────────────
"Why is login failing?"  12,500     3,100    75.2%
"Explain userService"      9,800     2,400    75.5%
"Add a unit test for X"    8,100     2,900    64.2%
```

Then show one redaction and the selected file list. Hand the `context_text` to Person 1's `/chat` to prove the LLM still answers correctly with the smaller context — **accuracy retained** is what makes the reduction credible.

---

## 8. Failure modes & fallbacks

| Risk | Mitigation |
|---|---|
| No match for query terms | Fall back to top files by size/recency; still under budget |
| Single file exceeds budget | Truncate chunk with `// [truncated]`; keep imports |
| Unknown language | Line-window chunking, coment-strip disabled |
| tiktoken unavailable | Chars/4 heuristic; flag `counter` in response |
| Repo huge (>5k files) | Bounded walk + file cap; measure `original` on filtered set only |
| Redaction false positive | Only redact assigned values, keep key names; log rule for review |

---

## 9. Definition of done

- [ ] `POST /context` returns the contract in §2.1.
- [ ] Hard `max_tokens` cap never exceeded.
- [ ] Token savings visible and reproducible on the frozen demo repo (target ≥ 50%).
- [ ] Secrets redacted with a reportable `redactions` list.
- [ ] Person 1 can drop context into `/chat` without changes.
- [ ] Person 3 can render savings from the metadata alone.
- [ ] No LLM calls inside the Context Engine.
