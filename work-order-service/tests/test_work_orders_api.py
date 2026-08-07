def test_health_requires_no_auth(client):
    assert client.get("/health").status_code == 200


def test_missing_auth_rejected(client):
    assert client.get("/work-orders").status_code == 401


def test_maintenance_history_for_seeded_asset(client, auth_headers):
    resp = client.get("/assets/AST-1001/maintenance-history", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_id"] == "AST-1001"
    assert len(body["history"]) >= 1
    assert all(h["status"] == "completed" for h in body["history"])


def test_maintenance_history_empty_for_unknown_asset(client, auth_headers):
    resp = client.get("/assets/AST-9999/maintenance-history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["history"] == []


def test_search_work_orders_by_asset(client, auth_headers):
    resp = client.get("/work-orders?asset_id=AST-1001", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_get_work_order_by_id(client, auth_headers):
    listing = client.get("/work-orders?asset_id=AST-1001", headers=auth_headers).json()
    work_order_id = listing["data"][0]["work_order_id"]
    resp = client.get(f"/work-orders/{work_order_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["work_order_id"] == work_order_id


def test_get_work_order_404_for_unknown_id(client, auth_headers):
    resp = client.get("/work-orders/WO-does-not-exist", headers=auth_headers)
    assert resp.status_code == 404


def test_draft_does_not_persist(client, auth_headers):
    before = client.get("/work-orders?asset_id=AST-2001", headers=auth_headers).json()["total"]
    draft = client.post(
        "/work-orders/draft",
        json={"asset_id": "AST-2001", "title": "Check bearing", "description": "recurring vibration"},
        headers=auth_headers,
    )
    assert draft.status_code == 200
    assert draft.json()["status"] == "draft"
    after = client.get("/work-orders?asset_id=AST-2001", headers=auth_headers).json()["total"]
    assert after == before


def test_create_without_confirm_is_rejected(client, auth_headers):
    resp = client.post(
        "/work-orders",
        json={"asset_id": "AST-2001", "title": "Check bearing", "confirm": False},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_create_with_confirm_persists(client, auth_headers):
    before = client.get("/work-orders?asset_id=AST-2001", headers=auth_headers).json()["total"]
    resp = client.post(
        "/work-orders",
        json={"asset_id": "AST-2001", "title": "Check bearing", "description": "recurring vibration", "confirm": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"
    after = client.get("/work-orders?asset_id=AST-2001", headers=auth_headers).json()["total"]
    assert after == before + 1
