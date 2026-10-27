# neuDB

**A database you can read with your own eyes.** Plain JSON files for tables, crash-atomic writes, text and cosine search in pure Python, zero core dependencies.

neuDB is embedded storage for local prototypes and LLM agents that need inspectable persistence without running PostgreSQL. It is deliberately NOT a PostgreSQL competitor: no server, no index, no transactions, no multi-process safety. Honest limits, documented in code and prose, because "works on my folder" beats debugging a pager you never hear.

| | |
|---|---|
| Core | Python stdlib only, zero dependencies, `connect` / `Database` / `Table` API plus CLI |
| Correctness | 32 tests: CRUD, persistence, search, API, AI schema, agent, concurrency, recovery |
| Lint / CI | flake8 clean, suite green in CI |
| Ceiling | ~10K rows per table by design (full-file rewrite per write, O(N) confirmed) |
| Extras | `pip install -e ".[api,agent,test]"` — HTTP layer, agent memory schema, test kit |
| License | MIT |

**Where to look first**

- `neudb/__init__.py` — the whole engine: `connect`, `Database`, `Table`; `cat *.json` is the debugger
- `neudb/api.py` — optional FastAPI layer with Swagger docs, API-key auth, request-size validation
- `neudb/agent.py` + `neudb/ai_schema.py` — AI memory tables (users, sessions, messages, memories)
- `tests/test_recovery.py` — corrupted files, interrupted skipped writes, explicit commentary about guarantees
- `docs/architecture.md` + `docs/storage.md` — what is guaranteed and what is not

## Problem

Local prototypes and agents need inspectable persistence without running PostgreSQL.

## Solution

A zero-dependency folder of human-readable JSON tables with atomic writes and pure-Python text + cosine search. Install from source (see Running Locally). Promo site: https://sajadinmaker.github.io/neudb/

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

```bash
pip install -e ".[test,api]" && pytest   # 32 tests: CRUD, persistence, search, API, AI schema, agent, concurrency, recovery
```

`tests/test_concurrency.py` (8 threads × 25 inserts, readers-during-writes),
`tests/test_recovery.py` (corruption, non-object JSON, interrupted-write + explicit sweep).

## Performance

Measured 2026-09-14 via `python benchmarks/bench.py` (this machine, Python 3.11):

- 2K records (338KB): **138 inserts/s, p50 7.3ms, p95 13.7ms**; read_all 2.6ms; text search 2.9ms
- 5K records (847KB): **56 inserts/s, p50 17.5ms, p95 34.4ms**; read_all 6.9ms
- Threaded 4×100: 400/400 rows, 0 lost

Per-insert cost grows with file size (full rewrite per write — O(N) confirmed).
See `docs/performance.md`. Do not use past ~10K rows per table.

## Limitations

Full-file rewrite/read per op; O(N) queries; no index/pagination in core; thread-only locking; bare `json.load` (no repair); embeddings bloat JSON. Website “indexed search” claim fixed to full-scan.

## Future Improvements

File locking for multi-process, backup/restore round-trip test, documented 10K-row
guideline enforcement (warn on large tables), single demo kept (`demos/realworld_coding_assistant.py`).

## Learned

~450 lines of stdlib suffice for the experiment; the API/agent/dashboard/website layers hid that simplicity and should stay examples, not core.

---

## Maintenance

Last maintained: 2026-10-26 – PyPI distribution retired (claims scrubbed); flake8 clean; promo site live.
