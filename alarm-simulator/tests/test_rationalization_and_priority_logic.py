from datetime import datetime, timedelta

from app.logic.priority import score_alarm
from app.logic.rationalization import find_candidates
from app.models import Alarm, Asset


def _alarm(alarm_id, asset_id, name, severity, start, duration_min=None):
    end_time = start + timedelta(minutes=duration_min) if duration_min is not None else None
    return Alarm(
        alarm_id=alarm_id, asset_id=asset_id, asset_name=asset_id, alarm_name=name,
        alarm_type="device", severity=severity, status="cleared" if end_time else "active",
        unit="Unit 1", site="NorthPlant", start_time=start, end_time=end_time,
    )


def test_rationalization_flags_recurrence():
    base = datetime(2026, 6, 1)
    alarms = [_alarm(f"A{i}", "AST-1", "High Vibration", "high", base + timedelta(days=i)) for i in range(6)]
    result = find_candidates(alarms, recurrence_threshold=5, stale_minutes_threshold=999999)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["reasons"] == ["recurrence"]


def test_rationalization_flags_stale_duration():
    base = datetime(2026, 6, 1)
    alarms = [_alarm("A1", "AST-1", "Stuck Valve", "medium", base, duration_min=300)]
    result = find_candidates(alarms, recurrence_threshold=999, stale_minutes_threshold=180)
    assert result["candidates"][0]["reasons"] == ["stale_duration"]


def test_rationalization_ignores_alarms_below_thresholds():
    base = datetime(2026, 6, 1)
    alarms = [_alarm("A1", "AST-1", "Occasional", "low", base, duration_min=5)]
    result = find_candidates(alarms, recurrence_threshold=5, stale_minutes_threshold=180)
    assert result["candidates"] == []


def test_priority_score_weighs_severity_criticality_and_recurrence():
    asset = Asset(asset_id="AST-1", asset_name="Pump", asset_type="Pump", unit="Unit 1", site="NorthPlant",
                   criticality="high", status="active", install_date="2020-01-01")
    base = datetime(2026, 6, 15)
    target = _alarm("A5", "AST-1", "High Vibration", "critical", base)
    history = [_alarm(f"H{i}", "AST-1", "High Vibration", "high", base - timedelta(days=i)) for i in range(1, 5)] + [target]

    result = score_alarm(target, asset, history)

    assert result["factors"]["severity_weight"] == 40
    assert result["factors"]["asset_criticality_weight"] == 30
    assert result["factors"]["recurrence_weight"] == 10  # 4 prior occurrences + itself, * 2
    assert result["priority_band"] in {"high", "critical"}


def test_priority_score_low_for_minor_isolated_alarm():
    asset = Asset(asset_id="AST-2", asset_name="Valve", asset_type="Valve", unit="Unit 4", site="SouthPlant",
                   criticality="low", status="active", install_date="2020-01-01")
    target = _alarm("A1", "AST-2", "Position Deviation", "low", datetime(2026, 6, 1), duration_min=1)
    result = score_alarm(target, asset, [target])
    assert result["priority_band"] == "low"
