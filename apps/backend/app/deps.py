"""FastAPI dependencies."""

from __future__ import annotations

import copy
from typing import Annotated, Optional

from fastapi import Header, HTTPException

from teambition_client import DEFAULT_API_CONFIGS, TeambitionAPI

from app.debug_store import append_log
from app.services.auth_service import decode_session_jwt
from app.services.config_cache import get_cached_api_configs
from app.settings import get_settings


def resolve_teambition_token(authorization: str) -> tuple[str, Optional[str]]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 需为 Bearer")
    bearer = authorization[7:].strip()
    settings = get_settings()
    if settings.jwt_secret:
        try:
            d = decode_session_jwt(bearer)
            return d["teambition_access_token"], d["tenant_id"]
        except Exception:
            pass
    return bearer, None


def get_teambition_client(
    authorization: Annotated[str, Header()],
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_debug_session: Annotated[Optional[str], Header(alias="X-Debug-Session")] = None,
) -> TeambitionAPI:
    token, tenant_from_jwt = resolve_teambition_token(authorization)
    tenant_id = tenant_from_jwt or x_tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="缺少 X-Tenant-Id")

    cached = get_cached_api_configs()
    configs = copy.deepcopy(cached) if cached else copy.deepcopy(DEFAULT_API_CONFIGS)

    debug = bool(x_debug_session)

    def on_log(entry: dict) -> None:
        if x_debug_session:
            append_log(x_debug_session, entry)

    return TeambitionAPI(
        token,
        tenant_id,
        api_configs=configs,
        debug=debug,
        on_request_log=on_log if debug else None,
    )
