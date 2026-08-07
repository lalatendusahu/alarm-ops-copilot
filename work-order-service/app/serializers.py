from app.models import WorkOrder


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def work_order_dict(wo: WorkOrder) -> dict:
    return {
        "work_order_id": wo.work_order_id,
        "asset_id": wo.asset_id,
        "asset_name": wo.asset_name,
        "title": wo.title,
        "description": wo.description,
        "work_type": wo.work_type,
        "priority": wo.priority,
        "status": wo.status,
        "created_at": _iso(wo.created_at),
        "completed_at": _iso(wo.completed_at),
        "notes": wo.notes,
    }
