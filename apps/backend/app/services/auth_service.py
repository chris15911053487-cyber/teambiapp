"""Auth: daily passphrase + optional session JWT."""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

import jwt
from pydantic import BaseModel

from teambition_client.auth import get_app_token

from app.settings import get_settings


class TokenResult(BaseModel):
    teambition_access_token: str
    tenant_id: str
    company_name: str
    session_jwt: Optional[str] = None


def _issue_session_jwt(tb_token: str, tenant_id: str, company_name: str) -> Optional[str]:
    settings = get_settings()
    if not settings.jwt_secret:
        return None
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "tte": tb_token,
        "tid": tenant_id,
        "cn": company_name,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + settings.jwt_ttl_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_session_jwt(token: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.jwt_secret:
        raise ValueError("JWT not configured")
    data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    return {
        "teambition_access_token": str(data["tte"]),
        "tenant_id": str(data["tid"]),
        "company_name": str(data.get("cn", "")),
    }


def exchange_app_credentials(
    *,
    app_id: str,
    app_secret: str,
    tenant_id: str,
    company_name: str,
    passphrase: str,
) -> TokenResult:
    today = dt.datetime.now().strftime("%Y%m%d")
    if passphrase != today:
        raise PermissionError("暗号错误")

    tb_token = get_app_token(app_id, app_secret)
    session_jwt = _issue_session_jwt(tb_token, tenant_id, company_name)
    return TokenResult(
        teambition_access_token=tb_token,
        tenant_id=tenant_id,
        company_name=company_name,
        session_jwt=session_jwt,
    )
