def test_alarm_trends_endpoint(client, auth_headers):
    resp = client.post(
        "/alarms/trends",
        json={
            "asset_ids": ["AST-1001"],
            "time_range": {"start_time": "2026-05-01T00:00:00", "end_time": "2026-05-08T00:00:00"},
            "bucket": "daily",
            "metrics": ["alarm_count", "avg_ack_delay"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket"] == "daily"
    assert len(body["buckets"]) == 7


def test_priority_score_endpoint(client, auth_headers):
    alarm_id = client.get("/alarms?asset_id=AST-1001&page=1&page_size=1", headers=auth_headers).json()["data"][0]["alarm_id"]
    resp = client.post("/alarms/priority-score", json={"alarm_id": alarm_id}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["priority_score"] <= 100
    assert body["priority_band"] in {"low", "medium", "high", "critical"}


def test_operator_recommendations_with_context(client, auth_headers):
    alarm_id = client.get("/alarms?asset_id=AST-1001&page=1&page_size=1", headers=auth_headers).json()["data"][0]["alarm_id"]
    resp = client.post(
        "/recommendations/operator-actions",
        json={"alarm_id": alarm_id, "include_related": True, "include_asset_context": True, "include_historical_pattern": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommended_actions"]
    assert "asset_context" in body
    assert "historical_pattern" in body


def test_recommendations_404_for_unknown_alarm(client, auth_headers):
    resp = client.post("/recommendations/operator-actions", json={"alarm_id": "ALM-999999"}, headers=auth_headers)
    assert resp.status_code == 404


def test_kpi_calculation_generate_then_execute_chain(client, auth_headers):
    gen = client.post(
        "/calculation-code/generate",
        json={"calculation_type": "critical_alarm_density", "filters": {"unit": "Unit 3", "start_time": "2026-05-01T00:00:00", "end_time": "2026-08-01T00:00:00"}},
        headers=auth_headers,
    )
    assert gen.status_code == 200
    calculation_id = gen.json()["calculation_id"]

    exe = client.post("/calculation-code/execute", json={"calculation_id": calculation_id}, headers=auth_headers)
    assert exe.status_code == 200
    assert exe.json()["status"] == "completed"
    assert "critical_alarm_density" in exe.json()["result"]


def test_kpi_generate_rejects_unknown_type(client, auth_headers):
    resp = client.post("/calculation-code/generate", json={"calculation_type": "not_real"}, headers=auth_headers)
    assert resp.status_code == 400


def test_kpi_execute_404_for_unknown_calculation_id(client, auth_headers):
    resp = client.post("/calculation-code/execute", json={"calculation_id": "calc-does-not-exist"}, headers=auth_headers)
    assert resp.status_code == 404


def test_flood_analysis_on_unit_2_finds_seeded_burst(client, auth_headers):
    resp = client.post(
        "/alarms/flood-analysis",
        json={"unit": "Unit 2", "time_range": {"start_time": "2026-05-01T00:00:00", "end_time": "2026-08-01T00:00:00"}, "threshold_count": 10, "rolling_window_minutes": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["flood_windows"]) >= 1


def test_kpi_definitions_endpoint(client, auth_headers):
    resp = client.get("/analytics/kpi-definitions", headers=auth_headers)
    assert resp.status_code == 200
    names = {k["name"] for k in resp.json()["kpis"]}
    assert "alarm_count" in names
