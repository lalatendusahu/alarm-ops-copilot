"""Work Order MCP server -- the second MCP domain alongside Alarm Management.

Run standalone from the repo root with:

    python mcp-servers/work_orders/server.py
"""
import os
import sys
from pathlib import Path
from typing import Annotated

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from pydantic import Field  # noqa: E402

from connectors.errors import AuthError, NotFoundError, UpstreamUnavailableError, ValidationError  # noqa: E402
from connectors.workorder_client import WorkOrderApiClient  # noqa: E402

HOST = os.getenv("MCP_WORKORDERS_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_WORKORDERS_PORT", "9002"))
BASE_URL = os.getenv("WORK_ORDER_API_BASE_URL", "http://localhost:8010")
TOKEN = os.getenv("WORK_ORDER_API_TOKEN", "demo-token")

mcp = FastMCP("work-orders", host=HOST, port=PORT)
client = WorkOrderApiClient(BASE_URL, TOKEN)

TraceId = Annotated[str | None, Field(description="Optional trace id to correlate this call with the rest of a multi-step request; generated if omitted")]


async def _run(label: str, coro) -> dict:
    try:
        data, trace_id = await coro
    except NotFoundError as exc:
        raise RuntimeError(f"{label}: not found - {exc}") from exc
    except ValidationError as exc:
        raise RuntimeError(f"{label}: invalid request - {exc}") from exc
    except AuthError as exc:
        raise RuntimeError(f"{label}: authentication to the work order API failed") from exc
    except UpstreamUnavailableError as exc:
        raise RuntimeError(f"{label}: work order API unavailable after retries - {exc}") from exc
    return {"trace_id": trace_id, "data": data}


@mcp.tool()
async def search_work_orders(
    asset_id: Annotated[str | None, Field(description="Filter to a single asset id")] = None,
    status: Annotated[str | None, Field(description="Filter by status: open | in_progress | completed")] = None,
    page: Annotated[int, Field(description="1-based page number", ge=1)] = 1,
    page_size: Annotated[int, Field(description="Results per page", ge=1, le=200)] = 20,
    trace_id: TraceId = None,
) -> dict:
    """Search work orders by asset and/or status."""
    return await _run("search_work_orders", client.search_work_orders(asset_id, status, page, page_size, trace_id=trace_id))


@mcp.tool()
async def get_work_order_by_id(
    work_order_id: Annotated[str, Field(description="Work order id")],
    trace_id: TraceId = None,
) -> dict:
    """Fetch a single work order's full detail record."""
    return await _run("get_work_order_by_id", client.get_work_order(work_order_id, trace_id=trace_id))


@mcp.tool()
async def get_maintenance_history(
    asset_id: Annotated[str, Field(description="Asset id to fetch completed maintenance history for")],
    limit: Annotated[int, Field(description="Maximum number of past work orders to return", ge=1, le=100)] = 20,
    trace_id: TraceId = None,
) -> dict:
    """Get an asset's completed work order history -- use this to check for prior repairs related to a recurring alarm."""
    return await _run("get_maintenance_history", client.get_maintenance_history(asset_id, limit, trace_id=trace_id))


@mcp.tool()
async def create_work_order_draft(
    asset_id: Annotated[str, Field(description="Asset the work order is for")],
    title: Annotated[str, Field(description="Short work order title")],
    description: Annotated[str, Field(description="Longer description of the issue and requested work")] = "",
    work_type: Annotated[str, Field(description="corrective | preventive | inspection")] = "corrective",
    priority: Annotated[str, Field(description="low | medium | high")] = "medium",
    confirm: Annotated[bool, Field(description="Must be explicitly set true to actually persist the work order; false (default) returns a preview only")] = False,
    trace_id: TraceId = None,
) -> dict:
    """Draft a new work order. By default this only returns a preview and writes nothing --
    a human must approve before calling this again with confirm=true, which is required for
    any write operation against the work order system."""
    body = {"asset_id": asset_id, "title": title, "description": description, "work_type": work_type, "priority": priority}
    if not confirm:
        return await _run("create_work_order_draft", client.draft_work_order(body, trace_id=trace_id))
    body["confirm"] = True
    return await _run("create_work_order_draft", client.create_work_order(body, trace_id=trace_id))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
