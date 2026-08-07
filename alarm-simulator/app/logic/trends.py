from datetime import timedelta

from app.models import Alarm
from app.schemas import TimeRange


def compute_trends(alarms: list[Alarm], time_range: TimeRange, bucket: str, metrics: list[str] | None) -> dict:
    metrics = metrics or ["alarm_count"]
    step = timedelta(hours=1) if bucket == "hourly" else timedelta(days=1)

    bucket_starts = []
    t = time_range.start_time
    while t < time_range.end_time:
        bucket_starts.append(t)
        t += step
    buckets: dict = {b: [] for b in bucket_starts}

    for alarm in alarms:
        if alarm.start_time < time_range.start_time or alarm.start_time >= time_range.end_time:
            continue
        idx = int((alarm.start_time - time_range.start_time) / step)
        idx = min(idx, len(bucket_starts) - 1)
        buckets[bucket_starts[idx]].append(alarm)

    out = []
    for start in bucket_starts:
        items = buckets[start]
        entry = {"bucket_start": start.isoformat() + "Z", "alarm_count": len(items)}
        if "avg_ack_delay" in metrics:
            delays = [(a.ack_time - a.start_time).total_seconds() for a in items if a.ack_time]
            entry["avg_ack_delay"] = round(sum(delays) / len(delays), 1) if delays else None
        out.append(entry)

    return {"bucket": bucket, "buckets": out}
