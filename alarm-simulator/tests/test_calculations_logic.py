from datetime import datetime, timedelta

import pytest

from app.logic.calculations import compute
from app.models import Alarm


def _alarm(alarm_id, severity, ack_delay_min=None, duration_min=None):
    start = datetime(2026, 6, 1)
    ack_time = start + timedelta(minutes=ack_delay_min) if ack_delay_min is not None else None
    end_time = start + timedelta(minutes=duration_min) if duration_min is not None else None
    return Alarm(
        alarm_id=alarm_id, asset_id="AST-1", asset_name="AST-1", alarm_name="X", alarm_type="process",
        severity=severity, status="cleared" if end_time else "active", unit="Unit 1", site="NorthPlant",
        start_time=start, end_time=end_time, ack_time=ack_time,
    )


def test_critical_alarm_density():
    alarms = [_alarm("A1", "critical"), _alarm("A2", "critical"), _alarm("A3", "low")]
    result = compute("critical_alarm_density", alarms)
    assert result["critical_alarm_density"] == pytest.approx(2 / 3, rel=1e-3)
    assert result["critical_count"] == 2


def test_operator_response_efficiency_penalizes_slow_ack():
    fast = [_alarm(f"F{i}", "high", ack_delay_min=1) for i in range(3)]
    slow = [_alarm(f"S{i}", "high", ack_delay_min=40) for i in range(3)]
    fast_score = compute("operator_response_efficiency", fast)["operator_response_efficiency"]
    slow_score = compute("operator_response_efficiency", slow)["operator_response_efficiency"]
    assert fast_score > slow_score


def test_nuisance_alarm_score_counts_short_lived_alarms():
    alarms = [_alarm(f"A{i}", "low", duration_min=0.3) for i in range(4)] + [_alarm("B1", "low", duration_min=30)]
    result = compute("nuisance_alarm_score", alarms)
    assert result["short_lived_count"] == 4
    assert result["nuisance_alarm_score"] == 0.8


def test_unsupported_calculation_type_raises():
    with pytest.raises(ValueError):
        compute("not_a_real_kpi", [])


def test_empty_alarm_set_does_not_divide_by_zero():
    assert compute("critical_alarm_density", []) == {"critical_alarm_density": 0.0, "critical_count": 0, "sample_size": 0}
