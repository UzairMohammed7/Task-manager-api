import pytest


# ---------- auth required ----------

def test_tasks_require_authentication(client):
    assert client.get("/tasks").status_code == 401
    assert client.post("/tasks", json={"title": "x"}).status_code == 401
    assert client.get("/tasks/1").status_code == 401
    assert client.patch("/tasks/1", json={"title": "x"}).status_code == 401
    assert client.delete("/tasks/1").status_code == 401


# ---------- create ----------

def test_create_task_uses_defaults(client, auth_headers):
    r = client.post("/tasks", json={"title": "Learn FastAPI"}, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Learn FastAPI"
    assert body["status"] == "todo"
    assert body["priority"] == "medium"
    assert body["description"] is None
    assert body["created_at"] and body["updated_at"]


def test_create_task_ignores_client_supplied_owner(client, auth_headers):
    me = client.get("/users/me", headers=auth_headers).json()
    r = client.post(
        "/tasks", json={"title": "Mine", "owner_id": 999}, headers=auth_headers
    )
    assert r.status_code == 201
    assert r.json()["owner_id"] == me["id"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "x", "status": "finished"},
        {"title": "x", "priority": "urgent"},
        {"title": "x", "due_date": "not-a-date"},
    ],
)
def test_create_task_validation_errors(client, auth_headers, payload):
    r = client.post("/tasks", json=payload, headers=auth_headers)
    assert r.status_code == 422


# ---------- read ----------

