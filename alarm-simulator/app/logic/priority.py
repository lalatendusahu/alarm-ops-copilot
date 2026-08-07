from datetime import timedelta

from app.models import Alarm, Asset

SEVERITY_WEIGHT = {"critical": 40, "high": 30, "medium": 15, "low": 5}
CRITICALITY_WEIGHT = {"high": 30, "medium": 15, "low": 5}


def score_alarm(alarm: Alarm, asset: Asset, recent_same_asset_alarms: list[Alarm]) -> dict:
    severity_weight = SEVERITY_WEIGHT.get(alarm.severity, 5)
    criticality_weight = CRITICALITY_WEIGHT.get(asset.criticality, 5)

    window_start = alarm.start_time - timedelta(days=30)
    recurrence_count = sum(
        1 for a in recent_same_asset_alarms
        if a.alarm_name == alarm.alarm_name and window_start <= a.start_time <= alarm.start_time
    )
    recurrence_weight = min(recurrence_count * 2, 20)

    if alarm.end_time is None:
        active_minutes = (
            (alarm.ack_time or alarm.start_time) - alarm.start_time
        ).total_seconds() / 60
    else:
        active_minutes = (alarm.end_time - alarm.start_time).total_seconds() / 60
    duration_weight = min(round(active_minutes / 10), 10)

    total = severity_weight + criticality_weight + recurrence_weight + duration_weight
    total = min(total, 100)

    if total >= 80:
        band = "critical"
    elif total >= 60:
        band = "high"
    elif total >= 35:
        band = "medium"
    else:
        band = "low"

    return {
        "alarm_id": alarm.alarm_id,
        "priority_score": total,
        "priority_band": band,
        "factors": {
            "severity_weight": severity_weight,
            "asset_criticality_weight": criticality_weight,
            "recurrence_weight": recurrence_weight,
            "duration_weight": duration_weight,
        },
    }
