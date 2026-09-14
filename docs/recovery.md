# neuDB failure recovery

Source: `neudb/__init__.py: Table._save, Table._read_file, Table.sweep_orphan_tmps`.

* Interrupted write: temp file + `os.replace` means the original table file is
  either fully old or fully new. A crash leaves at most a stray
  `.{table}.*.tmp` file. It is harmless (reads ignore it) and removed by an
  explicit `Table.sweep_orphan_tmps()` maintenance call — deliberately NOT on
  open, because a live concurrent writer may own a temp with the same pattern
  (deleting it mid-write breaks that writer's `os.replace`; caught by
  `tests/test_concurrency.py` during development).
* Corrupted data: `_read_file` raises `CorruptedTableError` (a `ValueError`
  carrying `.path`) on invalid JSON / non-UTF-8 / non-object top level —
  instead of a bare `json.load` traceback. No checksum, no backup rotation, no
  repair command. Restore from a directory backup (plain files).
* Operational guidance: back up the database directory; validate with
  `python -m json.tool <table>.json` before/after copies.
* Tests: `tests/test_recovery.py` (corruption, non-object, interrupted write +
  explicit sweep, duplicate-id semantics). Still missing: power-loss torture,
  backup/restore round-trip.
