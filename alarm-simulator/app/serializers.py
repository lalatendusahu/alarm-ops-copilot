from app.models import Alarm, Asset


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def asset_dict(asset: Asset) -> dict:
    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "asset_type": asset.asset_type,
        "unit": asset.unit,
        "site": asset.site,
        "criticality": asset.criticality,
        "status": asset.status,
        "install_date": asset.install_date,
        "description": asset.description,
    }


def alarm_dict(alarm: Alarm) -> dict:
    return {
        "alarm_id": alarm.alarm_id,
        "asset_id": alarm.asset_id,
        "asset_name": alarm.asset_name,
        "alarm_name": alarm.alarm_name,
        "alarm_type": alarm.alarm_type,
        "severity": alarm.severity,
        "status": alarm.status,
        "unit": alarm.unit,
        "site": alarm.site,
        "start_time": _iso(alarm.start_time),
        "end_time": _iso(alarm.end_time),
        "ack_time": _iso(alarm.ack_time),
        "description": alarm.description,
    }
