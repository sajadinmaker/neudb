<p align="center">
  <img src="docs/brand/logo-mark.jpg" alt="neuDB" width="200">
</p>

<h1 align="center">neuDB</h1>

<p align="center">
  <strong>Embedded Python database engine with persistent storage, semantic search, and AI memory capabilities.</strong><br>
  Zero dependencies · Human-readable JSON · Semantic search built in
</p>

<p align="center">
  <a href="docs/launch-video/neudb-launch-15s.mp4">
    <img src="docs/launch-video/neudb-launch-thumb.jpg" alt="neuDB launch video" width="640">
  </a>
</p>

<p align="center">
  <a href="https://pypi.org/project/neudb/"><img src="https://img.shields.io/pypi/v/neudb.svg" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="https://github.com/neuralbroker/neudb/actions"><img src="https://github.com/neuralbroker/neudb/actions/workflows/test.yml/badge.svg" alt="CI"></a>
</p>

<p align="center">
  <a href="docs/launch-video/neudb-launch-15s.mp4">Launch video</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#features">Features</a> ·
  <a href="#ai-memory">AI memory</a> ·
  <a href="#http-api">API</a> ·
  <a href="#agent">Agent</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

---

## Features

| | |
|---|---|
| **No server, no config** | A folder of JSON tables — `cat` is your debugger |
| **Semantic search** | Cosine similarity on embeddings, pure Python |
| **Text fallback** | Case-insensitive search when embeddings are off |
| **AI memory schema** | Users, sessions, messages, tags, memories |
| **Three interfaces** | Python library, CLI, optional HTTP API + agent |

## Architecture

```text
Python library / CLI
        ↓
Table (one JSON file per table, {id: record})
        ↓
Database (directory of tables, atomic file replace on write)
        ↓
Optional FastAPI (neudb/api.py, X-API-Key) → Browser dashboard
        ↓
Optional memory agent (neudb/agent.py, Ollama/OpenAI) + embeddings
```

Core engine: `neudb/__init__.py` (`Database`, `Table`, `cosine_similarity`, CLI).
HTTP layer: `neudb/api.py` (`create_app`, health/tables/records/users/sessions/messages/search).
Memory schema: `neudb/ai_schema.py` (`users`, `sessions`, `messages`, `tags`, `memories`).
See [docs/architecture.md](docs/architecture.md) for details.

## Storage Model

* One directory per database; one JSON file per table (`{id: record}`, indented JSON).
* Table names restricted to `^[A-Za-z0-9_]+$` with parent-directory check against traversal.
* Writes use same-directory temp file + `flush` + `os.fsync` + `os.replace` (atomic replace on POSIX).
* No server, no config; `cat` the JSON files to debug.
* No indexes; reads load the full table file into memory. See [docs/storage.md](docs/storage.md).

## Concurrency

* Same-process thread safety via per-path `threading.RLock` (`insert`/`update`/`delete` reload-then-write under lock).
* No multi-process file locking (`fcntl`/`flock`), no WAL, no transactions.
* Concurrent writes from multiple processes are not safe; concurrent threads are serialized per table file.
* See [docs/concurrency.md](docs/concurrency.md).

## Search

* `search_text(field, query)`: case-insensitive substring scan, pure Python.
* `search_similar(field, vector, top_k)`: brute-force cosine similarity scan over stored embedding lists.
* Embeddings are optional (`sentence-transformers/all-MiniLM-L6-v2` via `embed_text`); when unavailable, text fallback is used.
* All queries are full in-memory scans; there is no vector index. See [docs/search.md](docs/search.md).

## Failure Recovery

* Interrupted writes are mitigated by temp-file + atomic replace (original file stays intact if the process crashes mid-write; leftover `.*.tmp` files are unlinked on next save attempt).
* Corrupted JSON is not repaired: `_load` raises on invalid JSON; there are no checksums, backups, or repair tools.
* No concurrent-write, corruption, or crash-recovery tests yet — see Testing below.
* See [docs/recovery.md](docs/recovery.md).

## Benchmarks

No published benchmarks yet. Do not cite latency/throughput numbers for neuDB — none have been measured in this repository.

