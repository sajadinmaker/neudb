# neuDB search

Source: `neudb/__init__.py: cosine_similarity, Table.search_similar, Table.search_text`; `neudb/ai_schema.py: embed_text`.

* `cosine_similarity(a, b)`: pure-Python, length-checked, `0.0` on zero-norm.
* `search_similar(field, vec, top_k=5)`: brute-force scan of all records, skips missing/non-list/dim-mismatch embeddings, sorts descending, returns top-k. No vector index (no HNSW/IVF/FAISS).
* `search_text(field, query, top_k=5)`: case-insensitive substring scan; `[]` on `top_k<1` or empty query.
* Embeddings: `embed_text()` lazily loads `sentence-transformers/all-MiniLM-L6-v2`; returns `None` when the package is absent, in which case callers fall back to text search.
* Complexity: O(N·D) per vector query, O(N) per text query, plus full-file JSON load. Suitable for small local memories and prototypes, not for large-scale retrieval.
