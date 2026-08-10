from neudb import connect


def test_table_names_reject_path_traversal(tmp_path):
    db = connect(str(tmp_path))

    for name in ["../outside", "/tmp/outside", "bad-name", "nested/table"]:
        try:
            db.table(name)
        except ValueError as exc:
            assert "Invalid table name" in str(exc)
        else:
            raise AssertionError(f"table name should be rejected: {name}")


def test_create_table_rejects_path_traversal(tmp_path):
    db = connect(str(tmp_path))

    try:
        db.create_table("../outside")
    except ValueError as exc:
        assert "Invalid table name" in str(exc)
    else:
        raise AssertionError("create_table should reject path traversal")


def test_table_insert_select_update_delete(tmp_path):
    db = connect(str(tmp_path))
    users = db.table("users")

    user_id = users.insert({"username": "alice", "role": "admin"})

    assert users.exists(user_id)
    assert users.select_all() == [{"username": "alice", "role": "admin", "id": user_id}]
    assert users.select_by("username", "alice") == [{"username": "alice", "role": "admin", "id": user_id}]

    users.update(user_id, {"role": "owner"})

    assert users.select_by("role", "owner") == [{"username": "alice", "role": "owner", "id": user_id}]

    users.delete(user_id)

    assert users.select_all() == []
    assert not users.exists(user_id)


def test_table_persists_records_between_instances(tmp_path):
    db = connect(str(tmp_path))
    first_table = db.table("users")
    user_id = first_table.insert({"username": "bob"})

    second_table = db.table("users")

    assert second_table.select_all() == [{"username": "bob", "id": user_id}]


def test_table_handles_refresh_before_writes(tmp_path):
    db = connect(str(tmp_path))
    first_table = db.table("users")
    second_table = db.table("users")

    first_id = first_table.insert({"username": "first"})
    second_id = second_table.insert({"username": "second"})

    assert {record["id"] for record in first_table.select_all()} == {first_id, second_id}
