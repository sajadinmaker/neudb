# neuDB storage model

Source: `neudb/__init__.py: Database._table_path, Table._save, Table._load/_reload`.

* Database = directory. Table = single JSON file `{id: record}`, written with `json.dump(indent=2)`.
* Table-name validation: `^[A-Za-z0-9_]+$` plus `path.parent == db_dir` check (anti-traversal). `list_tables()` globs `*.json`.
* Write path (`Table._save`): `mkdir -p`, `tempfile.mkstemp(prefix=.{name}., suffix=.tmp)` in the same directory, `json.dump + flush + os.fsync + os.replace`, `finally` unlink leftover temp.
* Why temp+replace: on POSIX, `os.replace` is atomic — readers never see a half-written table file; a crash mid-write leaves the old file intact plus a stray `.*.tmp`.
* Reads: full-file `json.load` into memory on every `_reload`; no partial reads, no paging at storage layer (HTTP layer caps `limit≤1000`).
* No indexes, no compaction, no checksums, no backups. Human-readable by design (`cat` is the debugger).
