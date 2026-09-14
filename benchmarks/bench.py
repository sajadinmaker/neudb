"""neuDB benchmarks — measured numbers, fixed protocol.

Run:  python benchmarks/bench.py --records 2000
Measures on this machine: insert throughput, point-read (select_all reload),
text search, vector search (dim=32), and threaded writes.

Writes rewrite the whole file per op, so expect O(N) degradation — that IS
the finding this benchmark documents.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neudb import connect  # noqa: E402


def _pctl(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=int, default=2000)
    args = ap.parse_args()
    n = args.records

    tmp = tempfile.mkdtemp(prefix="neudb-bench-")
    db = connect(tmp)
    table = db.table("docs")

    # Insert throughput.
    lat: list[float] = []
    t0 = time.monotonic()
    for i in range(n):
        s = time.monotonic()
        table.insert({"i": i, "text": f"record number {i} about python and databases"})
        lat.append((time.monotonic() - s) * 1000)
    insert_s = time.monotonic() - t0

    # Point read: full reload + list.
    t0 = time.monotonic()
    rows = table.select_all()
    read_ms = (time.monotonic() - t0) * 1000
    assert len(rows) == n

    # Text search.
    t0 = time.monotonic()
    hits = table.search_text("text", "python", top_k=10)
    text_ms = (time.monotonic() - t0) * 1000

    # Vector search (attach small vectors to a subset to keep file small).
    vec_table = db.table("vecs")
    dim = 32
    for i in range(min(n, 1000)):
        vec_table.insert({"i": i, "embedding": [float(i % 7)] * dim})
    query = [1.0] * dim
    t0 = time.monotonic()
    vhits = vec_table.search_similar("embedding", query, top_k=10)
    vec_ms = (time.monotonic() - t0) * 1000

    # Threaded writes: 4 threads x 100 inserts into one table.
    ttable = db.table("threaded")
    t0 = time.monotonic()
    threads = []
    for _ in range(4):
        threads.append(threading.Thread(
            target=lambda: [ttable.insert({"x": 1}) for _ in range(100)]
        ))
    [t.start() for t in threads]
    [t.join() for t in threads]
    thread_s = time.monotonic() - t0
    threaded_count = len(ttable.select_all())

    fsize_kb = (Path(tmp) / "docs.json").stat().st_size / 1024

    print(f"records={n} file={fsize_kb:.0f}KB")
    print(f"insert: {n / insert_s:.0f} rec/s total={insert_s:.2f}s "
          f"p50={_pctl(lat, 0.5):.2f}ms p95={_pctl(lat, 0.95):.2f}ms mean={statistics.mean(lat):.2f}ms")
    print(f"read_all({n}): {read_ms:.1f}ms")
    print(f"text_search({n}): {text_ms:.1f}ms hits={len(hits)}")
    print(f"vec_search(1000, dim={dim}): {vec_ms:.1f}ms hits={len(vhits)}")
    print(f"threaded(4x100): {thread_s:.2f}s total_rows={threaded_count}")


if __name__ == "__main__":
    main()
