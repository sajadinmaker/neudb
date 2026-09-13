# neuDB failure recovery

Source: `neudb/__init__.py: Table._save, Table._load`.

* Interrupted write: temp file + `os.replace` means the original table file is either fully old or fully new. A crash leaves at most a stray `.{table}.*.tmp` file, unlinked on the next `_save()` attempt in the same process. There is no orphan-temp sweeper on open.
* Corrupted data: `_load` does a bare `json.load` — invalid JSON raises to the caller. No checksum, no backup rotation, no repair command, no compaction.
* Operational guidance: back up the database directory (it is plain files); restore by copying files back. Validate JSON with `python -m json.tool <table>.json` before/after copies.
* Missing tests: corrupted-file handling, interrupted-write recovery, backup/restore. None exist yet.
