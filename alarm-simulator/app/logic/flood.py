from datetime import timedelta

from app.models import Alarm


def analyze_flood(alarms: list[Alarm], threshold_count: int, rolling_window_minutes: int) -> dict:
    window = timedelta(minutes=rolling_window_minutes)
    times = sorted(a.start_time for a in alarms)
    n = len(times)

    windows: list[tuple] = []
    in_flood = False
    flood_start = None
    flood_end = None
    i = 0
    while i < n:
        j = i
        while j < n and times[j] <= times[i] + window:
            j += 1
        count = j - i
        if count >= threshold_count:
            if not in_flood:
                flood_start = times[i]
                in_flood = True
            flood_end = times[j - 1]
        elif in_flood:
            windows.append((flood_start, flood_end))
            in_flood = False
        i += 1
    if in_flood:
        windows.append((flood_start, flood_end))

    flood_windows = []
    for start, end in windows:
        count = sum(1 for t in times if start <= t <= end)
        span_minutes = max((end - start).total_seconds() / 60, 1)
        flood_windows.append({
            "start": start.isoformat() + "Z",
            "end": end.isoformat() + "Z",
            "alarm_count": count,
            "peak_rate_per_min": round(count / span_minutes, 2),
        })

    return {"threshold_count": threshold_count, "rolling_window_minutes": rolling_window_minutes, "flood_windows": flood_windows}
