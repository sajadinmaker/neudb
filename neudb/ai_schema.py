"""AI memory helpers for neuDB.

The embedding library is intentionally discovered and imported only when an
embedding is requested. This keeps the core API and dashboard fast to start.
"""

import importlib.util

from . import connect

SentenceTransformer = None
EMBEDDING_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None
EMBED_MODEL = None


def get_embedding_model():
    """Load the embedding model on first use."""
    global EMBED_MODEL
    if not EMBEDDING_AVAILABLE:
        return None
    if EMBED_MODEL is None:
        global SentenceTransformer
        if SentenceTransformer is None:
            try:
                from sentence_transformers import SentenceTransformer as Transformer
            except ImportError:
                return None
            SentenceTransformer = Transformer
        EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return EMBED_MODEL


def embed_text(content):
    model = get_embedding_model()
    if model is None:
        return None
    return model.encode(content).tolist()


def init_ai_database(db_dir="ai_memory"):
    db = connect(db_dir)
    for name in ["users", "sessions", "messages", "tags", "memories"]:
        db.create_table(name)
    return db


def add_user(db, username, email, display_name=None, metadata=None):
    user = {
        "username": username,
        "email": email,
        "display_name": display_name or username,
        "metadata": metadata or {}
    }
    return db.table("users").insert(user)


def create_session(db, user_id, title, description="", model="", metadata=None):
    session = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "metadata": {"model": model, **(metadata or {})}
    }
    return db.table("sessions").insert(session)


def add_message(db, session_id, role, content, metadata=None):
    message = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {}
    }
    return db.table("messages").insert(message)


def add_message_with_embedding(db, session_id, role, content, metadata=None):
    message = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "embedding": embed_text(content),
        "metadata": metadata or {}
    }
    return db.table("messages").insert(message)


def add_tag(db, name):
    tags = db.table("tags")
    existing = tags.select_by("name", name)
    if existing:
        return existing[0]["id"]
    return tags.insert({"name": name})


def tag_message(db, message_id, tag_name):
    add_tag(db, tag_name)
    msg_table = db.table("messages")
    msg = msg_table.select_by("id", message_id)
    if msg:
        msg = msg[0]
        tags_list = msg.get("metadata", {}).get("tags", [])
        if tag_name not in tags_list:
            tags_list.append(tag_name)
            msg["metadata"]["tags"] = tags_list
            msg_table.update(message_id, {"metadata": msg["metadata"]})


def get_session_messages(db, session_id):
    return [m for m in db.table("messages").select_all() if m["session_id"] == session_id]


def get_user_sessions(db, user_id):
    return db.table("sessions").select_by("user_id", user_id)


def add_memory(db, user_id, key, value, metadata=None):
    memories = db.table("memories")
    for mem in memories.select_all():
        if mem["user_id"] == user_id and mem["key"] == key:
            memories.update(mem["id"], {"value": value, "metadata": metadata or {}})
            return mem["id"]
    return memories.insert({
        "user_id": user_id,
        "key": key,
        "value": value,
        "metadata": metadata or {}
    })


def get_memory(db, user_id, key):
    for mem in db.table("memories").select_all():
        if mem["user_id"] == user_id and mem["key"] == key:
            return mem["value"]
    return None
