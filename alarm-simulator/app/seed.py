import random
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models import Alarm, Asset

WINDOW_START = datetime(2026, 5, 1)
WINDOW_END = datetime(2026, 8, 1)
SEED = 42

ASSETS = [
    ("AST-1001", "Boiler Feed Pump 101", "Pump", "Unit 1", "NorthPlant", "high"),
    ("AST-1002", "Boiler Feed Pump 102", "Pump", "Unit 1", "NorthPlant", "high"),
    ("AST-1003", "Condensate Pump 103", "Pump", "Unit 1", "NorthPlant", "medium"),
    ("AST-1004", "Feedwater Control Valve 104", "Valve", "Unit 1", "NorthPlant", "medium"),
    ("AST-2001", "Cooling Water Pump 201", "Pump", "Unit 2", "NorthPlant", "medium"),
    ("AST-2002", "Cooling Water Pump 202", "Pump", "Unit 2", "NorthPlant", "medium"),
    ("AST-2003", "Air Compressor 203", "Compressor", "Unit 2", "NorthPlant", "medium"),
    ("AST-2004", "Chiller Compressor 204", "Compressor", "Unit 2", "NorthPlant", "low"),
    ("AST-3001", "Process Compressor 301", "Compressor", "Unit 3", "SouthPlant", "high"),
    ("AST-3002", "Process Compressor 302", "Compressor", "Unit 3", "SouthPlant", "high"),
    ("AST-3003", "Reactor Feed Pump 303", "Pump", "Unit 3", "SouthPlant", "high"),
    ("AST-3004", "Steam Turbine 304", "Turbine", "Unit 3", "SouthPlant", "high"),
    ("AST-4001", "Lube Oil Pump 401", "Pump", "Unit 4", "SouthPlant", "medium"),
    ("AST-4002", "Nuisance Bypass Valve 402", "Valve", "Unit 4", "SouthPlant", "low"),
    ("AST-4003", "Instrument Air Compressor 403", "Compressor", "Unit 4", "SouthPlant", "medium"),
    ("AST-5001", "Crude Booster Pump Motor 501", "Motor", "Unit 5", "EastRefinery", "medium"),
    ("AST-5002", "Cooling Fan Motor 502", "Motor", "Unit 5", "EastRefinery", "low"),
    ("AST-5003", "Charge Pump Motor 503", "Motor", "Unit 5", "EastRefinery", "medium"),
    ("AST-5004", "Crude Booster Pump 504", "Pump", "Unit 5", "EastRefinery", "high"),
    ("AST-5005", "Relief Valve 505", "Valve", "Unit 5", "EastRefinery", "medium"),
]

ALARM_LIBRARY = {
    "Pump": [
        ("High Bearing Vibration", "device", ["high", "high", "critical", "medium"]),
        ("High Discharge Pressure", "process", ["medium", "high", "high"]),
        ("Low Suction Pressure", "process", ["medium", "medium", "high"]),
        ("High Motor Temperature", "process", ["medium", "high"]),
        ("Seal Leak Detected", "safety", ["high", "critical"]),
    ],
    "Valve": [
        ("Valve Position Deviation", "device", ["low", "medium", "medium"]),
        ("Valve Fail to Open", "safety", ["high", "critical"]),
        ("Valve Fail to Close", "safety", ["high", "critical"]),
    ],
    "Compressor": [
        ("High Discharge Temperature", "process", ["medium", "high"]),
        ("Low Suction Pressure", "process", ["medium", "medium", "high"]),
        ("High Vibration", "device", ["high", "critical", "medium"]),
        ("Surge Warning", "safety", ["high", "critical"]),
    ],
    "Turbine": [
        ("High Bearing Vibration", "device", ["high", "critical"]),
        ("Overspeed Warning", "safety", ["critical"]),
        ("High Exhaust Temperature", "process", ["medium", "high"]),
    ],
    "Motor": [
        ("High Winding Temperature", "process", ["medium", "high"]),
        ("High Vibration", "device", ["medium", "high"]),
        ("Overcurrent Trip", "safety", ["high", "critical"]),
    ],
}


def _random_time(rng: random.Random) -> datetime:
    total_seconds = int((WINDOW_END - WINDOW_START).total_seconds())
    return WINDOW_START + timedelta(seconds=rng.randint(0, total_seconds))


def _finalize(rng: random.Random, start: datetime, site: str, forced_duration_minutes: float | None = None) -> tuple:
    is_recent = (WINDOW_END - start) < timedelta(days=2)
    ack_time = None
    end_time = None

    if not is_recent or rng.random() < 0.4:
        ack_delay = rng.randint(15, 2700 if site != "EastRefinery" else 3600)
        ack_time = start + timedelta(seconds=ack_delay)

        if forced_duration_minutes is not None:
            duration_minutes = forced_duration_minutes
        else:
            duration_minutes = rng.choice([
                rng.uniform(0.2, 1),   # chattering / short-lived
                rng.uniform(2, 30),    # typical
                rng.uniform(60, 360),  # stale / long-running
            ])
        end_time = start + timedelta(minutes=duration_minutes)

    return ack_time, end_time


