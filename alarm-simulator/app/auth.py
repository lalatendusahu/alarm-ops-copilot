import os
import uuid

from fastapi import Header, HTTPException, Request

EXPECTED_TOKEN = os.getenv("ALARM_API_TOKEN", "demo-token")


def require_bearer_token(authorization: str = Header(default="")) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")


class TraceContext:
    def __init__(self, trace_id: str, client_id: str | None, metadata_tag: str | None):
        self.trace_id = trace_id
        self.client_id = client_id
        self.metadata_tag = metadata_tag


def get_trace_context(
    request: Request,
    trace_id: str | None = Header(default=None),
    x_client_id: str | None = Header(default=None),
    x_metadata_tag: str | None = Header(default=None),
) -> TraceContext:
    resolved_trace_id = trace_id or request.headers.get("trace_id") or str(uuid.uuid4())
    return TraceContext(resolved_trace_id, x_client_id, x_metadata_tag)
