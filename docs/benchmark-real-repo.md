# Benchmark: Context Engine on Real Repositories

*Generated 2026-10-04 by `bench/benchmark_context.py`.*

- Token counter: `tiktoken/cl100k_base` (exact for the cloud tokenizer family)
- Config: `max_tokens=8000`, `expand_deps=True`, adaptive `top_k` by complexity {'low': 3, 'medium': 5, 'high': 8}
- Baseline ("original") = all source files matched by the dataset globs.
- Modes: `file` = whole-file selection; `symbol` = symbol chunks + import graph.

### Methodology

- Ground truth = the files a maintainer would consult to answer the query. It is
  a *lower bound* on necessary context, not the full set.
- **Recall** = fraction of ground-truth files present in the selected context
  (the primary metric — did we send what is needed?).
- **Precision** = fraction of selected files that are ground truth. Extra files
  are usually dependency neighbors, so low precision is not automatically bad.
- Both modes share the same token budget and the same adaptive `top_k`.
- `expand_deps=True` for both; only `symbol` can act on the import graph.


## psf/requests (Python)

- Path: `/tmp/opencode/repos/requests`
- Commit: `611c6162cbc4`
- Source globs: `['src/requests/*.py']`

| # | Complexity | K | Query | Mode | Original | Selected | Saved | Files | Recall | Precision | Missing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | low | 3 | What does the requests.get function do? | file | 49479 | 7997 | 83.8% | 3 | 0.00 | 0.00 | src/requests/api.py |
| 1 | low | 3 | What does the requests.get function do? | symbol | 49479 | 7332 | 85.2% | 9 | 1.00 | 0.11 | - |
| 2 | low | 3 | How are cookies extracted from a response? | file | 49479 | 7992 | 83.8% | 2 | 1.00 | 0.50 | - |
| 2 | low | 3 | How are cookies extracted from a response? | symbol | 49479 | 7973 | 83.9% | 9 | 1.00 | 0.11 | - |
| 3 | medium | 5 | How does a Session prepare and send an HTTP request? | file | 49479 | 7995 | 83.8% | 2 | 0.67 | 1.00 | src/requests/models.py |
| 3 | medium | 5 | How does a Session prepare and send an HTTP request? | symbol | 49479 | 7976 | 83.9% | 15 | 1.00 | 0.20 | - |
| 4 | medium | 5 | How does requests handle an HTTP redirect such as a  | file | 49479 | 7994 | 83.8% | 1 | 0.33 | 1.00 | src/requests/adapters.py, src/requests/sessions.py |
| 4 | medium | 5 | How does requests handle an HTTP redirect such as a  | symbol | 49479 | 7962 | 83.9% | 15 | 1.00 | 0.20 | - |
| 5 | high | 8 | How does the HTTPAdapter manage connection pooling,  | file | 49479 | 8000 | 83.8% | 2 | 1.00 | 1.00 | - |
| 5 | high | 8 | How does the HTTPAdapter manage connection pooling,  | symbol | 49479 | 7948 | 83.9% | 14 | 1.00 | 0.14 | - |
| 6 | high | 8 | Trace the complete lifecycle of requests.get from th | file | 49479 | 8000 | 83.8% | 2 | 0.50 | 1.00 | src/requests/api.py, src/requests/models.py |
| 6 | high | 8 | Trace the complete lifecycle of requests.get from th | symbol | 49479 | 7984 | 83.9% | 17 | 1.00 | 0.24 | - |


### Detail: 'How does the HTTPAdapter manage connection pooling, retries and SSL co' (file)

- tokens: 49479 -> 8000 (83.8% saved)
- recall=1.00 precision=1.00
- selected chunks (2 total; first 12):
  - `src/requests/adapters.py` L1-749 score=0.377778 [path match: adapter; content match: adapter, connection, http, httpadapter, manage]
  - `src/requests/sessions.py` L1-921 score=0.355556 [content match: adapter, configuration, connection, http, httpadapter; truncated to fit budget]