To add one, measure and report: insert throughput, point-read latency, `search_text`/`search_similar` latency at 10K and 100K records, and concurrent-thread write behavior. See [docs/performance.md](docs/performance.md) for the protocol.

## Testing

```bash
pip install -e ".[test,api]"
pytest
```

Covered today (`tests/test_table.py`, `test_search.py`, `test_api.py`, `test_ai_schema.py`, `test_agent.py`): CRUD round-trips, persistence across instances, stale-handle reload, cosine/text edge cases, API auth + user/session/message flow + pagination, memory schema upserts, agent context formatting, Ollama remote-URL guard.

Not yet covered: threaded concurrent writes, lock contention, duplicate writes under concurrency, corrupted-file handling, interrupted-write recovery, performance/load. Contributions adding those tests are welcome — see [docs/decisions.md](docs/decisions.md).

## Quick start

```bash
git clone https://github.com/neuralbroker/neudb.git
cd neudb
pip install -e .
```

**CLI**

```bash
neudb table create users
neudb row insert users --data '{"username":"alice"}'
neudb row list users
```

**Library**

```python
from neudb import connect

db = connect("mydb")
users = db.table("users")
users.insert({"username": "bob"})
users.search_text("username", "bo")
```

## Install extras

```bash
pip install neudb              # core only
pip install "neudb[api]"       # FastAPI HTTP server
pip install "neudb[agent]"     # LLM memory agent + embeddings
pip install "neudb[test]"      # pytest + httpx
pip install -e ".[api,agent,test]"   # development
```

## AI memory

```python
from neudb.ai_schema import *

db = init_ai_database("my_memory")
alice = add_user(db, "alice", "alice@example.com")
session = create_session(db, alice, "Chat about Python")
add_message_with_embedding(db, session, "user", "How do I fix an import error?")

# Search by meaning
vec = embed_text("Python import errors")
results = db.table("messages").search_similar("embedding", vec, top_k=5)
```

## HTTP API

```bash
pip install -e ".[api]"
export NEUDB_API_KEY="change-me"
uvicorn neudb.api:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs

### Browser dashboard

neuDB includes a local dashboard for users who prefer a visual interface:

```bash
export NEUDB_API_KEY="change-me"
uvicorn neudb.api:app --reload
cd website && python3 -m http.server 8080
```

Open http://127.0.0.1:8080/dashboard.html to create tables, browse/filter records, and add, edit, or delete JSON records.

```bash
curl -X POST http://127.0.0.1:8000/users \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me' \
  -d '{"username":"alice","email":"alice@example.com"}'
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEUDB_API_KEY` | *(required)* | Auth for all DB endpoints |
| `NEUDB_API_DB` | `neudb_api_data/` | API storage directory |
| `NEUDB_CORS_ORIGINS` | `http://127.0.0.1:8080,http://localhost:8080` | Comma-separated dashboard origins |

## Agent

Long-term memory loop for Ollama or OpenAI:

```bash
ollama pull llama3.2
pip install -e ".[agent]"
neudb-agent --provider ollama --model llama3.2
```

```bash
export OPENAI_API_KEY="..."
neudb-agent --provider openai --model gpt-4o-mini
```

Each turn: search similar messages → inject context → save the exchange.

## Demos

```bash
python demos/realworld_coding_assistant.py  # full walkthrough (recommended)
python demos/agent_demo.py                  # users, sessions, tags, memories
python demos/semantic_demo.py               # cosine similarity (2D vectors)
python demos/real_semantic_demo.py          # real embeddings
```

## Project structure

```
neudb/
├── neudb/              # Python package
│   ├── __init__.py     # Core engine (Table, Database, CLI)
│   ├── ai_schema.py    # AI memory helpers
│   ├── api.py          # FastAPI HTTP API
│   └── agent.py        # LLM memory agent
├── tests/              # pytest suite (see tests/)
├── demos/              # Example scripts
├── docs/
├── website/            # Product landing page (local)
├── pyproject.toml
└── CHANGELOG.md
```

## Development

```bash
pip install -e ".[test,api]"
pytest
flake8 neudb/ tests/ --max-line-length=120 --ignore=E402,W503
```

## License

MIT — see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
