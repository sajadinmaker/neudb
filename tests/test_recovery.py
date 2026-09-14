"""Recovery: corruption surfaces cleanly, interrupted writes can't half-apply."""

import pytest

from neudb import CorruptedTableError, connect


def test_corrupted_file_raises_corrupted_error(tmp_path):
    db = connect(str(tmp_path))
    users = db.table("users")
    users.insert({"username": "alice"})
    # Corrupt the file on disk.
    path = tmp_path / "users.json"
    path.write_text("{ not valid json !!!", encoding="utf-8")

    with pytest.raises(CorruptedTableError) as exc_info:
        db.table("users")
    assert str(tmp_path) in str(exc_info.value)


def test_non_object_json_rejected(tmp_path):
    (tmp_path / "users.json").write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(CorruptedTableError):
        connect(str(tmp_path)).table("users")


def test_interrupted_write_leaves_old_data_intact(tmp_path):
    """A stray .tmp file (crash between mkstemp and os.replace) never affects reads.

    Sweeping is explicit (Table.sweep_orphan_tmps), never on open: deleting
    temps on open would race live writers in other threads (see
    test_concurrency.py history). The table file itself is untouched by a crash.
    """
    import time

    db = connect(str(tmp_path))
    users = db.table("users")
    users.insert({"username": "alice"})
    # Simulate a crash: temp file exists, real file untouched.
    stray = tmp_path / ".users.json.abc123.tmp"
    stray.write_text('{"bogus": true}', encoding="utf-8")
    # Make it look old enough to be sweepable, then sweep explicitly.
    old = time.time() - 1000
    import os

    os.utime(stray, (old, old))

    reopened = db.table("users")  # must not crash, must not sweep live files
    assert reopened.select_by("username", "alice")
    assert stray.exists()  # opener leaves rebuttable debris alone
    removed = reopened.sweep_orphan_tmps()
    assert ".users.json.abc123.tmp" in removed
    assert not stray.exists()
    assert reopened.select_by("username", "alice")


def test_duplicate_ids_last_write_wins_explicitly(tmp_path):
    db = connect(str(tmp_path))
    t = db.table("docs")
    rid = t.insert({"id": "fixed", "v": 1})
    assert rid == "fixed"
    t.insert({"id": "fixed", "v": 2})
    assert t.select_all() == [{"id": "fixed", "v": 2}]
