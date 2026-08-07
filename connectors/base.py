import uuid

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from connectors.errors import AuthError, NotFoundError, UpstreamUnavailableError, ValidationError


class BaseConnector:
    """Thin HTTP client shared by the MCP servers: bearer auth, trace propagation,
    timeout, retry with backoff on transient failures, and error classification.
    """

    def __init__(self, base_url: str, token: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self, trace_id: str | None, client_id: str | None, metadata_tag: str | None) -> tuple[dict, str]:
        resolved_trace_id = trace_id or str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {self.token}",
            "trace_id": resolved_trace_id,
        }
        if client_id:
            headers["x-client-id"] = client_id
        if metadata_tag:
            headers["x-metadata-tag"] = metadata_tag
        return headers, resolved_trace_id

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        trace_id: str | None = None,
        client_id: str | None = None,
        metadata_tag: str | None = None,
    ) -> tuple[dict, str]:
        headers, resolved_trace_id = self._headers(trace_id, client_id, metadata_tag)
        url = f"{self.base_url}{path}"

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.2, max=2),
            retry=retry_if_exception_type(UpstreamUnavailableError),
            reraise=True,
        )
        async def _call() -> dict:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.request(method, url, params=params, json=json_body, headers=headers)
                except httpx.TimeoutException as exc:
                    raise UpstreamUnavailableError(f"timeout calling {url}") from exc
                except httpx.ConnectError as exc:
                    raise UpstreamUnavailableError(f"connection error calling {url}") from exc

            if response.status_code == 401:
                raise AuthError(response.text)
            if response.status_code == 404:
                raise NotFoundError(response.text)
            if response.status_code >= 500:
                raise UpstreamUnavailableError(f"{response.status_code}: {response.text}")
            if response.status_code >= 400:
                raise ValidationError(response.text)
            return response.json()

        result = await _call()
        return result, resolved_trace_id

    async def get(self, path: str, *, params: dict | None = None, **trace_kwargs) -> tuple[dict, str]:
        return await self.request("GET", path, params=params, **trace_kwargs)

    async def post(self, path: str, *, json_body: dict | None = None, **trace_kwargs) -> tuple[dict, str]:
        return await self.request("POST", path, json_body=json_body, **trace_kwargs)
