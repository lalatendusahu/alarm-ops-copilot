import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from app.auth import TraceContext, get_trace_context, require_bearer_token
from app.db import get_session
from app.models import WorkOrder
from app.schemas import WorkOrderCreateRequest, WorkOrderDraftRequest
from app.serializers import work_order_dict

health_router = APIRouter()


@health_router.get("/health")
def health():
    return {"status": "ok"}


router = APIRouter(dependencies=[Depends(require_bearer_token)])


@router.get("/work-orders")
def list_work_orders(
    asset_id: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
):
    stmt = select(WorkOrder)
    if asset_id:
        stmt = stmt.where(WorkOrder.asset_id == asset_id)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    rows = list(session.exec(stmt))
    rows.sort(key=lambda w: w.created_at, reverse=True)

    total = len(rows)
    total_pages = max(math.ceil(total / page_size), 1)
    start = (page - 1) * page_size
    page_items = rows[start:start + page_size]
    return {
        "data": [work_order_dict(w) for w in page_items],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/work-orders/{work_order_id}")
def get_work_order(work_order_id: str, session: Session = Depends(get_session)):
    wo = session.get(WorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"work order not found: {work_order_id}")
    return work_order_dict(wo)


@router.get("/assets/{asset_id}/maintenance-history")
def maintenance_history(asset_id: str, limit: int = 20, session: Session = Depends(get_session)):
    stmt = select(WorkOrder).where(WorkOrder.asset_id == asset_id, WorkOrder.status == "completed")
    rows = list(session.exec(stmt))
    rows.sort(key=lambda w: w.completed_at or w.created_at, reverse=True)
    return {"asset_id": asset_id, "history": [work_order_dict(w) for w in rows[:limit]]}


@router.post("/work-orders/draft")
def draft_work_order(
    body: WorkOrderDraftRequest,
    response: Response,
    trace: TraceContext = Depends(get_trace_context),
):
    response.headers["x-trace-id"] = trace.trace_id
    return {
        "draft_id": f"DRAFT-{uuid.uuid4().hex[:10]}",
        "status": "draft",
        "asset_id": body.asset_id,
        "title": body.title,
        "description": body.description,
        "work_type": body.work_type,
        "priority": body.priority,
        "note": "This is a preview only. Re-submit with confirm=true to persist it as a real work order.",
    }


@router.post("/work-orders")
def create_work_order(
    body: WorkOrderCreateRequest,
    response: Response,
    session: Session = Depends(get_session),
    trace: TraceContext = Depends(get_trace_context),
):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm must be true to create a work order; use /work-orders/draft to preview first")

    wo = WorkOrder(
        work_order_id=f"WO-{uuid.uuid4().hex[:10]}",
        asset_id=body.asset_id,
        asset_name=body.asset_id,
        title=body.title,
        description=body.description,
        work_type=body.work_type,
        priority=body.priority,
        status="open",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(wo)
    session.commit()

    response.headers["x-trace-id"] = trace.trace_id
    return work_order_dict(wo)
