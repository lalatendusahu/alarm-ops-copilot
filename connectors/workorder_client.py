from connectors.base import BaseConnector


class WorkOrderApiClient(BaseConnector):
    async def search_work_orders(self, asset_id: str | None = None, status: str | None = None, page: int = 1, page_size: int = 20, **trace):
        params = {"page": page, "page_size": page_size}
        if asset_id:
            params["asset_id"] = asset_id
        if status:
            params["status"] = status
        return await self.get("/work-orders", params=params, **trace)

    async def get_work_order(self, work_order_id: str, **trace):
        return await self.get(f"/work-orders/{work_order_id}", **trace)

    async def get_maintenance_history(self, asset_id: str, limit: int = 20, **trace):
        return await self.get(f"/assets/{asset_id}/maintenance-history", params={"limit": limit}, **trace)

    async def draft_work_order(self, body: dict, **trace):
        return await self.post("/work-orders/draft", json_body=body, **trace)

    async def create_work_order(self, body: dict, **trace):
        return await self.post("/work-orders", json_body=body, **trace)
