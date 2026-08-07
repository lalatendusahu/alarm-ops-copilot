from sqlmodel import Session, select

from app.models import Alarm
from app.schemas import TimeRange


def fetch_alarms(
    session: Session,
    *,
    asset_ids: list[str] | None = None,
    unit: str | None = None,
    site: str | None = None,
    time_range: TimeRange | None = None,
    severity: list[str] | None = None,
    alarm_types: list[str] | None = None,
    status: str | None = None,
) -> list[Alarm]:
    stmt = select(Alarm)
    if asset_ids:
        stmt = stmt.where(Alarm.asset_id.in_(asset_ids))
    if unit:
        stmt = stmt.where(Alarm.unit == unit)
    if site:
        stmt = stmt.where(Alarm.site == site)
    if time_range:
        stmt = stmt.where(Alarm.start_time >= time_range.start_time, Alarm.start_time <= time_range.end_time)
    if severity:
        stmt = stmt.where(Alarm.severity.in_(severity))
    if alarm_types:
        stmt = stmt.where(Alarm.alarm_type.in_(alarm_types))
    if status:
        stmt = stmt.where(Alarm.status == status)
    return list(session.exec(stmt))
