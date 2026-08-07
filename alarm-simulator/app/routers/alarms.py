import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from app.auth import TraceContext, get_trace_context, require_bearer_token
from app.db import get_session
from app.logging_utils import get_logger, log_request
from app.logic import correlation as correlation_logic
from app.logic import flood as flood_logic
from app.logic import priority as priority_logic
from app.logic import rationalization as rationalization_logic
from app.logic import summary as summary_logic
from app.logic import trends as trends_logic
from app.models import Alarm, Asset
from app.query import fetch_alarms
from app.schemas import (
    AlarmSummaryRequest,
    AlarmTrendsRequest,
    CorrelationRequest,
    FloodAnalysisRequest,
    PriorityScoreRequest,
    RationalizationRequest,
)
from app.serializers import alarm_dict

router = APIRouter(dependencies=[Depends(require_bearer_token)])
logger = get_logger("alarm_simulator.alarms")

SORTABLE_FIELDS = {"start_time", "severity", "asset_id"}


@router.get("/alarms")
def list_alarms(
    response: Response,
    asset_id: str | None = None,
    unit: str | None = None,
    site: str | None = None,
    status: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = "start_time",
    sort_order: str = "desc",
    session: Session = Depends(get_session),
    trace: TraceContext = Depends(get_trace_context),
):
    if sort_by not in SORTABLE_FIELDS:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of {sorted(SORTABLE_FIELDS)}")

    stmt = select(Alarm)
    if asset_id:
        stmt = stmt.where(Alarm.asset_id == asset_id)
    if unit:
        stmt = stmt.where(Alarm.unit == unit)
    if site:
        stmt = stmt.where(Alarm.site == site)
    if status:
        stmt = stmt.where(Alarm.status == status)
    if start_time:
        stmt = stmt.where(Alarm.start_time >= start_time)
    if end_time:
        stmt = stmt.where(Alarm.start_time <= end_time)

    all_matches = list(session.exec(stmt))
    reverse = sort_order == "desc"
    all_matches.sort(key=lambda a: getattr(a, sort_by), reverse=reverse)

    total = len(all_matches)
    total_pages = max(math.ceil(total / page_size), 1)
    start = (page - 1) * page_size
    page_items = all_matches[start:start + page_size]

    response.headers["x-trace-id"] = trace.trace_id
    return {
        "data": [alarm_dict(a) for a in page_items],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/alarms/{alarm_id}")
def get_alarm(alarm_id: str, session: Session = Depends(get_session)):
    alarm = session.get(Alarm, alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail=f"alarm not found: {alarm_id}")
    return alarm_dict(alarm)


@router.post("/alarms/summary")
def alarm_summary(
    body: AlarmSummaryRequest,
    response: Response,
    session: Session = Depends(get_session),
    trace: TraceContext = Depends(get_trace_context),
):
    alarms = fetch_alarms(
        session,
        asset_ids=body.asset_ids,
        unit=body.unit,
        site=body.site,
        time_range=body.time_range,
        severity=body.severity,
        alarm_types=body.alarm_types,
    )
    response.headers["x-trace-id"] = trace.trace_id
    log_request(logger, route="/alarms/summary", trace_id=trace.trace_id, client_id=trace.client_id, status=200, duration_ms=0)
    return summary_logic.summarize(alarms, body.time_range, body.group_by, body.kpis)


@router.post("/alarms/trends")
def alarm_trends(body: AlarmTrendsRequest, session: Session = Depends(get_session)):
    alarms = fetch_alarms(
        session, asset_ids=body.asset_ids, unit=body.unit, site=body.site, time_range=body.time_range
    )
    return trends_logic.compute_trends(alarms, body.time_range, body.bucket, body.metrics)


@router.post("/alarms/correlation")
def alarm_correlation(
    body: CorrelationRequest,
    response: Response,
    session: Session = Depends(get_session),
    trace: TraceContext = Depends(get_trace_context),
):
    alarms = fetch_alarms(session, asset_ids=body.asset_ids, time_range=body.time_range)
    response.headers["x-trace-id"] = trace.trace_id
    return correlation_logic.analyze_correlation(
        alarms, body.asset_ids, body.lag_window_minutes, body.severity_threshold, body.min_support
    )


@router.post("/alarms/flood-analysis")
def alarm_flood_analysis(body: FloodAnalysisRequest, session: Session = Depends(get_session)):
    alarms = fetch_alarms(session, unit=body.unit, site=body.site, time_range=body.time_range)
    return flood_logic.analyze_flood(alarms, body.threshold_count, body.rolling_window_minutes)


@router.post("/alarms/rationalization-candidates")
def rationalization_candidates(body: RationalizationRequest, session: Session = Depends(get_session)):
    alarms = fetch_alarms(
        session, asset_ids=body.asset_ids, unit=body.unit, site=body.site, time_range=body.time_range
    )
    return rationalization_logic.find_candidates(alarms, body.recurrence_threshold, body.stale_minutes_threshold)


@router.post("/alarms/priority-score")
def priority_score(body: PriorityScoreRequest, session: Session = Depends(get_session)):
    alarm = session.get(Alarm, body.alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail=f"alarm not found: {body.alarm_id}")
    asset = session.get(Asset, alarm.asset_id)
    recent = fetch_alarms(session, asset_ids=[alarm.asset_id])
    return priority_logic.score_alarm(alarm, asset, recent)
