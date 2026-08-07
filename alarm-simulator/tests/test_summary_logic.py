from datetime import datetime, timedelta

from app.logic.summary import summarize
from app.models import Alarm
from app.schemas import TimeRange


def _alarm(alarm_id, asset_id, name, severity, start, ack_delay_min=None, duration_min=None):
    start_time = start
    ack_time = start_time + timedelta(minutes=ack_delay_min) if ack_delay_min is not None else None
    end_time = start_time + timedelta(minutes=duration_min) if duration_min is not None else None
    return Alarm(
        alarm_id=alarm_id, asset_id=asset_id, asset_name=asset_id, alarm_name=name,
        alarm_type="process", severity=severity, status="cleared" if end_time else "active",
        unit="Unit 1", site="NorthPlant", start_time=start_time, end_time=end_time, ack_time=ack_time,
    )


def test_groups_by_alarm_name_and_counts():
    base = datetime(2026, 6, 1)
    alarms = [
        _alarm("A1", "AST-1", "High Vibration", "high", base, ack_delay_min=1),
        _alarm("A2", "AST-1", "High Vibration", "critical", base + timedelta(days=1), ack_delay_min=2),
        _alarm("A3", "AST-1", "Low Pressure", "medium", base + timedelta(days=2)),
    ]
    tr = TimeRange(start_time=base, end_time=base + timedelta(days=10))

    result = summarize(alarms, tr, group_by=["alarm_name"], kpis=["alarm_count", "critical_count"])

    groups = {g["alarm_name"]: g for g in result["groups"]}
    assert groups["High Vibration"]["alarm_count"] == 2
    assert groups["High Vibration"]["critical_count"] == 1
    assert groups["Low Pressure"]["alarm_count"] == 1
    assert result["total_alarm_count"] == 3


def test_avg_ack_delay_ignores_unacknowledged():
    base = datetime(2026, 6, 1)
    alarms = [
        _alarm("A1", "AST-1", "X", "high", base, ack_delay_min=1),   # 60s
        _alarm("A2", "AST-1", "X", "high", base, ack_delay_min=3),   # 180s
        _alarm("A3", "AST-1", "X", "high", base),                     # no ack_time
    ]
    tr = TimeRange(start_time=base, end_time=base + timedelta(days=1))

    result = summarize(alarms, tr, group_by=["alarm_name"], kpis=["avg_ack_delay"])
    assert result["groups"][0]["avg_ack_delay"] == 120.0


def test_suppression_candidate_rate_flags_short_lived_alarms():
    base = datetime(2026, 6, 1)
    alarms = [
        _alarm("A1", "AST-1", "X", "low", base, duration_min=0.5),
        _alarm("A2", "AST-1", "X", "low", base, duration_min=45),
    ]
    tr = TimeRange(start_time=base, end_time=base + timedelta(days=1))

    result = summarize(alarms, tr, group_by=["alarm_name"], kpis=["suppression_candidate_rate"])
    assert result["groups"][0]["suppression_candidate_rate"] == 0.5


def test_no_alarms_returns_empty_groups():
    tr = TimeRange(start_time=datetime(2026, 1, 1), end_time=datetime(2026, 1, 2))
    result = summarize([], tr, group_by=["alarm_name"], kpis=["alarm_count"])
    assert result == {"groups": [], "total_alarm_count": 0}
