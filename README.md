# TokenGuard

> **A local-first AI gateway for coding assistants.**
>
> Use a small on-device model for simple coding tasks and intelligently send only the difficult tasks and relevant context to a cloud LLM — reducing token usage, cost, latency, and code exposure.

TokenGuard is not another coding LLM. It is an **intelligent inference layer** that decides *where* and *how much* AI should be used.

---

## Why

Cloud-only coding assistants send every request — and often a huge slice of your repository — to a remote model. That means:

- High token cost for trivial tasks (regex, syntax fixes, quick explanations)
- High latency for tasks a local model could handle instantly
- Unnecessary code exposure to third parties

TokenGuard routes each request to the cheapest, fastest, most private model that can actually answer it, and compresses context before anything leaves your machine.

---

## Features

| Feature | What it does | Implementation |
|---|---|---|
| 🧠 **Smart Router** | Decides Local vs Cloud | Rule-based scoring initially; later ML classifier |
| 🔄 **Confidence-based escalation** | Local model answers if confident; otherwise cloud | Local LLM returns `answer + confidence` |
| 🔍 **Smart Context Selection** | Sends only relevant code | AST / file dependency analysis + relevance scoring |
| 🗜️ **Context Compression** | Reduces tokens before cloud request | Local summarization / code chunk selection |
| 💰 **Token Optimizer** | Tracks and minimizes cloud tokens | Estimate tokens before/after filtering |
| 🔐 **Privacy Guard** | Prevents secrets from reaching cloud | Local regex/secret scanner → redact |
| ⚡ **Response Cache** | Avoids repeated LLM calls | Prompt + code hash → SQLite cache |
| 📊 **Analytics Dashboard** | Shows savings and performance | Track local/cloud requests, tokens, latency, cost |

---

## Architecture

```text
                  VS Code Extension
                         │
                         ▼
                  ┌──────────────┐
                  │ Orchestrator │
                  └──────┬───────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Task Analyzer   Context Engine   Privacy Guard
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                    Smart Router
                    /          \
                   ▼            ▼
             Local LLM       Cloud LLM
             Ollama          API
                   \            /
                    ▼          ▼
                       Response
                         │
                         ▼
                    VS Code UI
```

---

## Smart Router

Rather than training a model right away, start with a transparent rule-based score:

```text
score =
  complexity
+ context_size
+ files_involved
+ reasoning_requirement
+ local_uncertainty
```

Then route:

```text
score < 0.35  → Local
0.35–0.65     → Local first → escalate if uncertain
> 0.65        → Cloud
```

The local model responds with its answer and a confidence signal:

```json
{
  "answer": "...",
  "confidence": 0.82,
  "needs_cloud": false
}
```

If confidence is low, the orchestrator escalates to the cloud.

---

## Smart Context

Instead of sending the whole repository to the cloud:

```text
10,000 lines → Cloud
```

TokenGuard narrows the context first:

```text
Repository
    ↓
Find relevant files/functions
    ↓
Dependency analysis
    ↓
Relevant context
    ↓
2,000 lines → Cloud
```

Example result:

> **14,200 tokens → 3,100 tokens → 78% reduction**

---

## Tech Stack

| Layer | Choice |
|---|---|
| VS Code Extension | TypeScript |
| Orchestrator | Python + FastAPI |
| Local LLM | Ollama + small coding model |
| Cloud LLM | Any available API |
| Code analysis | Tree-sitter / AST |
| Cache | SQLite |
| Analytics | React or simple web dashboard |

---

## Getting Started

### Layout

| Path | What |
|---|---|
| `localpilot/app/` | Orchestrator API (FastAPI): analyzer, router, local/cloud LLM clients |
| `localpilot/optimizer/` | Context engine (relevant-file selection, compression, secret redaction) |
| `localpilot/ui.py` | Optional Streamlit demo UI (same flow as the extension) |
| `tokenguard/` | VS Code extension: the LocalPilot sidebar |

### Prerequisites

- [Ollama](https://ollama.com/) running locally with the local model pulled (default `qwen2.5-coder:7b`, set `LOCAL_MODEL` to change):

  ```bash
  ollama pull qwen2.5-coder:7b
  ```

- Python 3.9+
- Node.js 18+ (only to rebuild the extension; `tokenguard/out/` is committed)
- Optional: an Anthropic or OpenAI-compatible API key. Without one, `CLOUD_PROVIDER=mock` returns a stand-in cloud answer so the whole pipeline still runs.

### 1. Backend (Orchestrator)

```bash
cd localpilot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set CLOUD_PROVIDER / API keys here
uvicorn app.main:app --reload --port 8000
```

Check it: `curl localhost:8000/health`

### 2. VS Code extension (sidebar)

```bash
cd tokenguard
npm install
npm run compile
```

Open the `tokenguard/` folder in VS Code and press `F5`. In the Extension Development Host window, **open the project folder you want to ask about**
(it is sent as `repo_path`), then click the LocalPilot icon in the activity bar.

The backend URL is the `tokenguard.apiUrl` setting (default `http://localhost:8000`).

### How a prompt flows

1. The sidebar sends the prompt, the editor selection (`code`) and the workspace folder (`repo_path`) to `POST /analyze`. No model is called yet.
2. The sidebar shows the decision (`local` / `local_first` / `cloud`), the complexity score, the reasons, and how many tokens the global LLM would receive.
3. Simple or medium tasks run on the **local LLM** automatically; the answer card offers **Use global LLM** if you're not satisfied (highlighted when local confidence is low).
4. Complex tasks wait for you: **Use local LLM** or **Use global LLM (recommended)**.
5. The choice calls `POST /chat` with `force_route` = `local` or `cloud`. The global route only gets the optimized, secret-redacted context.

---

## Roadmap

### Must-have

1. VS Code / simple coding UI
2. Local LLM connection
3. Cloud LLM connection
4. Smart router
5. Token measurement
6. Basic context filtering
7. Demo dashboard

### If time remains

8. Secret redaction
9. Response caching
10. AST-based dependency analysis

---

## The Demo: Before / After

The same five requests, cloud-only vs TokenGuard:

```text
                    Cloud-only       TokenGuard
────────────────────────────────────────────────
Simple regex          800 tokens       0 cloud
Explain function     1,200 tokens       0 cloud
Fix syntax            900 tokens        0 cloud
Unit test            2,000 tokens       600 tokens
Multi-file refactor  8,500 tokens     3,200 tokens
────────────────────────────────────────────────
Total               13,400 tokens     3,800 tokens

                     ~72% fewer cloud tokens
```

The before/after measurement is the centerpiece of the presentation.

---

## Positioning

**TokenGuard is not a coding LLM. It is the inference layer that decides where your tokens go.**

- Keep simple work on-device
- Escalate only when necessary
- Send only the context that matters
- Keep secrets off the wire
