from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TimeRange(BaseModel):
    start_time: datetime
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time, info):
        start_time = info.data.get("start_time")
        if start_time and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class AlarmSummaryRequest(BaseModel):
    asset_ids: Optional[list[str]] = None
    unit: Optional[str] = None
    site: Optional[str] = None
    time_range: TimeRange
    severity: Optional[list[str]] = None
    alarm_types: Optional[list[str]] = None
    group_by: Optional[list[str]] = None
    kpis: Optional[list[str]] = None


class AlarmTrendsRequest(BaseModel):
    asset_ids: Optional[list[str]] = None
    unit: Optional[str] = None
    site: Optional[str] = None
    time_range: TimeRange
    bucket: str = "daily"  # hourly | daily
    metrics: Optional[list[str]] = None


class CorrelationRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1)
    time_range: TimeRange
    correlation_method: str = "cooccurrence"
    lag_window_minutes: int = 15
    severity_threshold: Optional[str] = None
    min_support: int = 1


class FloodAnalysisRequest(BaseModel):
    unit: Optional[str] = None
    site: Optional[str] = None
    time_range: TimeRange
    threshold_count: int = 10
    rolling_window_minutes: int = 10


class RationalizationRequest(BaseModel):
    asset_ids: Optional[list[str]] = None
    unit: Optional[str] = None
    site: Optional[str] = None
    time_range: TimeRange
    recurrence_threshold: int = 5
    stale_minutes_threshold: int = 180


class PriorityScoreRequest(BaseModel):
    alarm_id: str


class OperatorRecommendationsRequest(BaseModel):
    alarm_id: str
    include_related: bool = False
    include_asset_context: bool = False
    include_historical_pattern: bool = False


class CalculationGenerateRequest(BaseModel):
    calculation_type: str
    filters: dict = Field(default_factory=dict)


class CalculationExecuteRequest(BaseModel):
    calculation_id: str
    filters: Optional[dict] = None
