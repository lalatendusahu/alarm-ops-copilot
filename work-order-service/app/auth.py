import os
import uuid

from fastapi import Header, HTTPException, Request

EXPECTED_TOKEN = os.getenv("WORK_ORDER_API_TOKEN", "demo-token")


def require_bearer_token(authorization: str = Header(default="")) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    if authorization.removeprefix("Bearer ").strip() != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")


class TraceContext:
    def __init__(self, trace_id: str, client_id: str | None):
        self.trace_id = trace_id
        self.client_id = client_id


def get_trace_context(
    request: Request,
    trace_id: str | None = Header(default=None),
    x_client_id: str | None = Header(default=None),
) -> TraceContext:
    resolved = trace_id or request.headers.get("trace_id") or str(uuid.uuid4())
    return TraceContext(resolved, x_client_id)
