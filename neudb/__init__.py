#!/usr/bin/env python3
"""
neuDB - lightweight embedded Python storage experiment (zero dependencies).

One JSON file per table ({id: record}), atomic writes via temp + fsync +
os.replace, per-path threading.RLock (same process only), brute-force text +
cosine search. NOT a server, index, or PostgreSQL replacement.

Usage as CLI:
  python neudb.py table create <name>
  python neudb.py row insert <table> --data '<json>'
  python neudb.py row list <table>
  python neudb.py row find <table> --where <key=value>
  python neudb.py row search <table> --field embedding --vector '[0.1,0.2,...]'

Usage as library:
  import neudb
  db = neudb.connect("mydata")
  users = db.table("users")
  users.insert({"username": "alice"})
  users.insert({"text": "hello", "embedding": [0.1, 0.2]})
  results = users.search_similar("embedding", [0.1, 0.2])
"""

import json
import re
import os
import sys
import uuid
import math
import tempfile
import threading
from pathlib import Path
from typing import Dict, List


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
_PATH_LOCKS = {}
_PATH_LOCKS_GUARD = threading.Lock()


class CorruptedTableError(ValueError):
    """Raised when a table file exists but is not valid JSON.

    Subclasses ValueError so existing `except ValueError` callers keep working,
    while new code can catch the specific case and decide (restore from backup,
    quarantine the file, abort). The offending path is on `.path`.
    """

    def __init__(self, path: Path, message: str):
        self.path = path
        super().__init__(f"{message}: {path}")


def validate_identifier(value: str, label: str = "identifier") -> str:
    """Validate a table or field identifier used to build paths/query records."""
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {label}: use only letters, numbers, and underscores.")
    return value


def _lock_for_path(path: Path):
    key = str(path.resolve())
    with _PATH_LOCKS_GUARD:
        if key not in _PATH_LOCKS:
            _PATH_LOCKS[key] = threading.RLock()
        return _PATH_LOCKS[key]


