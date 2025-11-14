from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, RootModel


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    ee_service_account: str
    algeria_asset_id: str = "projects/ee-bensefiasofian/assets/Maine"
    default_buffer_m: int = 10000

    @classmethod
    def from_env(cls, env: Optional[dict[str, str]] = None) -> "Settings":
        data = env or os.environ

        # لم نعد نحتاج EE_CREDENTIALS_PATH
        service_account = data.get("EE_SERVICE_ACCOUNT")
        if not service_account:
            raise ValueError(
                "EE_SERVICE_ACCOUNT environment variable is required and must contain the Earth Engine service account email."
            )

        return cls(
            ee_service_account=service_account,
            algeria_asset_id=data.get(
                "ALGERIA_REGION_ASSET",
                "projects/ee-bensefiasofian/assets/Maine",
            ),
            default_buffer_m=int(data.get("EE_DEFAULT_BUFFER_M", "10000")),
        )


class SettingsContainer(RootModel[Settings]):
    """Helper wrapper so settings can be injected as a dependency in FastAPI."""

    root: Settings

    @property
    def settings(self) -> Settings:
        return self.root


settings = Settings.from_env()
