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

> Scaffolding is in progress. The steps below describe the intended setup.

### Prerequisites

- [Ollama](https://ollama.com/) running locally with a small coding model pulled, e.g.:

  ```bash
  ollama pull qwen2.5-coder:1.5b
  ```

- Python 3.10+
- Node.js 18+
- API key for a cloud LLM provider

### Backend (Orchestrator)

```bash
cd orchestrator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### VS Code Extension

```bash
cd extension
npm install
npm run compile
```

Press `F5` in VS Code to launch the Extension Development Host.

### Configuration

Create a `.env` file in the orchestrator directory:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:1.5b
CLOUD_LLM_API_KEY=your-key-here
CLOUD_LLM_MODEL=your-cloud-model
```

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