### Detail: 'How does the HTTPAdapter manage connection pooling, retries and SSL co' (symbol)

- tokens: 49479 -> 7948 (83.9% saved)
- recall=1.00 precision=0.14
- selected chunks (20 total; first 12):
  - `src/requests/adapters.py::HTTPAdapter` L158-237 score=0.764371 [symbol match: adapter, http, httpadapter; path match: adapter; content match: adapter, connection, http, httpadapter, manage]
  - `src/requests/sessions.py::Session` L395-474 score=0.750155 [content match: adapter, configuration, connection, http, manage]
  - `src/requests/models.py::__module__` L1-107 score=0.454317 [content match: adapter, connection, http, httpadapter, ssl]
  - `src/requests/__init__.py::__module__` L109-220 score=0.251307 [content match: connection, http, ssl]
  - `src/requests/exceptions.py::SSLError` L78-79 score=0.24504 [symbol match: ssl; content match: connection, ssl]
  - `src/requests/auth.py::HTTPDigestAuth` L264-343 score=0.191769 [symbol match: http; content match: connection, http]
  - `src/requests/cookies.py::MockRequest` L31-111 score=0.173099 [content match: http, manage]
  - `src/requests/api.py::request` L24-71 score=0.16451 [content match: http, ssl]
  - `src/requests/utils.py::resolve_proxies` L911-939 score=0.130247 [content match: configuration]
  - `src/requests/help.py::__module__` L1-34 score=0.098902 [content match: ssl]
  - `src/requests/__version__.py` L1-15 score=0.065608 [content match: http]
  - `src/requests/_types.py::__module__` L53-189 score=0.065608 [content match: http]
  - … and 8 more chunks


### Detail: 'Trace the complete lifecycle of requests.get from the public API throu' (file)

- tokens: 49479 -> 8000 (83.8% saved)
- recall=0.50 precision=1.00
- missed ground truth: src/requests/api.py, src/requests/models.py
- selected chunks (2 total; first 12):
  - `src/requests/adapters.py` L1-749 score=0.342857 [path match: adapter, requests; content match: adapter, back, get, object, requests]
  - `src/requests/sessions.py` L1-921 score=0.285714 [path match: requests, session; content match: adapter, back, get, object, requests; truncated to fit budget]


### Detail: 'Trace the complete lifecycle of requests.get from the public API throu' (symbol)

- tokens: 49479 -> 7984 (83.9% saved)
- recall=1.00 precision=0.24
- selected chunks (17 total; first 12):
  - `src/requests/sessions.py::SessionRedirectMixin` L127-206 score=0.359501 [symbol match: session; path match: requests, session; content match: adapter, back, get, object, requests]
  - `src/requests/adapters.py::HTTPAdapter` L578-657 score=0.330689 [symbol match: adapter; path match: adapter, requests; content match: adapter, get, object, requests, response]
  - `src/requests/__init__.py::__module__` L109-220 score=0.29156 [path match: requests; content match: api, back, get, requests, response]
  - `src/requests/api.py::request` L24-71 score=0.291372 [path match: api, requests; content match: get, object, requests, response, session]
  - `src/requests/_types.py::__module__` L53-189 score=0.270118 [path match: requests; content match: api, complete, get, requests, response]
  - `src/requests/models.py::PreparedRequest` L378-457 score=0.263087 [path match: requests; content match: back, get, object, requests, response]
  - `src/requests/utils.py::get_unicode_from_response` L633-671 score=0.251746 [symbol match: get, response; path match: requests; content match: back, get, object, requests, response]
  - `src/requests/cookies.py::MockRequest` L31-111 score=0.203323 [path match: requests; content match: back, get, object, requests, response]
  - `src/requests/status_codes.py::__module__` L1-108 score=0.203134 [path match: requests; content match: complete, object, requests, response]
  - `src/requests/structures.py::LookupDict` L96-130 score=0.191607 [path match: requests; content match: get, object, through]
  - `src/requests/auth.py::HTTPDigestAuth` L264-343 score=0.146429 [path match: requests; content match: get, object, requests, response]
  - `src/requests/compat.py::__module__` L46-116 score=0.11862 [path match: requests; content match: back, get; summary]
  - … and 5 more chunks


