from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Asset(SQLModel, table=True):
    asset_id: str = Field(primary_key=True)
    asset_name: str = Field(index=True)
    asset_type: str
    unit: str = Field(index=True)
    site: str = Field(index=True)
    criticality: str  # low | medium | high
    status: str  # active | inactive
    install_date: str
    description: str = ""


class Alarm(SQLModel, table=True):
    alarm_id: str = Field(primary_key=True)
    asset_id: str = Field(index=True, foreign_key="asset.asset_id")
    asset_name: str = Field(index=True)
    alarm_name: str = Field(index=True)
    alarm_type: str  # process | device | safety
    severity: str = Field(index=True)  # low | medium | high | critical
    status: str = Field(index=True)  # active | acknowledged | cleared
    unit: str = Field(index=True)
    site: str = Field(index=True)
    start_time: datetime = Field(index=True)
    end_time: Optional[datetime] = None
    ack_time: Optional[datetime] = None
    description: str = ""


class Calculation(SQLModel, table=True):
    calculation_id: str = Field(primary_key=True)
    calculation_type: str
    filters_json: str
    status: str  # ready | completed
    result_json: Optional[str] = None
    created_at: datetime
