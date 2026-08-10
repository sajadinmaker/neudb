from fastapi.testclient import TestClient

import neudb.ai_schema as ai_schema
from neudb.api import create_app


API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}


def test_api_rejects_missing_api_key(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    response = client.post("/users", json={"username": "alice", "email": "alice@example.com"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key."


def test_api_user_session_message_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_schema, "EMBEDDING_AVAILABLE", False)
    monkeypatch.setattr(ai_schema, "EMBED_MODEL", None)
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    user_response = client.post(
        "/users",
        headers=AUTH_HEADERS,
        json={"username": "alice", "email": "alice@example.com", "display_name": "Alice"},
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    session_response = client.post(
        "/sessions",
        headers=AUTH_HEADERS,
        json={"user_id": user_id, "title": "Debugging", "model": "codellama"},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    message_response = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": session_id, "role": "user", "content": "How do I fix imports?"},
    )
    assert message_response.status_code == 201
    assert message_response.json()["message"]["embedding"] is None

    messages_response = client.get(f"/sessions/{session_id}/messages", headers=AUTH_HEADERS)
    assert messages_response.status_code == 200
    messages = messages_response.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "How do I fix imports?"


def test_api_search_with_vector(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_schema, "EMBEDDING_AVAILABLE", False)
    monkeypatch.setattr(ai_schema, "EMBED_MODEL", None)
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    first = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Python", "embedding": [1.0, 0.0]},
    )
    second = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Weather", "embedding": [0.0, 1.0]},
    )

    response = client.post("/search", headers=AUTH_HEADERS, json={"vector": [1.0, 0.0], "top_k": 1})

    assert response.status_code == 200
    assert response.json()["results"] == [first.json()["message"]]
    assert second.json()["message"] not in response.json()["results"]


def test_api_search_requires_query_or_vector(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    response = client.post("/search", headers=AUTH_HEADERS, json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide either 'vector' or 'query'."


def test_api_search_falls_back_to_text_when_embeddings_are_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_schema, "embed_text", lambda content: None)
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))
    matching = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Python import help"},
    )
    client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Weather report"},
    )

    response = client.post("/search", headers=AUTH_HEADERS, json={"query": "python", "top_k": 5})

    assert response.status_code == 200
    assert response.json()["results"] == [matching.json()["message"]]


def test_api_dashboard_table_and_record_crud(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    create_table = client.post("/tables", headers=AUTH_HEADERS, json={"name": "notes"})
    assert create_table.status_code == 201
    assert "notes" in client.get("/tables", headers=AUTH_HEADERS).json()["tables"]

    created = client.post("/tables/notes/records", headers=AUTH_HEADERS, json={"title": "hello"})
    assert created.status_code == 201
    record_id = created.json()["id"]

    updated = client.patch(
        f"/tables/notes/records/{record_id}", headers=AUTH_HEADERS, json={"title": "updated"}
    )
    assert updated.status_code == 200
    assert updated.json()["record"]["title"] == "updated"

    listed = client.get("/tables/notes/records", headers=AUTH_HEADERS).json()
    assert listed["total"] == 1
    assert listed["records"][0]["title"] == "updated"

    deleted = client.delete(f"/tables/notes/records/{record_id}", headers=AUTH_HEADERS)
    assert deleted.status_code == 200
    assert client.get("/tables/notes/records", headers=AUTH_HEADERS).json()["total"] == 0