## expressjs/express (JavaScript)

- Path: `/tmp/opencode/repos/express`
- Commit: `7ef98448f8b3`
- Source globs: `['lib/*.js']`

| # | Complexity | K | Query | Mode | Original | Selected | Saved | Files | Recall | Precision | Missing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | low | 3 | What does the express() factory function do? | file | 16070 | 7202 | 55.2% | 3 | 1.00 | 0.33 | - |
| 1 | low | 3 | What does the express() factory function do? | symbol | 16070 | 1501 | 90.7% | 6 | 1.00 | 0.17 | - |
| 2 | low | 3 | How does res.json serialize and send JSON? | file | 16070 | 7996 | 50.2% | 3 | 1.00 | 0.33 | - |
| 2 | low | 3 | How does res.json serialize and send JSON? | symbol | 16070 | 1495 | 90.7% | 6 | 1.00 | 0.17 | - |
| 3 | medium | 5 | How is application middleware registered and execute | file | 16070 | 7995 | 50.2% | 3 | 1.00 | 0.67 | - |
| 3 | medium | 5 | How is application middleware registered and execute | symbol | 16070 | 1490 | 90.7% | 6 | 1.00 | 0.33 | - |
| 4 | medium | 5 | How does res.redirect work with relative URLs? | file | 16070 | 7997 | 50.2% | 3 | 0.67 | 0.67 | lib/request.js |
| 4 | medium | 5 | How does res.redirect work with relative URLs? | symbol | 16070 | 2018 | 87.4% | 6 | 1.00 | 0.50 | - |
| 5 | high | 8 | Trace how app.handle processes an incoming request t | file | 16070 | 7997 | 50.2% | 2 | 0.67 | 1.00 | lib/request.js |
| 5 | high | 8 | Trace how app.handle processes an incoming request t | symbol | 16070 | 1475 | 90.8% | 6 | 1.00 | 0.50 | - |
| 6 | high | 8 | How do the request and response objects delegate to  | file | 16070 | 7997 | 50.2% | 2 | 0.67 | 1.00 | lib/utils.js |
| 6 | high | 8 | How do the request and response objects delegate to  | symbol | 16070 | 1887 | 88.3% | 6 | 1.00 | 0.50 | - |


### Detail: 'Trace how app.handle processes an incoming request through middleware ' (file)

- tokens: 16070 -> 7997 (50.2% saved)
- recall=0.67 precision=1.00
- missed ground truth: lib/request.js
- selected chunks (2 total; first 12):
  - `lib/application.js` L1-632 score=0.34 [path match: app; content match: app, handle, middleware, request, response]
  - `lib/response.js` L1-1050 score=0.26 [path match: response; content match: app, middleware, request, response, through; truncated to fit budget]


### Detail: 'Trace how app.handle processes an incoming request through middleware ' (symbol)

- tokens: 16070 -> 1475 (90.8% saved)
- recall=1.00 precision=0.50
- selected chunks (17 total; first 12):
  - `lib/application.js::use` L190-244 score=0.355971 [path match: app; content match: app, handle, middleware, request, response]
  - `lib/express.js::createApplication` L36-56 score=0.276957 [symbol match: app; content match: app, handle, request, response]
  - `lib/request.js` L243-267 score=0.225578 [path match: request; content match: app, incoming, request]
  - `lib/response.js` L488-505 score=0.224131 [path match: response; content match: app, response, through]
  - `lib/utils.js` L61-65 score=0.04362 [content match: app]
  - `lib/view.js::render` L133-159 score=0.04362 [content match: app]
  - `lib/request.js::req` L30-30 score=0.181958 [path match: request; content match: incoming]
  - `lib/express.js` L62-64 score=0.147791 [content match: app, request, response]
  - `lib/application.js` L143-150 score=0.27407 [path match: app; content match: app, handle, through]
  - `lib/application.js` L246-254 score=0.276744 [path match: app; content match: app, middleware, routes]
  - `lib/request.js` L127-130 score=0.106847 [path match: request; content match: app]
  - `lib/application.js` L49-57 score=0.148806 [path match: app; content match: middleware]
  - … and 5 more chunks


