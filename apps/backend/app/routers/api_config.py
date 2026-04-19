"""API registry CRUD + Redis cache."""

from __future__ import annotations

import copy
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from teambition_client import DEFAULT_API_CONFIGS, TeambitionAPI

from app.deps import get_teambition_client
from app.services.config_cache import get_cached_api_configs, set_cached_api_configs

router = APIRouter(prefix="/api-configs", tags=["api-configs"])


@router.get("")
def get_configs(_client: Annotated[TeambitionAPI, Depends(get_teambition_client)]):
    cached = get_cached_api_configs()
    return {"configs": copy.deepcopy(cached) if cached else copy.deepcopy(DEFAULT_API_CONFIGS)}


@router.put("")
def put_configs(
    body: dict[str, Any],
    _client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    configs = body.get("configs")
    if not isinstance(configs, list):
        return {"ok": False, "error": "configs must be a list"}
    set_cached_api_configs(configs)
    return {"ok": True, "configs": configs}
