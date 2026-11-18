import json
import logging
from typing import Final

from fastapi import Request

SECURITY_LOGGER: Final = logging.getLogger("patchpoint.security")
ERROR_LOGGER: Final = logging.getLogger("patchpoint.errors")

_LOG_FORMAT: Final = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    """Attach one stderr handler to the application logger; propagation stays on for tests."""
    app_logger = logging.getLogger("patchpoint")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)


def log_security_event(
    event: str,
    request: Request | None,
    *,
    level: int = logging.INFO,
    **fields: str | int | None,
) -> None:
    """Log a security event as one JSON line. Callers must never pass secrets in `fields`."""
    client_ip = request.client.host if request is not None and request.client is not None else None
    payload = {"event": event, "client_ip": client_ip, **fields}
    SECURITY_LOGGER.log(level, json.dumps(payload, ensure_ascii=False, sort_keys=True))
