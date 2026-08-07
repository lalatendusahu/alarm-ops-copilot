from pydantic import BaseModel


class WorkOrderDraftRequest(BaseModel):
    asset_id: str
    title: str
    description: str = ""
    work_type: str = "corrective"
    priority: str = "medium"


class WorkOrderCreateRequest(WorkOrderDraftRequest):
    confirm: bool = False
