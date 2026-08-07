import os
import tempfile

os.environ["WORK_ORDER_DB_PATH"] = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["WORK_ORDER_API_TOKEN"] = "demo-token"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer demo-token"}
