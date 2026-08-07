from collections import defaultdict
from itertools import combinations

from app.models import Alarm

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def analyze_correlation(
    alarms: list[Alarm],
    asset_ids: list[str],
    lag_window_minutes: int,
    severity_threshold: str | None,
    min_support: int,
) -> dict:
    min_severity = SEVERITY_ORDER.get(severity_threshold, 0)
    filtered = [
        a for a in alarms
        if a.asset_id in asset_ids and SEVERITY_ORDER.get(a.severity, 0) >= min_severity
    ]
    by_asset: dict[str, list[Alarm]] = defaultdict(list)
    for a in filtered:
        by_asset[a.asset_id].append(a)

    lag = lag_window_minutes * 60
    pairs = []
    for asset_a, asset_b in combinations(sorted(by_asset.keys()), 2):
        matches = []
        for a in by_asset[asset_a]:
            for b in by_asset[asset_b]:
                if abs((a.start_time - b.start_time).total_seconds()) <= lag:
                    matches.append((a, b))
        if len(matches) >= min_support:
            pairs.append({
                "asset_id_a": asset_a,
                "asset_id_b": asset_b,
                "cooccurrence_count": len(matches),
                "support": len(matches),
                "sample_alarm_pair": {
                    "alarm_name_a": matches[0][0].alarm_name,
                    "alarm_name_b": matches[0][1].alarm_name,
                },
            })

    pairs.sort(key=lambda p: p["cooccurrence_count"], reverse=True)
    return {"correlation_method": "cooccurrence", "pairs": pairs}
