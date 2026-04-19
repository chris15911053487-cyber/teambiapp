"""Application settings."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated browser origins",
    )
    redis_url: Optional[str] = Field(default=None, description="redis://localhost:6379/0")
    jwt_secret: Optional[str] = Field(
        default=None,
        description="If set, /auth/token returns session_jwt wrapping Teambition token",
    )
    jwt_ttl_seconds: int = 86400
    tb_company_profiles_json: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("TB_COMPANY_PROFILES_JSON"),
        description='JSON array: [{"name":"...","app_id":"...","app_secret":"...","tenant_id":"..."}]',
    )

    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_company_profiles() -> Dict[str, Dict[str, str]]:
    """name -> {app_id, app_secret, tenant_id}."""
    raw = get_settings().tb_company_profiles_json
    if not raw:
        # Optional: load from file path for local dev
        path = os.environ.get("TB_COMPANY_PROFILES_FILE")
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                raw = f.read()
    if not raw:
        return {}
    data: Any = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("TB_COMPANY_PROFILES_JSON must be a JSON array")
    out: Dict[str, Dict[str, str]] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        out[name] = {
            "app_id": str(row["app_id"]),
            "app_secret": str(row["app_secret"]),
            "tenant_id": str(row["tenant_id"]),
        }
    return out
