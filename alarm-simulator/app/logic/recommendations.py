from app.models import Alarm, Asset

RULES = [
    (("vibration", "bearing"), [
        "Inspect bearing condition and lubrication",
        "Check shaft alignment and coupling wear",
        "Review vibration trend for progressive degradation",
    ]),
    (("pressure",), [
        "Check for line blockage or closed downstream valve",
        "Verify pressure transmitter calibration",
        "Inspect pump/compressor discharge for cavitation",
    ]),
    (("temperature",), [
        "Check cooling water flow and heat exchanger fouling",
        "Verify lubrication oil level and condition",
        "Confirm temperature sensor calibration",
    ]),
    (("level",), [
        "Verify level transmitter reading against local gauge",
        "Check for blocked drain or inlet line",
        "Confirm control valve is responding to setpoint",
    ]),
    (("flow",), [
        "Check for strainer or filter blockage",
        "Verify valve position matches control signal",
        "Inspect for cavitation or air entrainment",
    ]),
]
DEFAULT_ACTIONS = [
    "Acknowledge and verify alarm against field conditions",
    "Review recent maintenance history for the asset",
    "Escalate to shift supervisor if condition persists",
]


def _actions_for(alarm_name: str) -> list[str]:
    name = alarm_name.lower()
    for keywords, actions in RULES:
        if any(k in name for k in keywords):
            return actions
    return DEFAULT_ACTIONS


def build_recommendations(
    alarm: Alarm,
    asset: Asset,
    related_alarms: list[Alarm],
    historical_same_name: list[Alarm],
    include_related: bool,
    include_asset_context: bool,
    include_historical_pattern: bool,
) -> dict:
    result = {
        "alarm_id": alarm.alarm_id,
        "alarm_name": alarm.alarm_name,
        "recommended_actions": _actions_for(alarm.alarm_name),
    }
    if include_related:
        result["related_alarms"] = [
            {"alarm_id": a.alarm_id, "alarm_name": a.alarm_name, "severity": a.severity, "status": a.status}
            for a in related_alarms if a.alarm_id != alarm.alarm_id
        ][:10]
    if include_asset_context:
        result["asset_context"] = {
            "asset_id": asset.asset_id,
            "asset_name": asset.asset_name,
            "asset_type": asset.asset_type,
            "criticality": asset.criticality,
            "unit": asset.unit,
            "site": asset.site,
        }
    if include_historical_pattern:
        result["historical_pattern"] = {
            "occurrence_count_90d": len(historical_same_name),
            "is_recurring": len(historical_same_name) >= 5,
        }
    return result
