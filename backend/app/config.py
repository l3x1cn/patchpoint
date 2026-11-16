from pathlib import Path
from typing import Final

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION: Final = "0.2.0"
BACKEND_DIR: Final = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PATCHPOINT_")

    database_path: Path = BACKEND_DIR / "data" / "patchpoint.db"
    seed_demo_data: bool = True
    docs_enabled: bool = False
    cors_origins: list[str] = ["http://localhost:5500"]
    max_body_bytes: int = Field(default=65_536, ge=1_024, le=10_485_760)

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_origin(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError(
                "cors_origins must list explicit origins; '*' cannot be combined with credentials"
            )

        return origins
