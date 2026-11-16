from collections.abc import Callable
from typing import Final

from fastapi.testclient import TestClient

API_BASE_URL: Final = "https://testserver"
DEFAULT_PASSWORD: Final = "Correct-Horse-Battery-42"
DEMO_PASSWORD: Final = "Demo-Accounts-Pass-2026"

type LoginAs = Callable[..., TestClient]
type UserFactory = Callable[..., int]
type TicketFactory = Callable[..., int]
