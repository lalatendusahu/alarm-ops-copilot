import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

ALARM_API_PORT = 18100
WORKORDER_API_PORT = 18110
ALARM_MCP_PORT = 18101
WORKORDER_MCP_PORT = 18111


def _wait_for_port(host: str, port: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.3)
    raise TimeoutError(f"nothing listening on {host}:{port} after {timeout}s")


def _spawn(cmd: list[str], cwd: Path, env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        cmd, cwd=str(cwd), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="session")
def live_stack():
    if not (REPO_ROOT / "rag" / "index" / "manifest.json").exists():
        pytest.skip("RAG index not built -- run `python rag/ingestion/ingest.py` before the e2e suite")

    processes = []
    base_env = os.environ.copy()
    base_env["ALARM_API_TOKEN"] = "demo-token"
    base_env["WORK_ORDER_API_TOKEN"] = "demo-token"

    alarm_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    wo_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name

    alarm_env = base_env.copy()
    alarm_env["ALARM_DB_PATH"] = alarm_db
    processes.append(_spawn(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(ALARM_API_PORT)],
        REPO_ROOT / "alarm-simulator", alarm_env,
    ))

    wo_env = base_env.copy()
    wo_env["WORK_ORDER_DB_PATH"] = wo_db
    processes.append(_spawn(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(WORKORDER_API_PORT)],
        REPO_ROOT / "work-order-service", wo_env,
    ))

    _wait_for_port("localhost", ALARM_API_PORT)
    _wait_for_port("localhost", WORKORDER_API_PORT)

    alarm_mcp_env = base_env.copy()
    alarm_mcp_env["ALARM_API_BASE_URL"] = f"http://localhost:{ALARM_API_PORT}"
    alarm_mcp_env["MCP_ALARM_PORT"] = str(ALARM_MCP_PORT)
    processes.append(_spawn(
        [sys.executable, str(REPO_ROOT / "mcp-servers" / "alarm_management" / "server.py")],
        REPO_ROOT, alarm_mcp_env,
    ))

    wo_mcp_env = base_env.copy()
    wo_mcp_env["WORK_ORDER_API_BASE_URL"] = f"http://localhost:{WORKORDER_API_PORT}"
    wo_mcp_env["MCP_WORKORDERS_PORT"] = str(WORKORDER_MCP_PORT)
    processes.append(_spawn(
        [sys.executable, str(REPO_ROOT / "mcp-servers" / "work_orders" / "server.py")],
        REPO_ROOT, wo_mcp_env,
    ))

    _wait_for_port("localhost", ALARM_MCP_PORT)
    _wait_for_port("localhost", WORKORDER_MCP_PORT)
    time.sleep(1)  # let the MCP servers finish mounting their streamable-http route

    yield {
        "alarm_api_url": f"http://localhost:{ALARM_API_PORT}",
        "workorder_api_url": f"http://localhost:{WORKORDER_API_PORT}",
        "alarm_mcp_url": f"http://localhost:{ALARM_MCP_PORT}/mcp",
        "workorder_mcp_url": f"http://localhost:{WORKORDER_MCP_PORT}/mcp",
    }

    for proc in processes:
        proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    for path in (alarm_db, wo_db):
        try:
            os.unlink(path)
        except OSError:
            pass
