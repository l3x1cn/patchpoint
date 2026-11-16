from pathlib import Path
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION: Final = "0.1.0"
BACKEND_DIR: Final = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PATCHPOINT_")

    database_path: Path = BACKEND_DIR / "data" / "patchpoint.db"
    seed_demo_data: bool = True
