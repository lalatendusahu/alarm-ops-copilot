def test_search_finds_boiler_feed_pump_101(client, auth_headers):
    resp = client.get("/assets/search?query=Boiler%20Feed%20Pump%20101", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert body["results"][0]["asset_id"] == "AST-1001"


def test_asset_metadata_404_for_unknown_asset(client, auth_headers):
    resp = client.get("/assets/does-not-exist/metadata", headers=auth_headers)
    assert resp.status_code == 404


def test_alarm_list_is_paginated(client, auth_headers):
    resp = client.get("/alarms?asset_id=AST-1001&page=1&page_size=5", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert len(body["data"]) <= 5
    assert body["total"] >= len(body["data"])


def test_alarm_list_rejects_bad_sort_field(client, auth_headers):
    resp = client.get("/alarms?sort_by=not_a_field", headers=auth_headers)
    assert resp.status_code == 400


def test_get_alarm_by_id_roundtrip(client, auth_headers):
    listing = client.get("/alarms?asset_id=AST-1001&page=1&page_size=1", headers=auth_headers).json()
    alarm_id = listing["data"][0]["alarm_id"]

    resp = client.get(f"/alarms/{alarm_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["alarm_id"] == alarm_id


def test_get_alarm_by_id_404_for_unknown_id(client, auth_headers):
    resp = client.get("/alarms/ALM-999999", headers=auth_headers)
    assert resp.status_code == 404
