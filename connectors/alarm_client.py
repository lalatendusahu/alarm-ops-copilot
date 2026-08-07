from connectors.base import BaseConnector


class AlarmApiClient(BaseConnector):
    async def search_assets(self, query: str, unit: str | None = None, site: str | None = None, limit: int = 10, **trace):
        params = {"query": query, "limit": limit}
        if unit:
            params["unit"] = unit
        if site:
            params["site"] = site
        return await self.get("/assets/search", params=params, **trace)

    async def get_asset_metadata(self, asset_id: str, **trace):
        return await self.get(f"/assets/{asset_id}/metadata", **trace)

    async def get_alarms(
        self,
        *,
        asset_id: str | None = None,
        unit: str | None = None,
        site: str | None = None,
        status: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "start_time",
        sort_order: str = "desc",
        **trace,
    ):
        params = {"page": page, "page_size": page_size, "sort_by": sort_by, "sort_order": sort_order}
        for key, value in (
            ("asset_id", asset_id), ("unit", unit), ("site", site), ("status", status),
            ("start_time", start_time), ("end_time", end_time),
        ):
            if value:
                params[key] = value
        return await self.get("/alarms", params=params, **trace)

    async def get_alarm_by_id(self, alarm_id: str, **trace):
        return await self.get(f"/alarms/{alarm_id}", **trace)

    async def get_alarm_summary(self, body: dict, **trace):
        return await self.post("/alarms/summary", json_body=body, **trace)

    async def get_alarm_trends(self, body: dict, **trace):
        return await self.post("/alarms/trends", json_body=body, **trace)

    async def analyze_correlation(self, body: dict, **trace):
        return await self.post("/alarms/correlation", json_body=body, **trace)

    async def analyze_flood(self, body: dict, **trace):
        return await self.post("/alarms/flood-analysis", json_body=body, **trace)

    async def get_rationalization_candidates(self, body: dict, **trace):
        return await self.post("/alarms/rationalization-candidates", json_body=body, **trace)

    async def get_priority_score(self, body: dict, **trace):
        return await self.post("/alarms/priority-score", json_body=body, **trace)

    async def get_operator_recommendations(self, body: dict, **trace):
        return await self.post("/recommendations/operator-actions", json_body=body, **trace)

    async def generate_kpi_calculation(self, body: dict, **trace):
        return await self.post("/calculation-code/generate", json_body=body, **trace)

    async def execute_kpi_calculation(self, body: dict, **trace):
        return await self.post("/calculation-code/execute", json_body=body, **trace)

    async def list_kpi_definitions(self, **trace):
        return await self.get("/analytics/kpi-definitions", **trace)
