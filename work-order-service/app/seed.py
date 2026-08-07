import uuid
from datetime import datetime

from sqlmodel import Session, select

from app.models import WorkOrder

# (asset_id, asset_name, title, work_type, priority, status, created, completed, notes)
RECORDS = [
    ("AST-1001", "Boiler Feed Pump 101", "Replace outboard bearing", "corrective", "high", "completed",
     datetime(2026, 5, 12), datetime(2026, 5, 14),
     "Bearing showed heavy wear consistent with recurring high vibration alarms. Replaced and re-aligned."),
    ("AST-1001", "Boiler Feed Pump 101", "Vibration analysis follow-up", "inspection", "medium", "completed",
     datetime(2026, 6, 2), datetime(2026, 6, 2),
     "Post-repair vibration readings within acceptable range at time of inspection."),
    ("AST-1001", "Boiler Feed Pump 101", "Lubrication schedule review", "preventive", "medium", "completed",
     datetime(2026, 6, 20), datetime(2026, 6, 21),
     "Adjusted lubrication interval; vibration alarms continued to recur afterward."),
    ("AST-1002", "Boiler Feed Pump 102", "Routine seal inspection", "preventive", "low", "completed",
     datetime(2026, 5, 20), datetime(2026, 5, 20), "No abnormalities found."),
    ("AST-3001", "Process Compressor 301", "Surge valve calibration", "corrective", "high", "completed",
     datetime(2026, 5, 28), datetime(2026, 5, 29), "Recalibrated anti-surge valve after repeated surge warnings."),
    ("AST-3004", "Steam Turbine 304", "Bearing temperature investigation", "corrective", "high", "in_progress",
     datetime(2026, 7, 15), None, "Awaiting parts for bearing replacement."),
    ("AST-4002", "Nuisance Bypass Valve 402", "Deadband tuning", "corrective", "low", "open",
     datetime(2026, 7, 20), None, "Chattering position deviation alarms reported by operations."),
    ("AST-5004", "Crude Booster Pump 504", "Annual overhaul", "preventive", "medium", "completed",
     datetime(2026, 5, 5), datetime(2026, 5, 10), "Standard overhaul completed on schedule."),
]


def seed(session: Session, force: bool = False) -> int:
    existing = session.exec(select(WorkOrder)).first()
    if existing and not force:
        return 0

    if force:
        for row in session.exec(select(WorkOrder)):
            session.delete(row)
        session.commit()

    for asset_id, asset_name, title, work_type, priority, status, created, completed, notes in RECORDS:
        session.add(WorkOrder(
            work_order_id=f"WO-{uuid.uuid4().hex[:10]}",
            asset_id=asset_id,
            asset_name=asset_name,
            title=title,
            description=title,
            work_type=work_type,
            priority=priority,
            status=status,
            created_at=created,
            completed_at=completed,
            notes=notes,
        ))
    session.commit()
    return len(RECORDS)