def test_get_task(client, auth_headers, make_task):
    task = make_task(auth_headers, title="Read me")
    r = client.get(f"/tasks/{task['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Read me"


def test_get_missing_task_is_404(client, auth_headers):
    assert client.get("/tasks/9999", headers=auth_headers).status_code == 404


def test_get_task_with_non_integer_id_is_422(client, auth_headers):
    assert client.get("/tasks/abc", headers=auth_headers).status_code == 422


# ---------- update (PATCH) ----------

def test_patch_changes_only_sent_fields(client, auth_headers, make_task):
    task = make_task(auth_headers, title="Keep me", priority="high")
    r = client.patch(
        f"/tasks/{task['id']}", json={"status": "done"}, headers=auth_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "done"
    assert body["title"] == "Keep me"
    assert body["priority"] == "high"


def test_patch_null_clears_nullable_field(client, auth_headers, make_task):
    task = make_task(auth_headers, description="temporary")
    r = client.patch(
        f"/tasks/{task['id']}", json={"description": None}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["description"] is None


@pytest.mark.parametrize("field", ["title", "status", "priority"])
def test_patch_null_on_required_field_is_422(client, auth_headers, make_task, field):
    task = make_task(auth_headers)
    r = client.patch(f"/tasks/{task['id']}", json={field: None}, headers=auth_headers)
    assert r.status_code == 422


def test_patch_invalid_enum_is_422(client, auth_headers, make_task):
    task = make_task(auth_headers)
    r = client.patch(
        f"/tasks/{task['id']}", json={"status": "finished"}, headers=auth_headers
    )
    assert r.status_code == 422


# ---------- delete ----------

def test_delete_task(client, auth_headers, make_task):
    task = make_task(auth_headers)
    r = client.delete(f"/tasks/{task['id']}", headers=auth_headers)
    assert r.status_code == 204
    assert r.content == b""
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).status_code == 404


# ---------- ownership (IDOR protection) ----------

def test_user_cannot_access_another_users_task(
    client, auth_headers, other_auth_headers, make_task
):
    alices = make_task(auth_headers, title="Alice private")
    url = f"/tasks/{alices['id']}"

    # Bob gets 404 (not 403) for every verb, so existence isn't leaked.
    assert client.get(url, headers=other_auth_headers).status_code == 404
    assert (
        client.patch(url, json={"title": "hacked"}, headers=other_auth_headers).status_code
        == 404
    )
    assert client.delete(url, headers=other_auth_headers).status_code == 404

    # Alice's task is untouched.
    r = client.get(url, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Alice private"


def test_list_only_returns_own_tasks(client, auth_headers, other_auth_headers, make_task):
    make_task(auth_headers, title="A1")
    make_task(auth_headers, title="A2")
    make_task(other_auth_headers, title="B1")

    alice = client.get("/tasks", headers=auth_headers).json()
    bob = client.get("/tasks", headers=other_auth_headers).json()

    assert alice["total"] == 2
    assert {t["title"] for t in alice["items"]} == {"A1", "A2"}
    assert bob["total"] == 1
    assert bob["items"][0]["title"] == "B1"


# ---------- pagination ----------

def test_pagination_envelope_and_order(client, auth_headers, make_task):
    for i in range(1, 6):
        make_task(auth_headers, title=f"T{i}")

    r = client.get("/tasks?limit=2&offset=2", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5  # total ignores limit/offset
    assert body["limit"] == 2
    assert body["offset"] == 2
    # Newest first: T5, T4, | T3, T2 | T1
    assert [t["title"] for t in body["items"]] == ["T3", "T2"]


def test_offset_past_the_end_returns_empty_page(client, auth_headers, make_task):
    make_task(auth_headers)
    r = client.get("/tasks?offset=100", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 1


@pytest.mark.parametrize(
    "query",
    ["limit=0", "limit=101", "offset=-1", "status=banana", "priority=urgent"],
)
def test_invalid_list_query_params_are_422(client, auth_headers, query):
    assert client.get(f"/tasks?{query}", headers=auth_headers).status_code == 422


# ---------- filtering ----------

@pytest.fixture()
def mixed_tasks(auth_headers, make_task):
    make_task(auth_headers, title="a", status="todo", priority="low")
    make_task(auth_headers, title="b", status="todo", priority="high")
    make_task(auth_headers, title="c", status="done", priority="high")
    make_task(auth_headers, title="d", status="in_progress", priority="medium")


@pytest.mark.parametrize(
    ("query", "expected_titles"),
    [
        ("status=todo", {"a", "b"}),
        ("status=done", {"c"}),
        ("priority=high", {"b", "c"}),
        ("status=todo&priority=high", {"b"}),  # filters combine with AND
        ("status=done&priority=low", set()),
    ],
)
def test_filters(client, auth_headers, mixed_tasks, query, expected_titles):
    r = client.get(f"/tasks?{query}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert {t["title"] for t in body["items"]} == expected_titles
    assert body["total"] == len(expected_titles)


# ---------- search ----------

def test_search_matches_title_or_description_case_insensitively(
    client, auth_headers, make_task
):
    make_task(auth_headers, title="Pay INVOICE", description=None)
    make_task(auth_headers, title="Groceries", description="buy invoice paper")
    make_task(auth_headers, title="Unrelated")

    r = client.get("/tasks?search=invoice", headers=auth_headers)
    assert {t["title"] for t in r.json()["items"]} == {"Pay INVOICE", "Groceries"}
    assert r.json()["total"] == 2


def test_search_treats_wildcards_literally(client, auth_headers, make_task):
    make_task(auth_headers, title="100% done")
    make_task(auth_headers, title="100 percent")
    make_task(auth_headers, title="a_b")
    make_task(auth_headers, title="axb")

    percent = client.get("/tasks?search=100%25", headers=auth_headers).json()
    assert [t["title"] for t in percent["items"]] == ["100% done"]

    underscore = client.get("/tasks?search=a_b", headers=auth_headers).json()
    assert [t["title"] for t in underscore["items"]] == ["a_b"]


def test_search_combines_with_filters_and_pagination(client, auth_headers, make_task):
    for i in range(3):
        make_task(auth_headers, title=f"report {i}", priority="high")
    make_task(auth_headers, title="report low", priority="low")
    make_task(auth_headers, title="other", priority="high")

    r = client.get("/tasks?search=report&priority=high&limit=2", headers=auth_headers)
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2