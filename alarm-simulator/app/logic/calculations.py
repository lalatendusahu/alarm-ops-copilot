from app.logic.flood import analyze_flood
from app.models import Alarm

SUPPORTED_TYPES = {
    "alarm_flood_index",
    "critical_alarm_density",
    "operator_response_efficiency",
    "nuisance_alarm_score",
}


def compute(calculation_type: str, alarms: list[Alarm]) -> dict:
    if calculation_type == "alarm_flood_index":
        flood = analyze_flood(alarms, threshold_count=10, rolling_window_minutes=10)
        windows = flood["flood_windows"]
        index = round(sum(w["alarm_count"] for w in windows) / max(len(alarms), 1), 3)
        return {"alarm_flood_index": index, "flood_window_count": len(windows), "sample_size": len(alarms)}

    if calculation_type == "critical_alarm_density":
        critical = sum(1 for a in alarms if a.severity == "critical")
        density = round(critical / len(alarms), 3) if alarms else 0.0
        return {"critical_alarm_density": density, "critical_count": critical, "sample_size": len(alarms)}

    if calculation_type == "operator_response_efficiency":
        delays = [(a.ack_time - a.start_time).total_seconds() / 60 for a in alarms if a.ack_time]
        avg_delay = round(sum(delays) / len(delays), 2) if delays else 0.0
        efficiency = round(max(0.0, 100 - avg_delay * 2), 1)
        return {"operator_response_efficiency": efficiency, "avg_ack_delay_minutes": avg_delay, "sample_size": len(delays)}

    if calculation_type == "nuisance_alarm_score":
        short_lived = [
            a for a in alarms if a.end_time and (a.end_time - a.start_time).total_seconds() <= 60
        ]
        score = round(len(short_lived) / len(alarms), 3) if alarms else 0.0
        return {"nuisance_alarm_score": score, "short_lived_count": len(short_lived), "sample_size": len(alarms)}

    raise ValueError(f"unsupported calculation_type: {calculation_type}")
