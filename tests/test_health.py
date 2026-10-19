def test_hello(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_db_health(client):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json() == {"database": "ok"}