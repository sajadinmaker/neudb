# neuDB — Product Documentation

> Deep codebase documentation + user-serving product guide.
> Codebase: `/home/sajad/Projects/portfolio/neudb` | Stack: Python stdlib core, optional FastAPI/agent | PyPI: `neudb` 0.4.1 | License: MIT

## 1. What this product is

neuDB is an embedded, zero-dependency Python storage experiment: a folder of human-readable JSON tables with crash-atomic writes (`temp + fsync + os.replace`), per-path `RLock`, brute-force text + cosine search, CLI, and optional AI-memory tables + HTTP/agent examples. Explicitly NOT a PostgreSQL competitor — for local prototypes and agents needing inspectable persistence (`cat *.json` is the debugger).

**Who it's for:** Python developers prototyping agents / tools who want `pip install neudb` persistence without running Postgres.

## 2. How it works

```
pip install neudb (core: dependencies=[])
  ↓ neudb/__init__.py: connect, Database, Table
  ↓ Table = one JSON file {id: record} | Database = directory of tables
  ↓ CLI: neudb table create | row insert/list/find/search
Extras:
  .[api] neudb/api.py:create_app — X-API-Key, /tables|records|search|users|sessions|messages
  .[agent] neudb/agent.py:MemoryChatAgent, ai_schema.py (users,sessions,messages,tags,memories)
  demos/realworld_coding_assistant.py, website/dashboard.html
```

Key files: `neudb/__init__.py`, `neudb/api.py`, `neudb/ai_schema.py`, `neudb/agent.py`, `pyproject.toml`, `docs/*.md`, `benchmarks/bench.py`.

## 3. User guide (serve users)

### Library
```bash
pip install neudb
python -c "from neudb import connect; db=connect('./mydb'); t=db.table('users'); t.insert({'username':'alice'}); print(t.all())"
```

### CLI
```bash
pip install -e .
neudb table create users
neudb row insert users --data '{"username":"alice"}'
neudb row list users
```

### API server (Docker or local)
```bash
pip install -e ".[api]"
NEUDB_API_DB=./data NEUDB_API_KEY=secret uvicorn neudb.api:app --port 8000
# Docker:
docker build -t neudb-api .
docker run -p 8000:8000 -v ./data:/data -e NEUDB_API_DB=/data -e NEUDB_API_KEY=secret neudb-api
# → GET /health, /tables, /records, /search
```

## 4. Configuration

- `NEUDB_API_DB` — data directory (default `neudb_api_data`)
- `NEUDB_API_KEY` — required to enable HTTP API (else 503); send as `X-API-Key`
- `NEUDB_CORS_ORIGINS` — CSV allow-list (default localhost:8080)

## 5. Deployment / operations

- Library: PyPI `neudb` (version in `pyproject.toml`); keep `CHANGELOG.md` in sync
- API: Dockerfile (uvicorn, `HEALTHCHECK /health`); persist `NEUDB_DIR` volume; single-process only (no multi-process safety)
- Limits (by design): full-file rewrite/read per op O(N); no index/pagination; ~10K rows/table ceiling; bare `json.load` (no repair); embeddings bloat JSON
- Benchmarks (2026-09-14, Python 3.11): 2K rows 138 ins/s p50 7.3ms; 5K rows 56 ins/s p50 17.5ms; threaded 4×100 400/400

## 6. Roadmap (if productized)

Multi-process file locking, backup/restore round-trip test, 10K-row warn enforcement, single demo only, pagination/index or documented ceiling.

## 7. Verification

```bash
pip install -e ".[test,api]" && pytest  # 32 tests
python benchmarks/bench.py
```
