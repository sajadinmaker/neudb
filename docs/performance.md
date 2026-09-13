# neuDB performance

Status: no published benchmarks. The numbers below are a protocol, not results — do not cite neuDB latency/throughput until measured.

## Protocol (to run on a fixed machine, Python version, and commit)

1. Insert throughput: time `N = 1K / 10K` single-record inserts into one table; report records/s + p50/p95 per-insert latency.
2. Point reads: time `get`/filter by id over the same sizes; report p50/p95.
3. Text search: `search_text` over 10K and 100K records; report p50/p95 and top_k effect.
4. Vector search: `search_similar` with fixed dim (e.g. 384) over 10K and 100K records; report p50/p95.
5. Concurrency: K threads × M inserts each into one table; report success count, lost-update count, wall time.
6. Environment: record CPU/RAM/disk, Python version, commit SHA, table-file sizes on disk.

## Known scaling properties (by construction, not measurement)

* Writes rewrite the whole table file; reads load the whole file. Cost grows at least linearly with table size.
* Vector/text search are linear scans. There is no index to make them sublinear.

Remove any marketing latency claim (e.g. “<50ms indexed search” in `website/`) until this protocol produces numbers.
