"""Tests for MCPToolRegistry itself (apps/backend/orchestrator/mcp_client.py) --
discovery and call dispatch, as opposed to tests/integration/test_orchestration.py,
which exercises the ReAct loop against a hand-written fake registry.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from apps.backend.orchestrator.mcp_client import MCPToolRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]
ALARM_MCP_PORT = 18201


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.3)
    raise TimeoutError(f"nothing listening on {host}:{port} after {timeout}s")


def _closed_port() -> int:
    """A port nothing is listening on -- stands in for an unreachable MCP server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def alarm_mcp_url():
    # discover() only calls list_tools(), which FastMCP answers from the registered tool
    # signatures without touching the upstream alarm API -- so the alarm-simulator does
    # not need to be running for this fixture.
    env = os.environ.copy()
    env["MCP_ALARM_PORT"] = str(ALARM_MCP_PORT)
    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "mcp-servers" / "alarm_management" / "server.py")],
        cwd=str(REPO_ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port("localhost", ALARM_MCP_PORT)
        time.sleep(1)  # let the streamable-http route finish mounting
        yield f"http://localhost:{ALARM_MCP_PORT}/mcp"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.asyncio
async def test_call_rejects_a_name_without_a_namespace_separator():
    registry = MCPToolRegistry(servers={"alarm": "http://localhost:9/mcp"})
    result, is_error = await registry.call("search_assets", {})
    assert is_error
    assert "not a valid namespaced tool name" in result["error"]


@pytest.mark.asyncio
async def test_call_rejects_an_unknown_server_prefix():
    registry = MCPToolRegistry(servers={"alarm": "http://localhost:9/mcp"})
    result, is_error = await registry.call("workorders__search_work_orders", {})
    assert is_error
    assert "unknown MCP server 'workorders'" in result["error"]


@pytest.mark.asyncio
async def test_discover_skips_an_unreachable_server_and_keeps_the_reachable_one(alarm_mcp_url):
    dead_port = _closed_port()
    registry = MCPToolRegistry(servers={
        "alarm": alarm_mcp_url,
        "ghost": f"http://localhost:{dead_port}/mcp",
    })

    tools = await registry.discover()

    assert {t.server for t in tools} == {"alarm"}
    assert any(t.name == "search_assets" for t in tools)


@pytest.mark.asyncio
async def test_call_against_an_unreachable_server_reports_unavailable_not_an_exception():
    dead_port = _closed_port()
    registry = MCPToolRegistry(servers={"ghost": f"http://localhost:{dead_port}/mcp"})

    result, is_error = await registry.call("ghost__anything", {})

    assert is_error
    assert "unavailable" in result["error"]
