from fastapi import APIRouter, Depends

from app.auth import require_bearer_token

router = APIRouter(dependencies=[Depends(require_bearer_token)])

KPI_DEFINITIONS = [
    {"name": "alarm_count", "description": "Number of alarms in the matched group", "unit": "count"},
    {"name": "critical_count", "description": "Number of critical-severity alarms in the group", "unit": "count"},
    {"name": "recurring_rate", "description": "Alarms per day for the group over the requested window", "unit": "alarms/day"},
    {"name": "avg_ack_delay", "description": "Average time between alarm start and operator acknowledgement", "unit": "seconds"},
    {"name": "suppression_candidate_rate", "description": "Fraction of alarms in the group that clear within 60 seconds", "unit": "ratio"},
    {"name": "alarm_flood_index", "description": "Share of alarms occurring inside detected flood windows", "unit": "ratio"},
    {"name": "critical_alarm_density", "description": "Share of alarms in the filtered set that are critical severity", "unit": "ratio"},
    {"name": "operator_response_efficiency", "description": "Score (0-100) derived from average acknowledgement delay", "unit": "score"},
    {"name": "nuisance_alarm_score", "description": "Share of alarms that clear within 60 seconds of activation", "unit": "ratio"},
]


@router.get("/analytics/kpi-definitions")
def kpi_definitions():
    return {"kpis": KPI_DEFINITIONS}
