# neuDB architecture

Source of truth: `neudb/__init__.py` (core), `neudb/api.py` (HTTP), `neudb/ai_schema.py` (memory schema), `neudb/agent.py` (memory agent).

```text
Python library / CLI (neudb/__init__.py: connect, Database, Table, main)
        ↓
Table = one JSON file {id: record} in a database directory
        ↓ (temp file + fsync + os.replace on write)
Optional FastAPI app (neudb/api.py: create_app, X-API-Key via hmac.compare_digest)
        ↓
Browser dashboard (website/dashboard.html, local only)
        ↓
Optional agent (neudb/agent.py: MemoryChatAgent + OllamaClient/OpenAIClient)
Memory tables (neudb/ai_schema.py: users, sessions, messages, tags, memories)
```

## Request paths

* Library: `connect(dir) → Database.table(name) → insert/select/update/delete/search_*`.
* CLI: `neudb table create | row insert|list|find|delete | search`.
* HTTP: `GET /health`, `GET/POST /tables`, `GET/POST /tables/{t}/records?limit≤1000&offset`, `PATCH/DELETE /tables/{t}/records/{id}`, `POST /users|/sessions|/messages`, `GET /sessions/{id}/messages`, `POST /search` (vector direct, else `query → embed_text → search_similar`, fallback `search_text`).
* Auth: `X-API-Key` required when `NEUDB_API_KEY` is set; `503` if unset, `401` if wrong. Limits: `MAX_TEXT_LENGTH=20000`, `MAX_VECTOR_DIM=4096`, `MAX_TOP_K=100`.

## What is intentionally not here

No server process for core use, no query planner, no indexes, no WAL, no transactions, no multi-process coordination. See `concurrency.md`, `recovery.md`, `decisions.md`.
