"""Optional Redis cache for API configs."""

from __future__ import annotations

import json
from typing import Optional

import redis

from app.settings import get_settings


def _client() -> Optional[redis.Redis]:
    url = get_settings().redis_url
    if not url:
        return None
    return redis.from_url(url, decode_responses=True)


def get_cached_api_configs() -> Optional[list[dict]]:
    r = _client()
    if r is None:
        return None
    raw = r.get("teambition:api_configs")
    if not raw:
        return None
    data = json.loads(raw)
    if isinstance(data, list):
        return data
    return None


def set_cached_api_configs(configs: list[dict]) -> None:
    r = _client()
    if r is None:
        return
    r.set("teambition:api_configs", json.dumps(configs, ensure_ascii=False))
