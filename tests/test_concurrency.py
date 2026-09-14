"""Concurrency: threaded writers must not lose updates (same process)."""

import threading

from neudb import connect


def test_concurrent_writes_lose_nothing(tmp_path):
    db = connect(str(tmp_path))
    threads, per_thread = 8, 25
    errors: list = []

    def worker(n: int):
        try:
            table = db.table("events")
            for i in range(per_thread):
                table.insert({"thread": n, "i": i})
        except Exception as exc:  # pragma: no cover — fail loudly below
            errors.append(exc)

    pool = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()

    assert not errors, errors
    rows = db.table("events").select_all()
    assert len(rows) == threads * per_thread
    assert len({r["id"] for r in rows}) == threads * per_thread


def test_concurrent_readers_and_writers(tmp_path):
    """Reads reload from disk; they must never crash while a writer replaces the file."""
    import time

    db = connect(str(tmp_path))
    stop = threading.Event()
    errors: list = []

    def writer():
        table = db.table("mixed")
        i = 0
        while not stop.is_set():
            table.insert({"i": i})
            i += 1

    def reader():
        table = db.table("mixed")
        while not stop.is_set():
            try:
                table.select_all()
            except Exception as exc:
                errors.append(exc)
                return

    wt = threading.Thread(target=writer)
    readers = [threading.Thread(target=reader) for _ in range(4)]
    wt.start()
    for r in readers:
        r.start()
    time.sleep(0.5)
    stop.set()
    wt.join()
    for r in readers:
        r.join()
    assert not errors, errors
