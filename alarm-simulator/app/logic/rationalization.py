from collections import defaultdict

from app.models import Alarm


def find_candidates(alarms: list[Alarm], recurrence_threshold: int, stale_minutes_threshold: int) -> dict:
    groups: dict[tuple, list[Alarm]] = defaultdict(list)
    for a in alarms:
        groups[(a.asset_id, a.alarm_name)].append(a)

    candidates = []
    for (asset_id, alarm_name), items in groups.items():
        durations = [
            (a.end_time - a.start_time).total_seconds() / 60
            for a in items if a.end_time
        ]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else None
        occurrence_count = len(items)

        reasons = []
        if occurrence_count >= recurrence_threshold:
            reasons.append("recurrence")
        if avg_duration is not None and avg_duration >= stale_minutes_threshold:
            reasons.append("stale_duration")
        if not reasons:
            continue

        recommendation = (
            "Review for suppression or deadband tuning: recurs frequently"
            if "recurrence" in reasons
            else "Review for auto-clear or root-cause fix: stays active far longer than expected"
        )
        if len(reasons) == 2:
            recommendation = "High rationalization priority: recurs frequently and stays active long — candidate for redesign or removal"

        candidates.append({
            "asset_id": asset_id,
            "asset_name": items[0].asset_name,
            "alarm_name": alarm_name,
            "occurrence_count": occurrence_count,
            "avg_duration_minutes": avg_duration,
            "reasons": reasons,
            "recommendation": recommendation,
        })

    candidates.sort(key=lambda c: c["occurrence_count"], reverse=True)
    return {"candidates": candidates}