# ----------------------------------------------------------------------
# Helper: cosine similarity
# ----------------------------------------------------------------------
def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Return the cosine similarity between two vectors of equal length."""
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must be the same length.")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ----------------------------------------------------------------------
# Core engine
# ----------------------------------------------------------------------
class Table:
    """Represents a single table stored as a JSON file."""

    def __init__(self, path: str):
        self.path = Path(path)
        self._data: Dict[str, dict] = {}
        self._load()

    def sweep_orphan_tmps(self, max_age_seconds: float = 300) -> list[str]:
        """Remove stray temp files from interrupted `_save` calls.

        Explicit maintenance — deliberately NOT run on open: a concurrent
        writer in another thread/process may have a live temp file with the
        same pattern, and deleting it mid-write corrupts that write
        (found by tests/test_concurrency.py: sweep-on-open deleted a live
        temp and the writer's os.replace failed with FileNotFoundError).
        Only files older than max_age_seconds are removed. Returns basenames.
        """
        import time

        removed: list[str] = []
        try:
            parent = self.path.parent
            if not parent.exists():
                return removed
            now = time.time()
            for tmp in parent.glob(f".{self.path.name}.*.tmp"):
                try:
                    if now - tmp.stat().st_mtime < max_age_seconds:
                        continue
                    tmp.unlink()
                    removed.append(tmp.name)
                except OSError:
                    pass
        except OSError:
            pass
        return removed

    def _read_file(self) -> Dict[str, dict]:
        try:
            with open(self.path, 'r', encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise CorruptedTableError(
                self.path, f"table file is not valid JSON ({exc})"
            ) from exc
        except UnicodeDecodeError as exc:
            raise CorruptedTableError(
                self.path, f"table file is not valid UTF-8 ({exc})"
            ) from exc
        if not isinstance(data, dict):
            raise CorruptedTableError(
                self.path, f"table file must contain a JSON object, got {type(data).__name__}"
            )
        return data

    def _load(self):
        if self.path.exists():
            with _lock_for_path(self.path):
                self._data = self._read_file()

    def _reload(self):
        """Refresh this handle so multiple Table instances do not go stale."""
        if not self.path.exists():
            self._data = {}
            return
        with _lock_for_path(self.path):
            self._data = self._read_file()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = _lock_for_path(self.path)
        temp_path = None
        with lock:
            fd, temp_name = tempfile.mkstemp(
                dir=str(self.path.parent),
                prefix=f".{self.path.name}.",
                suffix=".tmp",
            )
            temp_path = Path(temp_name)
            try:
                with os.fdopen(fd, 'w', encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self.path)
            finally:
                if temp_path is not None and temp_path.exists():
                    temp_path.unlink()

    def insert(self, record: dict) -> str:
        """Insert a record. If no 'id' field, auto-generate UUID."""
        if not isinstance(record, dict):
            raise TypeError("record must be a dictionary")
        with _lock_for_path(self.path):
            self._reload()
            id = record.get("id") or str(uuid.uuid4())
            record["id"] = id
            self._data[id] = record
            self._save()
            return id

    def insert_with_embedding(self, record: dict, embedding: List[float]) -> str:
        """Insert a record and attach an embedding vector."""
        record["embedding"] = embedding
        return self.insert(record)

    def select_all(self) -> List[dict]:
        self._reload()
        return list(self._data.values())

    def select_by(self, key: str, value: str) -> List[dict]:
        validate_identifier(key, "field name")
        self._reload()
        return [r for r in self._data.values() if str(r.get(key)) == value]

    def update(self, id: str, updates: dict):
        if not isinstance(updates, dict):
            raise TypeError("updates must be a dictionary")
        with _lock_for_path(self.path):
            self._reload()
            if id in self._data:
                self._data[id].update(updates)
                self._save()

    def delete(self, id: str):
        with _lock_for_path(self.path):
            self._reload()
            if id in self._data:
                del self._data[id]
                self._save()

    def exists(self, id: str) -> bool:
        self._reload()
        return id in self._data

    def search_similar(self, field: str, query_vector: List[float], top_k: int = 5) -> List[dict]:
        """Return top_k records sorted by cosine similarity of 'field' to query_vector."""
        validate_identifier(field, "field name")
        if top_k < 1:
            return []
        self._reload()
        results = []
        for record in self._data.values():
            vec = record.get(field)
            if vec is not None and isinstance(vec, list):
                try:
                    sim = cosine_similarity(query_vector, vec)
                    results.append((sim, record))
                except ValueError:
                    continue
        # Sort descending by similarity
        results.sort(key=lambda x: x[0], reverse=True)
        return [record for (sim, record) in results[:top_k]]

    def search_text(self, field: str, query: str, top_k: int = 5) -> List[dict]:
        """Return top_k records where field contains query, case-insensitive."""
        validate_identifier(field, "field name")
        if top_k < 1:
            return []
        self._reload()
        query_text = query.lower()
        if not query_text:
            return []
        results = []
        for record in self._data.values():
            value = record.get(field)
            if value is not None and query_text in str(value).lower():
                results.append(record)
        return results[:top_k]


class Database:
    """A database is a folder containing table files."""

    def __init__(self, db_dir: str):
        self.db_dir = Path(db_dir).expanduser().resolve()

    def _table_path(self, name: str) -> Path:
        table_name = validate_identifier(name, "table name")
        path = (self.db_dir / f"{table_name}.json").resolve()
        if self.db_dir != path.parent:
            raise ValueError("Table path escapes database directory.")
        return path

    def table(self, name: str) -> Table:
        return Table(self._table_path(name))

    def list_tables(self) -> List[str]:
        """Return table names currently present in this database directory."""
        if not self.db_dir.exists():
            return []
        return sorted(path.stem for path in self.db_dir.glob("*.json") if path.is_file())

    def create_table(self, name: str):
        """Create a new table (just create an empty file)."""
        path = self._table_path(name)
        if not path.exists():
            table = Table(path)
            table._save()
            print(f"Table '{name}' created.")
        else:
            print(f"Table '{name}' already exists.")


def connect(db_dir: str = "neudb_data") -> Database:
    """Connect to (or create) a database directory."""
    os.makedirs(db_dir, exist_ok=True)
    return Database(db_dir)


# ----------------------------------------------------------------------
# CLI interface (extended with search)
# ----------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]
    db = connect()

    if command == "table" and len(sys.argv) >= 4:
        action = sys.argv[2]
        name = sys.argv[3]
        if action == "create":
            db.create_table(name)
        else:
            print("Unknown table action. Use 'create'.")

    elif command == "row":
        if len(sys.argv) < 4:
            print("Usage: row <action> <table> [options]")
            return
        action = sys.argv[2]
        table_name = sys.argv[3]
        table = db.table(table_name)

        if action == "insert":
            if "--data" in sys.argv:
                idx = sys.argv.index("--data")
                data_str = sys.argv[idx + 1]
                record = json.loads(data_str)
                id = table.insert(record)
                print(f"Inserted with ID: {id}")
            else:
                print("Use --data '<json>'")

        elif action == "list":
            rows = table.select_all()
            for row in rows:
                print(row)

        elif action == "find":
            if "--where" in sys.argv:
                idx = sys.argv.index("--where")
                condition = sys.argv[idx + 1]
                if "=" in condition:
                    key, value = condition.split("=", 1)
                    rows = table.select_by(key.strip(), value.strip())
                    for row in rows:
                        print(row)
                else:
                    print("Format: --where key=value")
            else:
                print("Use --where key=value")

        elif action == "delete":
            if "--id" in sys.argv:
                idx = sys.argv.index("--id")
                id = sys.argv[idx + 1]
                table.delete(id)
                print(f"Deleted {id}")
            else:
                print("Use --id <id>")

        elif action == "search":
            if "--field" in sys.argv and "--vector" in sys.argv:
                field_idx = sys.argv.index("--field")
                field_name = sys.argv[field_idx + 1]
                vec_idx = sys.argv.index("--vector")
                vec_str = sys.argv[vec_idx + 1]
                query_vector = json.loads(vec_str)
                results = table.search_similar(field_name, query_vector)
                for row in results:
                    print(row)
            else:
                print("Usage: row search <table> --field <field_name> --vector '[0.1,0.2,...]'")

        else:
            print("Unknown row action. Use: insert, list, find, delete, search.")

    else:
        print("Unknown command. Use 'table' or 'row'.")


if __name__ == "__main__":
    main()
