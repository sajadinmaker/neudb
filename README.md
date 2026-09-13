# neuDB

Lightweight embedded Python storage experiment exploring persistence, search, and AI memory.

## Problem

Local prototypes and agents need inspectable persistence without running PostgreSQL.

## Solution

A zero-dependency folder of human-readable JSON tables with atomic writes and pure-Python text + cosine search. Published on [PyPI](https://pypi.org/project/neudb/) (0.4.0 live).

## What it is / is NOT

- IS: `neudb/__init__.py` — `connect`, `Database`, `Table`, CLI; `cat *.json` is the debugger.
- IS: optional AI-memory tables (`users`, `sessions`, `messages`, `tags`, `memories`) and optional FastAPI/agent examples.
- NOT: a PostgreSQL competitor. No server, no index, no transactions, no multi-process safety, no scale.

## Why it exists

To debug what an LLM agent remembered on disk without pgvector, and to learn where stdlib persistence breaks.

## Architecture

```text
Python library / CLI
  ↓
Table = one JSON file {id: record}
  ↓ (temp + fsync + os.replace)
Database = directory of tables
  ↓
Optional FastAPI / agent / dashboard (examples, not core)
```

See `docs/architecture.md`.

## Key Engineering Decisions

1. JSON files for readability and trivial backup.
2. Temp-file + `fsync` + `os.replace` for crash-atomic single-file writes.
3. Per-path `threading.RLock` for same-process threads only.
4. Brute-force scans (no index) to stay dependency-free.
5. Extras (`api`, `agent`, `test`) keep core at `dependencies = []`.

## Tech Stack

Python (stdlib only for core) · optional FastAPI · optional sentence-transformers

## Features

1. Create/list/insert/select/update/delete with traversal-safe names
2. Atomic file replace on write
3. Thread-serialized writes (single process)
4. Case-insensitive text search
5. Cosine-similarity vector search with text fallback
6. CLI + minimal HTTP + memory-schema helpers

## Running Locally

```bash
pip install -e .
neudb table create users
neudb row insert users --data '{"username":"alice"}'
neudb row list users
pip install -e ".[test,api]" && pytest
```

## Testing

`tests/test_table.py`, `test_search.py`, `test_api.py`, `test_ai_schema.py`, `test_agent.py`: CRUD, persistence, auth flow, memory upserts. Missing: concurrent-write, corruption, crash-recovery, load tests.

## Performance

No published benchmarks. Do not cite latency numbers. Protocol in `docs/performance.md` (insert/read/search at 10K/100K, threaded writes).

## Limitations

Full-file rewrite/read per op; O(N) queries; no index/pagination in core; thread-only locking; bare `json.load` (no repair); embeddings bloat JSON. Website “indexed search” claim fixed to full-scan.

## Future Improvements

File locking for multi-process, safe-load + corruption tests, documented size limits or a real index, measured benchmarks, single demo (keep `realworld_coding_assistant.py`).

## Learned

~450 lines of stdlib suffice for the experiment; the API/agent/dashboard/website layers hid that simplicity and should stay examples, not core.
