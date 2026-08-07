def test_health_requires_no_auth(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_missing_auth_header_rejected(client):
    resp = client.get("/assets/search?query=pump")
    assert resp.status_code == 401


def test_wrong_token_rejected(client):
    resp = client.get("/assets/search?query=pump", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401


def test_trace_id_is_generated_when_absent(client, auth_headers):
    resp = client.get("/alarms?page=1&page_size=1", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers.get("x-trace-id")


def test_trace_id_is_echoed_when_provided(client, auth_headers):
    headers = {**auth_headers, "trace_id": "trace-test-123"}
    body = {
        "asset_ids": ["AST-1001"],
        "time_range": {"start_time": "2026-05-01T00:00:00", "end_time": "2026-08-01T00:00:00"},
    }
    resp = client.post("/alarms/summary", json=body, headers=headers)
    assert resp.status_code == 200
    assert resp.headers["x-trace-id"] == "trace-test-123"
