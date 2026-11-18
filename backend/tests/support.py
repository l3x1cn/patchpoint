import json
import logging
from collections.abc import Callable
from typing import Any, Final

import pytest
from fastapi.testclient import TestClient

API_BASE_URL: Final = "https://testserver"
DEFAULT_PASSWORD: Final = "Correct-Horse-Battery-42"
DEMO_PASSWORD: Final = "Demo-Accounts-Pass-2026"
SECURITY_LOGGER: Final = "patchpoint.security"
ERRORS_LOGGER: Final = "patchpoint.errors"

type LoginAs = Callable[..., TestClient]
type UserFactory = Callable[..., int]
type TicketFactory = Callable[..., int]


def log_records(
    caplog: pytest.LogCaptureFixture, logger: str = SECURITY_LOGGER
) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == logger]


def log_events(
    caplog: pytest.LogCaptureFixture, logger: str = SECURITY_LOGGER
) -> list[dict[str, Any]]:
    return [json.loads(record.getMessage()) for record in log_records(caplog, logger)]
