from datetime import datetime, timedelta

from app.logic.correlation import analyze_correlation
from app.logic.flood import analyze_flood
from app.models import Alarm


def _alarm(alarm_id, asset_id, name, severity, start):
    return Alarm(
        alarm_id=alarm_id, asset_id=asset_id, asset_name=asset_id, alarm_name=name,
        alarm_type="process", severity=severity, status="active",
        unit="Unit 1", site="NorthPlant", start_time=start,
    )


def test_flood_detects_dense_burst_and_ignores_sparse_background():
    base = datetime(2026, 6, 1, 9, 0, 0)
    burst = [_alarm(f"B{i}", "AST-1", "X", "medium", base + timedelta(seconds=30 * i)) for i in range(12)]
    background = [_alarm("S1", "AST-1", "X", "medium", base + timedelta(hours=5))]

    result = analyze_flood(burst + background, threshold_count=10, rolling_window_minutes=10)

    assert len(result["flood_windows"]) == 1
    window = result["flood_windows"][0]
    assert window["alarm_count"] == 12


def test_flood_returns_no_windows_below_threshold():
    base = datetime(2026, 6, 1, 9, 0, 0)
    alarms = [_alarm(f"A{i}", "AST-1", "X", "medium", base + timedelta(minutes=i)) for i in range(5)]
    result = analyze_flood(alarms, threshold_count=10, rolling_window_minutes=10)
    assert result["flood_windows"] == []


def test_correlation_finds_cooccurring_pair_within_lag_window():
    base = datetime(2026, 6, 1, 12, 0, 0)
    alarms = [
        _alarm("A1", "AST-1", "High Vibration", "high", base),
        _alarm("A2", "AST-2", "High Discharge Pressure", "high", base + timedelta(minutes=5)),
        _alarm("A3", "AST-3", "Unrelated", "low", base + timedelta(days=3)),
    ]
    result = analyze_correlation(alarms, ["AST-1", "AST-2", "AST-3"], lag_window_minutes=15, severity_threshold=None, min_support=1)

    pairs = {(p["asset_id_a"], p["asset_id_b"]): p for p in result["pairs"]}
    assert ("AST-1", "AST-2") in pairs
    assert pairs[("AST-1", "AST-2")]["cooccurrence_count"] == 1
    assert ("AST-1", "AST-3") not in pairs


def test_correlation_respects_severity_threshold():
    base = datetime(2026, 6, 1, 12, 0, 0)
    alarms = [
        _alarm("A1", "AST-1", "Low Sev", "low", base),
        _alarm("A2", "AST-2", "Also Low", "low", base + timedelta(minutes=2)),
    ]
    result = analyze_correlation(alarms, ["AST-1", "AST-2"], lag_window_minutes=15, severity_threshold="high", min_support=1)
    assert result["pairs"] == []