def _build_alarm(rng: random.Random, counter: int, asset: tuple, name: str, alarm_type: str,
                  severity: str, start: datetime, forced_duration_minutes: float | None = None) -> Alarm:
    asset_id, asset_name, _, unit, site, _ = asset
    ack_time, end_time = _finalize(rng, start, site, forced_duration_minutes)
    status = "cleared" if end_time else ("acknowledged" if ack_time else "active")
    return Alarm(
        alarm_id=f"ALM-{counter:06d}",
        asset_id=asset_id,
        asset_name=asset_name,
        alarm_name=name,
        alarm_type=alarm_type,
        severity=severity,
        status=status,
        unit=unit,
        site=site,
        start_time=start,
        end_time=end_time,
        ack_time=ack_time,
        description=f"{name} on {asset_name}",
    )


def generate_alarms(rng: random.Random) -> list[Alarm]:
    alarms = []
    counter = 1

    for asset in ASSETS:
        asset_id, asset_name, asset_type, unit, site, criticality = asset
        pool = ALARM_LIBRARY[asset_type]
        baseline_count = rng.randint(8, 22)
        for _ in range(baseline_count):
            name, alarm_type, severities = rng.choice(pool)
            severity = rng.choice(severities)
            start = _random_time(rng)
            alarms.append(_build_alarm(rng, counter, asset, name, alarm_type, severity, start))
            counter += 1

    # Boiler Feed Pump 101: pronounced recurring high-severity vibration pattern, the
    # signal the mandatory 90-day investigation scenario is built around.
    bfp101 = next(a for a in ASSETS if a[0] == "AST-1001")
    span_days = (WINDOW_END - WINDOW_START).days
    for i in range(20):
        start = WINDOW_START + timedelta(days=(span_days / 20) * i, hours=rng.randint(0, 20))
        severity = rng.choice(["high", "high", "critical"])
        alarms.append(_build_alarm(rng, counter, bfp101, "High Bearing Vibration", "device", severity, start))
        counter += 1

    # Unit 2 flood burst: ~14 alarms inside an 8-minute window across the four Unit 2 assets.
    unit2_assets = [a for a in ASSETS if a[3] == "Unit 2"]
    burst_start = WINDOW_START + timedelta(days=40, hours=9, minutes=12)
    for _ in range(14):
        asset = rng.choice(unit2_assets)
        name, alarm_type, severities = rng.choice(ALARM_LIBRARY[asset[2]])
        start = burst_start + timedelta(seconds=rng.randint(0, 8 * 60))
        alarms.append(_build_alarm(
            rng, counter, asset, name, alarm_type, rng.choice(severities), start,
            forced_duration_minutes=rng.uniform(0.5, 2),
        ))
        counter += 1

    # Unit 4 nuisance chattering: a bypass valve that clears in under a minute, repeatedly.
    valve402 = next(a for a in ASSETS if a[0] == "AST-4002")
    for _ in range(30):
        start = _random_time(rng)
        alarms.append(_build_alarm(
            rng, counter, valve402, "Valve Position Deviation", "device", "low", start,
            forced_duration_minutes=rng.uniform(0.1, 0.9),
        ))
        counter += 1

    # Unit 1 stale alarms: reinforce the rationalization stale-duration path.
    valve104 = next(a for a in ASSETS if a[0] == "AST-1004")
    for _ in range(8):
        start = _random_time(rng)
        alarms.append(_build_alarm(
            rng, counter, valve104, "Valve Position Deviation", "device", "medium", start,
            forced_duration_minutes=rng.uniform(180, 400),
        ))
        counter += 1

    return alarms


def seed(session: Session, force: bool = False) -> int:
    existing = session.exec(select(Asset)).first()
    if existing and not force:
        return 0

    if force:
        for row in session.exec(select(Alarm)):
            session.delete(row)
        for row in session.exec(select(Asset)):
            session.delete(row)
        session.commit()

    rng = random.Random(SEED)

    for asset_id, asset_name, asset_type, unit, site, criticality in ASSETS:
        session.add(Asset(
            asset_id=asset_id,
            asset_name=asset_name,
            asset_type=asset_type,
            unit=unit,
            site=site,
            criticality=criticality,
            status="active",
            install_date="2019-03-01",
            description=f"{asset_type} in {unit}, {site}",
        ))

    alarms = generate_alarms(rng)
    for alarm in alarms:
        session.add(alarm)

    session.commit()
    return len(alarms)
