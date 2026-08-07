from collections import defaultdict

from app.models import Alarm
from app.schemas import TimeRange

ALL_KPIS = ["alarm_count", "critical_count", "recurring_rate", "avg_ack_delay", "suppression_candidate_rate"]


def summarize(alarms: list[Alarm], time_range: TimeRange, group_by: list[str] | None, kpis: list[str] | None) -> dict:
    days = max((time_range.end_time - time_range.start_time).total_seconds() / 86400, 1)
    group_by = group_by or ["asset_id"]
    kpis = kpis or ALL_KPIS

    groups: dict[tuple, list[Alarm]] = defaultdict(list)
    for alarm in alarms:
        key = tuple(getattr(alarm, field, None) for field in group_by)
        groups[key].append(alarm)

    result = []
    for key, items in groups.items():
        row = dict(zip(group_by, key))
        if "alarm_count" in kpis:
            row["alarm_count"] = len(items)
        if "critical_count" in kpis:
            row["critical_count"] = sum(1 for a in items if a.severity == "critical")
        if "recurring_rate" in kpis:
            row["recurring_rate"] = round(len(items) / days, 3)
        if "avg_ack_delay" in kpis:
            delays = [(a.ack_time - a.start_time).total_seconds() for a in items if a.ack_time]
            row["avg_ack_delay"] = round(sum(delays) / len(delays), 1) if delays else None
        if "suppression_candidate_rate" in kpis:
            short_lived = sum(
                1 for a in items if a.end_time and (a.end_time - a.start_time).total_seconds() <= 60
            )
            row["suppression_candidate_rate"] = round(short_lived / len(items), 3)
        result.append(row)

    result.sort(key=lambda r: r.get("alarm_count", 0), reverse=True)
    return {"groups": result, "total_alarm_count": len(alarms)}
