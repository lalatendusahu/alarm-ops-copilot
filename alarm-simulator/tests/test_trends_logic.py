from datetime import datetime, timedelta

from app.logic.trends import compute_trends
from app.models import Alarm
from app.schemas import TimeRange


def _alarm(alarm_id, start, ack_delay_min=None):
    ack_time = start + timedelta(minutes=ack_delay_min) if ack_delay_min is not None else None
    return Alarm(
        alarm_id=alarm_id, asset_id="AST-1", asset_name="AST-1", alarm_name="X", alarm_type="process",
        severity="medium", status="active", unit="Unit 1", site="NorthPlant", start_time=start, ack_time=ack_time,
    )


def test_daily_bucketing_groups_alarms_by_day():
    base = datetime(2026, 6, 1)
    alarms = [
        _alarm("A1", base + timedelta(hours=2)),
        _alarm("A2", base + timedelta(hours=20)),
        _alarm("A3", base + timedelta(days=1, hours=3)),
    ]
    tr = TimeRange(start_time=base, end_time=base + timedelta(days=2))

    result = compute_trends(alarms, tr, bucket="daily", metrics=["alarm_count"])

    assert result["bucket"] == "daily"
    assert len(result["buckets"]) == 2
    assert result["buckets"][0]["alarm_count"] == 2
    assert result["buckets"][1]["alarm_count"] == 1


def test_hourly_bucketing():
    base = datetime(2026, 6, 1, 8, 0, 0)
    alarms = [_alarm("A1", base + timedelta(minutes=10)), _alarm("A2", base + timedelta(hours=1, minutes=5))]
    tr = TimeRange(start_time=base, end_time=base + timedelta(hours=3))

    result = compute_trends(alarms, tr, bucket="hourly", metrics=["alarm_count"])

    assert len(result["buckets"]) == 3
    assert result["buckets"][0]["alarm_count"] == 1
    assert result["buckets"][1]["alarm_count"] == 1
    assert result["buckets"][2]["alarm_count"] == 0


def test_avg_ack_delay_metric_per_bucket():
    base = datetime(2026, 6, 1)
    alarms = [_alarm("A1", base, ack_delay_min=1), _alarm("A2", base, ack_delay_min=3)]
    tr = TimeRange(start_time=base, end_time=base + timedelta(days=1))

    result = compute_trends(alarms, tr, bucket="daily", metrics=["alarm_count", "avg_ack_delay"])

    assert result["buckets"][0]["avg_ack_delay"] == 120.0


def test_alarms_outside_window_are_excluded():
    base = datetime(2026, 6, 1)
    alarms = [_alarm("A1", base - timedelta(days=5)), _alarm("A2", base + timedelta(hours=1))]
    tr = TimeRange(start_time=base, end_time=base + timedelta(days=1))

    result = compute_trends(alarms, tr, bucket="daily", metrics=["alarm_count"])

    assert sum(b["alarm_count"] for b in result["buckets"]) == 1
