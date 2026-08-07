from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.auth import TraceContext, get_trace_context, require_bearer_token
from app.db import get_session
from app.logic.recommendations import build_recommendations
from app.models import Alarm, Asset
from app.query import fetch_alarms
from app.schemas import OperatorRecommendationsRequest

router = APIRouter(dependencies=[Depends(require_bearer_token)])


@router.post("/recommendations/operator-actions")
def operator_actions(
    body: OperatorRecommendationsRequest,
    response: Response,
    session: Session = Depends(get_session),
    trace: TraceContext = Depends(get_trace_context),
):
    alarm = session.get(Alarm, body.alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail=f"alarm not found: {body.alarm_id}")
    asset = session.get(Asset, alarm.asset_id)

    related = fetch_alarms(session, asset_ids=[alarm.asset_id], status="active") if body.include_related else []

    historical = []
    if body.include_historical_pattern:
        window_start = alarm.start_time - timedelta(days=90)
        all_asset_alarms = fetch_alarms(session, asset_ids=[alarm.asset_id])
        historical = [
            a for a in all_asset_alarms
            if a.alarm_name == alarm.alarm_name and a.start_time >= window_start
        ]

    response.headers["x-trace-id"] = trace.trace_id
    return build_recommendations(
        alarm, asset, related, historical,
        body.include_related, body.include_asset_context, body.include_historical_pattern,
    )
