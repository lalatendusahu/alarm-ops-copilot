import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def alarm_mcp_module():
    return _load("alarm_mcp_server", REPO_ROOT / "mcp-servers" / "alarm_management" / "server.py")


@pytest.fixture(scope="session")
def workorder_mcp_module():
    return _load("workorder_mcp_server", REPO_ROOT / "mcp-servers" / "work_orders" / "server.py")