### Detail: 'How do the request and response objects delegate to Node.js HTTP primi' (file)

- tokens: 16070 -> 7997 (50.2% saved)
- recall=0.67 precision=1.00
- missed ground truth: lib/utils.js
- selected chunks (2 total; first 12):
  - `lib/response.js` L1-1050 score=0.363636 [path match: js, response; content match: content, http, js, node, request]
  - `lib/request.js` L1-528 score=0.327273 [path match: js, request; content match: content, http, js, node, request; truncated to fit budget]


### Detail: 'How do the request and response objects delegate to Node.js HTTP primi' (symbol)

- tokens: 16070 -> 1887 (88.3% saved)
- recall=1.00 precision=0.50
- selected chunks (19 total; first 12):
  - `lib/response.js::contentDisposition` L15-36 score=0.446756 [symbol match: content; path match: js, response; content match: content, http, node, types]
  - `lib/utils.js` L15-22 score=0.340781 [path match: js; content match: content, http, node, types]
  - `lib/request.js` L243-267 score=0.24964 [path match: js, request; content match: content, js, request, types]
  - `lib/application.js::defaultConfiguration` L90-141 score=0.217061 [path match: js; content match: js, node, request, response]
  - `lib/express.js::bodyParser` L15-21 score=0.217061 [path match: js; content match: node, request, response]
  - `lib/view.js::debug` L16-18 score=0.112791 [path match: js; content match: node]
  - `lib/request.js::req` L30-30 score=0.159466 [path match: js, request; content match: http]
  - `lib/express.js` L58-60 score=0.112791 [path match: js; content match: types]
  - `lib/express.js` L62-64 score=0.131542 [path match: js; content match: request, response]
  - `lib/application.js` L467-469 score=0.155331 [path match: js; content match: delegate]
  - `lib/request.js::secure` L326-328 score=0.159466 [path match: js, request; content match: http]
  - `lib/request.js` L127-130 score=0.176077 [path match: js, request; content match: types]
  - … and 7 more chunks


## Aggregate

| Mode | Mean recall | Mean precision | Mean token savings |
|---|---|---|---|
| file | 0.708 | 0.708 | 67.4% |
| symbol | 1.000 | 0.264 | 86.9% |

### Recall by complexity (symbol mode)

| Complexity | Mean recall (symbol) | Queries |
|---|---|---|
| low | 1.000 | 4 |
| medium | 1.000 | 4 |
| high | 1.000 | 4 |

### Interpretation

- `symbol` recovered **100%** of ground truth vs **71%** for `file`, while sending **87%** fewer tokens on average (vs 67% for `file`).
- Recall stays at 1.00 from low to high complexity, i.e. the context layer did not degrade on harder, multi-file questions.
- The decisive case: *"What does requests.get do?"* — `file` mode missed `api.py` entirely (recall 0.00) because the token *get* is ubiquitous, while symbol matching found the `get` function definition.
- Lowest precision comes from dependency expansion and file headers; those are mostly useful context, but they inflate the file count. Tighten by lowering `top_k`, `dep_hops`, or `max_chunks_per_file` when token budget matters more than recall.

### Limitations

- Python functions in these repos are large, so a single "best chunk" can be hundreds of lines; paragraph chunking is coarse for long functions.
- One-hop import expansion can miss indirect dependencies across libraries (e.g. transport internals); recall above was still complete because the ground-truth files also co-occur lexically.
- JS/TS chunking is blank-line + brace-depth heuristic, not a real parser; it over-splits some files (many tiny blocks) but preserves coverage.
- Ground-truth labels are the author's; a different reviewer may include more files.
