import logging
import os
import sys

_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            stream=sys.stdout,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        _configured = True
    return logging.getLogger(name)


def log_request(logger: logging.Logger, *, route: str, trace_id: str, client_id: str | None, status: int, duration_ms: float) -> None:
    logger.info(
        "route=%s trace_id=%s client_id=%s status=%s duration_ms=%.1f",
        route, trace_id, client_id or "-", status, duration_ms,
    )
