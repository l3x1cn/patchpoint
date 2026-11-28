from pathlib import Path
from typing import Final, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION: Final = "0.3.0"
BACKEND_DIR: Final = Path(__file__).resolve().parent.parent
HOST_COOKIE_PREFIX: Final = "__Host-"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PATCHPOINT_")

    database_path: Path = BACKEND_DIR / "data" / "patchpoint.db"
    seed_demo_data: bool = False
    demo_password: SecretStr | None = None
    docs_enabled: bool = False
    cors_origins: list[str] = ["http://patchpoint.localhost:5500"]
    max_body_bytes: int = Field(default=65_536, ge=1_024, le=10_485_760)
    cookie_secure: bool = True
    cookie_name: str = Field(default="session", pattern=r"^(__Host-)?[A-Za-z][A-Za-z0-9_-]{0,63}$")
    session_idle_minutes: int = Field(default=30, ge=1, le=1_440)
    session_absolute_minutes: int = Field(default=480, ge=1, le=10_080)
    login_max_failures: int = Field(default=5, ge=1, le=100)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1_440)

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_origin(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError(
                "cors_origins must list explicit origins; '*' cannot be combined with credentials"
            )

        return origins

    @model_validator(mode="after")
    def require_demo_password_for_seed(self) -> Self:
        if self.seed_demo_data and self.demo_password is None:
            raise ValueError(
                "PATCHPOINT_DEMO_PASSWORD is required when PATCHPOINT_SEED_DEMO_DATA is true"
            )

        return self

    @model_validator(mode="after")
    def require_secure_cookie_for_host_prefix(self) -> Self:
        if self.cookie_name.startswith(HOST_COOKIE_PREFIX) and not self.cookie_secure:
            raise ValueError(
                "PATCHPOINT_COOKIE_NAME with the __Host- prefix "
                "requires PATCHPOINT_COOKIE_SECURE=true"
            )

        return self
