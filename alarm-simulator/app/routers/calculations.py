import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.auth import TraceContext, get_trace_context, require_bearer_token
from app.db import get_session
from app.logic import calculations as calc_logic
from app.models import Calculation
from app.query import fetch_alarms
from app.schemas import CalculationExecuteRequest, CalculationGenerateRequest, TimeRange

router = APIRouter(dependencies=[Depends(require_bearer_token)])


@router.post("/calculation-code/generate")
def generate_calculation(body: CalculationGenerateRequest, session: Session = Depends(get_session)):
    if body.calculation_type not in calc_logic.SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported calculation_type '{body.calculation_type}', expected one of {sorted(calc_logic.SUPPORTED_TYPES)}",
        )

    calculation_id = f"calc-{uuid.uuid4().hex[:12]}"
    calc = Calculation(
        calculation_id=calculation_id,
        calculation_type=body.calculation_type,
        filters_json=json.dumps(body.filters),
        status="ready",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(calc)
    session.commit()

    return {
        "calculation_id": calculation_id,
        "calculation_type": body.calculation_type,
        "generated_code_summary": f"deterministic rule-based evaluator for {body.calculation_type}",
        "status": "ready",
    }


@router.post("/calculation-code/execute")
def execute_calculation(
    body: CalculationExecuteRequest,
    response: Response,
    session: Session = Depends(get_session),
    trace: TraceContext = Depends(get_trace_context),
):
    calc = session.get(Calculation, body.calculation_id)
    if not calc:
        raise HTTPException(status_code=404, detail=f"calculation not found: {body.calculation_id}")

    filters = json.loads(calc.filters_json)
    if body.filters:
        filters.update(body.filters)

    time_range = None
    if filters.get("start_time") and filters.get("end_time"):
        time_range = TimeRange(start_time=filters["start_time"], end_time=filters["end_time"])

    alarms = fetch_alarms(session, unit=filters.get("unit"), site=filters.get("site"), time_range=time_range)
    result = calc_logic.compute(calc.calculation_type, alarms)

    calc.result_json = json.dumps(result)
    calc.status = "completed"
    session.add(calc)
    session.commit()

    response.headers["x-trace-id"] = trace.trace_id
    return {"calculation_id": calc.calculation_id, "calculation_type": calc.calculation_type, "result": result, "status": "completed"}
