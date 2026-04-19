"""Application JWT + appToken exchange (no Streamlit)."""

from __future__ import annotations

import time

import jwt
import requests

OPEN_API_BASE = "https://open.teambition.com/api"
APP_TOKEN_PATH = "/appToken"


def sign_app_access_jwt(app_id: str, app_secret: str, periodical: int = 3600) -> str:
    """HS256 app JWT for exchanging app_access_token (same as legacy config_sidebar)."""
    iat = int(time.time() / periodical) * periodical
    payload = {
        "iat": iat,
        "exp": iat + int(1.1 * periodical),
        "_appId": app_id,
    }
    return jwt.encode(payload, app_secret, algorithm="HS256")


def get_app_token(app_id: str, app_secret: str, *, timeout: float = 10.0) -> str:
    """POST /api/appToken with Bearer app JWT."""
    url = f"{OPEN_API_BASE}{APP_TOKEN_PATH}"
    app_jwt = sign_app_access_jwt(app_id, app_secret)
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Content-Type": "application/json",
    }
    payload = {"appId": app_id, "appSecret": app_secret}

    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"获取 Token 失败: 非 JSON 响应 (HTTP {response.status_code})"
        ) from exc

    if isinstance(result, dict) and result.get("message") and result.get("error"):
        raise RuntimeError(f"获取 Token 失败: {result.get('message')}")

    code = result.get("code") if isinstance(result, dict) else None
    if code is not None and code not in (0, 200):
        raise RuntimeError(
            f"获取 Token 失败: {result.get('errorMessage', result)} (code: {code})"
        )

    if not isinstance(result, dict):
        raise RuntimeError(f"获取 Token 失败: {result}")

    token = None
    inner = result.get("result")
    if isinstance(inner, dict):
        token = inner.get("appToken")
    if not token:
        token = result.get("appToken")

    if not token:
        raise RuntimeError(f"获取 Token 失败: {result}")

    return token
