# neuDB performance

Measured 2026-09-14 via `python benchmarks/bench.py` on this dev machine
(Python 3.11, local disk, commit on `main` after corruption/concurrency hardening).
Full-file rewrite per write, full-file load per read — cost grows with table size
by construction. These numbers document that, not marketing.

## Results

| Workload | 2,000 records (338KB file) | 5,000 records (847KB file) |
|---|---|---|
| Insert throughput | 138 rec/s, p50 7.3ms, p95 13.7ms | 56 rec/s, p50 17.5ms, p95 34.4ms |
| `select_all` (full reload) | 2.6ms | 6.9ms |
| `search_text` over all | 2.9ms | 6.8ms |
| `search_similar` (1K rows, dim=32) | 14.3ms | 13.7ms |
| Threaded 4×100 inserts | 1.94s, 400/400 rows, 0 lost | 2.18s, 400/400 rows, 0 lost |

## What this proves

1. Per-insert latency grows with file size (7ms → 18ms mean from 2K → 5K):
   every write rewrites the whole file. O(N) writes confirmed by measurement.
2. Reads/searches are linear scans but cheap at small sizes (single-digit ms).
3. Same-process threaded writers lose nothing (RLock + reload-inside-lock).
4. Vector search cost is dominated by row count × dim, not table-file size.

## What this does NOT prove

100K-record behavior (extrapolates to minutes per thousand writes — do not use
neuDB there), multi-process safety (none — last-writer-wins across processes),
or crash power-loss durability beyond single-file atomic replace.
