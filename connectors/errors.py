class ConnectorError(Exception):
    """Base class for all connector-level failures."""


class AuthError(ConnectorError):
    """Upstream rejected the bearer token."""


class NotFoundError(ConnectorError):
    """Upstream returned 404 for the requested resource."""


class ValidationError(ConnectorError):
    """Upstream rejected the request payload (4xx other than 401/404)."""


class UpstreamUnavailableError(ConnectorError):
    """Upstream timed out or returned 5xx after retries were exhausted."""
