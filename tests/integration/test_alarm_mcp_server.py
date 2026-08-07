import json

import httpx
import pytest
import respx

from mcp.shared.memory import create_connected_server_and_client_session

BASE = "http://localhost:8000"


def _text(result):
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_tool_discovery_lists_expected_tools(alarm_mcp_module):
    async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
        tools = await session.list_tools()
        names = {t.name for t in tools.tools}
        for expected in ["search_assets", "get_alarms", "get_alarm_summary", "analyze_alarm_correlation",
                          "generate_kpi_calculation", "execute_kpi_calculation"]:
            assert expected in names


@pytest.mark.asyncio
async def test_tool_schema_marks_required_and_optional_fields(alarm_mcp_module):
    async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
        tools = await session.list_tools()
        schema = next(t.inputSchema for t in tools.tools if t.name == "search_assets")
        assert schema["required"] == ["query"]
        assert "limit" in schema["properties"]


@pytest.mark.asyncio
async def test_successful_tool_call_returns_data_and_trace_id(alarm_mcp_module):
    with respx.mock() as router:
        router.get(f"{BASE}/assets/search").mock(
            return_value=httpx.Response(200, json={"results": [{"asset_id": "AST-1001"}], "count": 1})
        )
        async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("search_assets", {"query": "Boiler Feed Pump 101"})

    assert result.isError is False
    body = _text(result)
    assert body["trace_id"]
    assert body["data"]["results"][0]["asset_id"] == "AST-1001"


@pytest.mark.asyncio
async def test_trace_id_is_propagated_to_upstream_request(alarm_mcp_module):
    with respx.mock() as router:
        route = router.get(f"{BASE}/assets/search").mock(
            return_value=httpx.Response(200, json={"results": [], "count": 0})
        )
        async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
            await session.call_tool("search_assets", {"query": "pump", "trace_id": "trace-fixed-001"})

    assert route.calls[0].request.headers["trace_id"] == "trace-fixed-001"


@pytest.mark.asyncio
async def test_not_found_error_is_mapped_to_a_readable_tool_error(alarm_mcp_module):
    with respx.mock() as router:
        router.get(f"{BASE}/assets/unknown-id/metadata").mock(return_value=httpx.Response(404, text="asset not found"))
        async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("get_asset_metadata", {"asset_id": "unknown-id"})

    assert result.isError is True
    assert "not found" in result.content[0].text


@pytest.mark.asyncio
async def test_upstream_5xx_is_retried_then_mapped_to_unavailable_error(alarm_mcp_module):
    with respx.mock() as router:
        route = router.get(f"{BASE}/assets/search").mock(return_value=httpx.Response(503, text="db down"))
        async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("search_assets", {"query": "pump"})

    assert result.isError is True
    assert "unavailable" in result.content[0].text
    assert route.call_count == 3  # BaseConnector retries up to max_retries


@pytest.mark.asyncio
async def test_auth_error_is_mapped_without_leaking_the_token(alarm_mcp_module):
    with respx.mock() as router:
        router.get(f"{BASE}/assets/search").mock(return_value=httpx.Response(401, text="invalid token"))
        async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("search_assets", {"query": "pump"})

    assert result.isError is True
    assert "authentication" in result.content[0].text
    assert alarm_mcp_module.TOKEN not in result.content[0].text


@pytest.mark.asyncio
async def test_missing_required_argument_is_rejected_by_schema_validation(alarm_mcp_module):
    async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
        result = await session.call_tool("search_assets", {})
    assert result.isError is True


@pytest.mark.asyncio
async def test_calling_an_unknown_tool_name_fails_cleanly(alarm_mcp_module):
    async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
        result = await session.call_tool("does_not_exist", {})
    assert result.isError is True


@pytest.mark.asyncio
async def test_kpi_generate_then_execute_chain_passes_calculation_id_through(alarm_mcp_module):
    with respx.mock() as router:
        router.post(f"{BASE}/calculation-code/generate").mock(
            return_value=httpx.Response(200, json={"calculation_id": "calc-abc", "status": "ready"})
        )
        exec_route = router.post(f"{BASE}/calculation-code/execute").mock(
            return_value=httpx.Response(200, json={"calculation_id": "calc-abc", "result": {}, "status": "completed"})
        )
        async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
            generated = await session.call_tool("generate_kpi_calculation", {"calculation_type": "critical_alarm_density"})
            calculation_id = _text(generated)["data"]["calculation_id"]
            await session.call_tool("execute_kpi_calculation", {"calculation_id": calculation_id})

    sent_body = json.loads(exec_route.calls[0].request.content)
    assert sent_body["calculation_id"] == "calc-abc"


@pytest.mark.asyncio
async def test_remaining_alarm_tools_dispatch_and_unwrap_correctly(alarm_mcp_module):
    with respx.mock() as router:
        router.get(f"{BASE}/alarms").mock(return_value=httpx.Response(200, json={"data": [], "page": 1, "page_size": 50, "total": 0, "total_pages": 1}))
        router.get(f"{BASE}/alarms/ALM-1").mock(return_value=httpx.Response(200, json={"alarm_id": "ALM-1"}))
        router.post(f"{BASE}/alarms/correlation").mock(return_value=httpx.Response(200, json={"pairs": []}))
        router.post(f"{BASE}/alarms/flood-analysis").mock(return_value=httpx.Response(200, json={"flood_windows": []}))
        router.post(f"{BASE}/alarms/rationalization-candidates").mock(return_value=httpx.Response(200, json={"candidates": []}))
        router.post(f"{BASE}/alarms/priority-score").mock(return_value=httpx.Response(200, json={"priority_score": 42}))
        router.post(f"{BASE}/recommendations/operator-actions").mock(return_value=httpx.Response(200, json={"recommended_actions": []}))
        router.get(f"{BASE}/analytics/kpi-definitions").mock(return_value=httpx.Response(200, json={"kpis": []}))

        async with create_connected_server_and_client_session(alarm_mcp_module.mcp._mcp_server) as session:
            calls = {
                "get_alarms": {},
                "get_alarm_by_id": {"alarm_id": "ALM-1"},
                "analyze_alarm_correlation": {"asset_ids": ["AST-1"], "start_time": "2026-01-01T00:00:00Z", "end_time": "2026-01-02T00:00:00Z"},
                "analyze_alarm_flood": {"start_time": "2026-01-01T00:00:00Z", "end_time": "2026-01-02T00:00:00Z"},
                "get_rationalization_candidates": {"start_time": "2026-01-01T00:00:00Z", "end_time": "2026-01-02T00:00:00Z"},
                "get_alarm_priority_score": {"alarm_id": "ALM-1"},
                "get_operator_recommendations": {"alarm_id": "ALM-1"},
                "list_kpi_definitions": {},
            }
            for name, args in calls.items():
                result = await session.call_tool(name, args)
                assert result.isError is False, f"{name} failed: {result.content}"
                assert "data" in _text(result)

