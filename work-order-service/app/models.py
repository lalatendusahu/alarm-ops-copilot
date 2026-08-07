from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class WorkOrder(SQLModel, table=True):
    work_order_id: str = Field(primary_key=True)
    asset_id: str = Field(index=True)
    asset_name: str
    title: str
    description: str = ""
    work_type: str  # corrective | preventive | inspection
    priority: str  # low | medium | high
    status: str = Field(index=True)  # open | in_progress | completed
    created_at: datetime
    completed_at: Optional[datetime] = None
    notes: str = ""
