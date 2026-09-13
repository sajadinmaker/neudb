# neuDB engineering decisions

* Why a directory of JSON files? Zero dependencies, human-readable, trivial backup (`cp -r`), `cat`-debuggable. Trade-off: full-file rewrite per write, full-file load per read, no indexes — write/read cost grows with table size.
* Why temp-file + fsync + replace? Cheapest atomic-commit primitive on POSIX without a WAL. Gives crash-atomic single-file writes with stdlib only.
* Why `threading.RLock` only? Covers the common single-process threaded case (e.g. FastAPI workers in one process) with no new dependencies. Multi-process safety was deferred (would need `fcntl` locking + reload discipline).
* Why no index? Prototype scale + dependency-free constraint. Every query is a scan; adding any index (B-tree for filters, HNSW for vectors) would change the storage format and is a deliberate future boundary.
* Why optional FastAPI/agent/embeddings as extras? Core stays dependency-free (`dependencies = []`); `api`, `agent`/`embeddings`, `test` extras pull `fastapi/uvicorn`, `sentence-transformers`, `httpx/pytest` only when needed.
* Why per-user tables for memory (`users/sessions/messages/tags/memories`)? Makes the agent loop (`retrieve → inject → persist`) a thin layer over the same Table API instead of a second store.
* What would come next (not yet done): multiprocess file locking, corruption tests + safe-load, pagination/index or documented size limits, Dockerfile + `.env.example` (added), measured benchmarks.
