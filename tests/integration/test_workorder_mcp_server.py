import json

import httpx
import pytest
import respx

from mcp.shared.memory import create_connected_server_and_client_session

BASE = "http://localhost:8010"


def _text(result):
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_tool_discovery_lists_all_four_tools(workorder_mcp_module):
    async with create_connected_server_and_client_session(workorder_mcp_module.mcp._mcp_server) as session:
        tools = await session.list_tools()
        names = {t.name for t in tools.tools}
    assert names == {"search_work_orders", "get_work_order_by_id", "get_maintenance_history", "create_work_order_draft"}


@pytest.mark.asyncio
async def test_maintenance_history_call(workorder_mcp_module):
    with respx.mock() as router:
        router.get(f"{BASE}/assets/AST-1001/maintenance-history").mock(
            return_value=httpx.Response(200, json={"asset_id": "AST-1001", "history": [{"work_order_id": "WO-1"}]})
        )
        async with create_connected_server_and_client_session(workorder_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("get_maintenance_history", {"asset_id": "AST-1001"})

    assert result.isError is False
    assert _text(result)["data"]["history"][0]["work_order_id"] == "WO-1"


@pytest.mark.asyncio
async def test_draft_without_confirm_calls_the_preview_endpoint_only(workorder_mcp_module):
    with respx.mock(assert_all_called=False) as router:
        draft_route = router.post(f"{BASE}/work-orders/draft").mock(
            return_value=httpx.Response(200, json={"draft_id": "DRAFT-1", "status": "draft"})
        )
        create_route = router.post(f"{BASE}/work-orders").mock(return_value=httpx.Response(200, json={}))

        async with create_connected_server_and_client_session(workorder_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("create_work_order_draft", {
                "asset_id": "AST-1001", "title": "Check bearing",
            })

    assert result.isError is False
    assert _text(result)["data"]["status"] == "draft"
    assert draft_route.call_count == 1
    assert create_route.call_count == 0


@pytest.mark.asyncio
async def test_draft_with_confirm_true_calls_the_create_endpoint(workorder_mcp_module):
    with respx.mock(assert_all_called=False) as router:
        draft_route = router.post(f"{BASE}/work-orders/draft").mock(return_value=httpx.Response(200, json={}))
        create_route = router.post(f"{BASE}/work-orders").mock(
            return_value=httpx.Response(200, json={"work_order_id": "WO-1", "status": "open"})
        )

        async with create_connected_server_and_client_session(workorder_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("create_work_order_draft", {
                "asset_id": "AST-1001", "title": "Check bearing", "confirm": True,
            })

    assert result.isError is False
    assert _text(result)["data"]["status"] == "open"
    assert draft_route.call_count == 0
    assert create_route.call_count == 1
    sent_body = json.loads(create_route.calls[0].request.content)
    assert sent_body["confirm"] is True


@pytest.mark.asyncio
async def test_upstream_validation_error_is_mapped(workorder_mcp_module):
    with respx.mock() as router:
        router.post(f"{BASE}/work-orders").mock(return_value=httpx.Response(400, text="confirm must be true"))
        async with create_connected_server_and_client_session(workorder_mcp_module.mcp._mcp_server) as session:
            result = await session.call_tool("create_work_order_draft", {
                "asset_id": "AST-1001", "title": "x", "confirm": True,
            })

    assert result.isError is True
    assert "invalid request" in result.content[0].text


@pytest.mark.asyncio
async def test_missing_required_argument_rejected(workorder_mcp_module):
    async with create_connected_server_and_client_session(workorder_mcp_module.mcp._mcp_server) as session:
        result = await session.call_tool("create_work_order_draft", {"asset_id": "AST-1001"})
    assert result.isError is True


@pytest.mark.asyncio
async def test_search_and_get_work_order_by_id(workorder_mcp_module):
    with respx.mock() as router:
        router.get(f"{BASE}/work-orders").mock(
            return_value=httpx.Response(200, json={"data": [{"work_order_id": "WO-1"}], "page": 1, "page_size": 20, "total": 1, "total_pages": 1})
        )
        router.get(f"{BASE}/work-orders/WO-1").mock(return_value=httpx.Response(200, json={"work_order_id": "WO-1", "status": "open"}))

        async with create_connected_server_and_client_session(workorder_mcp_module.mcp._mcp_server) as session:
            search_result = await session.call_tool("search_work_orders", {"asset_id": "AST-1001"})
            get_result = await session.call_tool("get_work_order_by_id", {"work_order_id": "WO-1"})

    assert search_result.isError is False
    assert _text(search_result)["data"]["data"][0]["work_order_id"] == "WO-1"
    assert get_result.isError is False
    assert _text(get_result)["data"]["status"] == "open"
