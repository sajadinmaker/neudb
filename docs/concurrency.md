# neuDB concurrency

Source: `neudb/__init__.py: _PATH_LOCKS, _PATH_LOCKS_GUARD, Table.insert/update/delete`.

* Same-process threads: per-resolved-path `threading.RLock`. `insert`/`update`/`delete` do `with lock: _reload(); mutate; _save()`. This serializes threads in one process per table file.
* Reads (`select_*`, `exists`, `search_*`) call `_reload()` without holding the lock.
* What is NOT provided: multi-process locking (`fcntl`/`flock` absent), cross-machine coordination, transactions, isolation levels, WAL/replay.
* Consequence: two processes writing the same table file concurrently can lost-update (last-writer-wins on full-file replace). Do not share one database directory across processes if writes overlap.
* Missing tests: threaded concurrent writes, lock contention, duplicate writes under concurrency. See `../tests/` — none exist yet.
