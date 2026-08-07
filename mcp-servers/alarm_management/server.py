"""Alarm Management MCP server.

Wraps the Alarm Management API simulator as MCP tools. Run standalone from the repo
root with:

    python mcp-servers/alarm_management/server.py

Independent of the copilot -- can be probed with `mcp dev` or any MCP client pointed
at the streamable-http endpoint below.
"""
import os
import sys
from pathlib import Path
from typing import Annotated

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from pydantic import Field  # noqa: E402

from connectors.alarm_client import AlarmApiClient  # noqa: E402
from connectors.errors import AuthError, NotFoundError, UpstreamUnavailableError, ValidationError  # noqa: E402

HOST = os.getenv("MCP_ALARM_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_ALARM_PORT", "9001"))
BASE_URL = os.getenv("ALARM_API_BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("ALARM_API_TOKEN", "demo-token")

mcp = FastMCP("alarm-management", host=HOST, port=PORT)
client = AlarmApiClient(BASE_URL, TOKEN)


async def _run(label: str, coro) -> dict:
    try:
        data, trace_id = await coro
    except NotFoundError as exc:
        raise RuntimeError(f"{label}: not found - {exc}") from exc
    except ValidationError as exc:
        raise RuntimeError(f"{label}: invalid request - {exc}") from exc
    except AuthError as exc:
        raise RuntimeError(f"{label}: authentication to the alarm API failed") from exc
    except UpstreamUnavailableError as exc:
        raise RuntimeError(f"{label}: alarm API unavailable after retries - {exc}") from exc
    return {"trace_id": trace_id, "data": data}


TraceId = Annotated[str | None, Field(description="Optional trace id to correlate this call with the rest of a multi-step request; generated if omitted")]


@mcp.tool()
async def search_assets(
    query: Annotated[str, Field(description="Free-text asset name or type to search for, e.g. 'Boiler Feed Pump 101' or 'compressor'")],
    unit: Annotated[str | None, Field(description="Restrict to a specific unit, e.g. 'Unit 2'")] = None,
    site: Annotated[str | None, Field(description="Restrict to a specific site, e.g. 'EastRefinery'")] = None,
    limit: Annotated[int, Field(description="Maximum number of matching assets to return", ge=1, le=100)] = 10,
    trace_id: TraceId = None,
) -> dict:
    """Search the asset registry by name or type. Use this first to resolve a named asset to its asset_id."""
    return await _run("search_assets", client.search_assets(query, unit, site, limit, trace_id=trace_id))


@mcp.tool()
async def get_asset_metadata(
    asset_id: Annotated[str, Field(description="Asset id returned by search_assets")],
    trace_id: TraceId = None,
) -> dict:
    """Fetch full metadata (type, unit, site, criticality, status) for a specific asset."""
    return await _run("get_asset_metadata", client.get_asset_metadata(asset_id, trace_id=trace_id))


@mcp.tool()
async def get_alarms(
    asset_id: Annotated[str | None, Field(description="Filter to a single asset id")] = None,
    unit: Annotated[str | None, Field(description="Filter to a unit")] = None,
    site: Annotated[str | None, Field(description="Filter to a site")] = None,
    status: Annotated[str | None, Field(description="Filter by alarm status: active | acknowledged | cleared")] = None,
    start_time: Annotated[str | None, Field(description="ISO-8601 lower bound on alarm start time")] = None,
    end_time: Annotated[str | None, Field(description="ISO-8601 upper bound on alarm start time")] = None,
    page: Annotated[int, Field(description="1-based page number", ge=1)] = 1,
    page_size: Annotated[int, Field(description="Results per page", ge=1, le=500)] = 50,
    sort_by: Annotated[str, Field(description="One of: start_time | severity | asset_id")] = "start_time",
    sort_order: Annotated[str, Field(description="asc or desc")] = "desc",
    trace_id: TraceId = None,
) -> dict:
    """List raw alarm records with filtering, sorting, and pagination."""
    return await _run("get_alarms", client.get_alarms(
        asset_id=asset_id, unit=unit, site=site, status=status, start_time=start_time, end_time=end_time,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order, trace_id=trace_id,
    ))


@mcp.tool()
async def get_alarm_by_id(
    alarm_id: Annotated[str, Field(description="Alarm id, e.g. from get_alarms")],
    trace_id: TraceId = None,
) -> dict:
    """Fetch a single alarm's full detail record."""
    return await _run("get_alarm_by_id", client.get_alarm_by_id(alarm_id, trace_id=trace_id))


@mcp.tool()
async def get_alarm_summary(
    start_time: Annotated[str, Field(description="ISO-8601 window start")],
    end_time: Annotated[str, Field(description="ISO-8601 window end")],
    asset_ids: Annotated[list[str] | None, Field(description="Limit to these asset ids")] = None,
    unit: Annotated[str | None, Field(description="Limit to a unit")] = None,
    site: Annotated[str | None, Field(description="Limit to a site")] = None,
    severity: Annotated[list[str] | None, Field(description="Limit to these severities, e.g. ['high','critical']")] = None,
    alarm_types: Annotated[list[str] | None, Field(description="Limit to these alarm types: process | device | safety")] = None,
    group_by: Annotated[list[str] | None, Field(description="Fields to group by, e.g. ['alarm_name'] or ['asset_id','severity']")] = None,
    kpis: Annotated[list[str] | None, Field(description="KPIs to compute per group, e.g. ['alarm_count','recurring_rate','avg_ack_delay']")] = None,
    trace_id: TraceId = None,
) -> dict:
    """Aggregate alarm counts and KPIs (recurrence rate, ack delay, etc.) grouped by asset, name, or severity."""
    body = {
        "asset_ids": asset_ids, "unit": unit, "site": site,
        "time_range": {"start_time": start_time, "end_time": end_time},
        "severity": severity, "alarm_types": alarm_types, "group_by": group_by, "kpis": kpis,
    }
    return await _run("get_alarm_summary", client.get_alarm_summary(body, trace_id=trace_id))


@mcp.tool()
async def get_alarm_trends(
    start_time: Annotated[str, Field(description="ISO-8601 window start")],
    end_time: Annotated[str, Field(description="ISO-8601 window end")],
    asset_ids: Annotated[list[str] | None, Field(description="Limit to these asset ids")] = None,
    unit: Annotated[str | None, Field(description="Limit to a unit")] = None,
    site: Annotated[str | None, Field(description="Limit to a site")] = None,
    bucket: Annotated[str, Field(description="Time bucket size: hourly | daily")] = "daily",
    metrics: Annotated[list[str] | None, Field(description="Metrics per bucket, e.g. ['alarm_count','avg_ack_delay']")] = None,
    trace_id: TraceId = None,
) -> dict:
    """Compute a time-bucketed trend of alarm activity over the requested window."""
    body = {
        "asset_ids": asset_ids, "unit": unit, "site": site,
        "time_range": {"start_time": start_time, "end_time": end_time},
        "bucket": bucket, "metrics": metrics,
    }
    return await _run("get_alarm_trends", client.get_alarm_trends(body, trace_id=trace_id))


@mcp.tool()
async def analyze_alarm_correlation(
    asset_ids: Annotated[list[str], Field(description="Two or more asset ids to check for co-occurring alarms", min_length=1)],
    start_time: Annotated[str, Field(description="ISO-8601 window start")],
    end_time: Annotated[str, Field(description="ISO-8601 window end")],
    correlation_method: Annotated[str, Field(description="Correlation method; currently 'cooccurrence'")] = "cooccurrence",
    lag_window_minutes: Annotated[int, Field(description="Max minutes between two alarms to count as co-occurring")] = 15,
    severity_threshold: Annotated[str | None, Field(description="Only consider alarms at or above this severity")] = None,
    min_support: Annotated[int, Field(description="Minimum co-occurrence count to report a pair")] = 1,
    trace_id: TraceId = None,
) -> dict:
    """Find pairs of assets whose alarms tend to fire close together in time -- useful for root-cause analysis."""
    body = {
        "asset_ids": asset_ids, "time_range": {"start_time": start_time, "end_time": end_time},
        "correlation_method": correlation_method, "lag_window_minutes": lag_window_minutes,
        "severity_threshold": severity_threshold, "min_support": min_support,
    }
    return await _run("analyze_alarm_correlation", client.analyze_correlation(body, trace_id=trace_id))


@mcp.tool()
async def analyze_alarm_flood(
    start_time: Annotated[str, Field(description="ISO-8601 window start")],
    end_time: Annotated[str, Field(description="ISO-8601 window end")],
    unit: Annotated[str | None, Field(description="Limit to a unit")] = None,
    site: Annotated[str | None, Field(description="Limit to a site")] = None,
    threshold_count: Annotated[int, Field(description="Alarm count within the rolling window that constitutes a flood")] = 10,
    rolling_window_minutes: Annotated[int, Field(description="Size of the rolling window in minutes")] = 10,
    trace_id: TraceId = None,
) -> dict:
    """Detect alarm flood windows (bursts exceeding a rate threshold) in the given period."""
    body = {
        "unit": unit, "site": site, "time_range": {"start_time": start_time, "end_time": end_time},
        "threshold_count": threshold_count, "rolling_window_minutes": rolling_window_minutes,
    }
    return await _run("analyze_alarm_flood", client.analyze_flood(body, trace_id=trace_id))


@mcp.tool()
async def get_rationalization_candidates(
    start_time: Annotated[str, Field(description="ISO-8601 window start")],
    end_time: Annotated[str, Field(description="ISO-8601 window end")],
    asset_ids: Annotated[list[str] | None, Field(description="Limit to these asset ids")] = None,
    unit: Annotated[str | None, Field(description="Limit to a unit")] = None,
    site: Annotated[str | None, Field(description="Limit to a site")] = None,
    recurrence_threshold: Annotated[int, Field(description="Occurrence count above which an alarm is flagged as recurring")] = 5,
    stale_minutes_threshold: Annotated[int, Field(description="Average active duration (minutes) above which an alarm is flagged as stale")] = 180,
    trace_id: TraceId = None,
) -> dict:
    """Identify alarms that are candidates for rationalization: chatter frequently or stay active far too long."""
    body = {
        "asset_ids": asset_ids, "unit": unit, "site": site,
        "time_range": {"start_time": start_time, "end_time": end_time},
        "recurrence_threshold": recurrence_threshold, "stale_minutes_threshold": stale_minutes_threshold,
    }
    return await _run("get_rationalization_candidates", client.get_rationalization_candidates(body, trace_id=trace_id))


@mcp.tool()
async def get_alarm_priority_score(
    alarm_id: Annotated[str, Field(description="Alarm id to score")],
    trace_id: TraceId = None,
) -> dict:
    """Compute a 0-100 priority score for a single alarm from severity, asset criticality, recurrence, and duration."""
    return await _run("get_alarm_priority_score", client.get_priority_score({"alarm_id": alarm_id}, trace_id=trace_id))


@mcp.tool()
async def get_operator_recommendations(
    alarm_id: Annotated[str, Field(description="Alarm id to generate recommendations for")],
    include_related: Annotated[bool, Field(description="Include other currently active alarms on the same asset")] = False,
    include_asset_context: Annotated[bool, Field(description="Include the parent asset's metadata")] = False,
    include_historical_pattern: Annotated[bool, Field(description="Include a 90-day recurrence summary for this alarm name on this asset")] = False,
    trace_id: TraceId = None,
) -> dict:
    """Get rule-based recommended operator actions for an alarm, optionally with related context."""
    body = {
        "alarm_id": alarm_id, "include_related": include_related,
        "include_asset_context": include_asset_context, "include_historical_pattern": include_historical_pattern,
    }
    return await _run("get_operator_recommendations", client.get_operator_recommendations(body, trace_id=trace_id))


@mcp.tool()
async def generate_kpi_calculation(
    calculation_type: Annotated[str, Field(description="One of: alarm_flood_index | critical_alarm_density | operator_response_efficiency | nuisance_alarm_score")],
    unit: Annotated[str | None, Field(description="Unit to scope the calculation to")] = None,
    site: Annotated[str | None, Field(description="Site to scope the calculation to")] = None,
    start_time: Annotated[str | None, Field(description="ISO-8601 window start")] = None,
    end_time: Annotated[str | None, Field(description="ISO-8601 window end")] = None,
    trace_id: TraceId = None,
) -> dict:
    """Register a KPI calculation and get back a calculation_id. Call execute_kpi_calculation with that id to run it."""
    body = {"calculation_type": calculation_type, "filters": {"unit": unit, "site": site, "start_time": start_time, "end_time": end_time}}
    return await _run("generate_kpi_calculation", client.generate_kpi_calculation(body, trace_id=trace_id))


@mcp.tool()
async def execute_kpi_calculation(
    calculation_id: Annotated[str, Field(description="calculation_id returned by generate_kpi_calculation")],
    unit: Annotated[str | None, Field(description="Override the unit filter from generate_kpi_calculation")] = None,
    site: Annotated[str | None, Field(description="Override the site filter from generate_kpi_calculation")] = None,
    start_time: Annotated[str | None, Field(description="Override the window start")] = None,
    end_time: Annotated[str | None, Field(description="Override the window end")] = None,
    trace_id: TraceId = None,
) -> dict:
    """Run a previously generated KPI calculation and return its result. Always call generate_kpi_calculation first."""
    filters = {k: v for k, v in {"unit": unit, "site": site, "start_time": start_time, "end_time": end_time}.items() if v is not None}
    body = {"calculation_id": calculation_id, "filters": filters or None}
    return await _run("execute_kpi_calculation", client.execute_kpi_calculation(body, trace_id=trace_id))


@mcp.tool()
async def list_kpi_definitions(trace_id: TraceId = None) -> dict:
    """List all KPI names the alarm API can compute, with descriptions and units."""
    return await _run("list_kpi_definitions", client.list_kpi_definitions(trace_id=trace_id))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
