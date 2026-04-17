#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teambition API 配置侧边栏模块
"""

import time

import jwt
import requests
import streamlit as st

# 与开放平台「应用授权凭证」及 @tng/teambition-openapi-sdk 一致：本地用 appSecret 签 HS256 JWT，再 POST 换取 app_access_token。
# 文档若写「POST https://open.teambition.com/v3/app/token」：请勿在浏览器打开该地址（会进登录页）；程序里请用下方官方网关路径。
# 请求格式相同：Authorization: Bearer <应用 JWT>，Body: {"appId","appSecret"}。线上可调用的换票接口为 POST /api/appToken（非 /v3/app/token）。
OPEN_API_BASE = "https://open.teambition.com/api"
APP_TOKEN_PATH = "/appToken"

# 企业应用凭证（仅 Python 侧使用，界面不展示 AppId / Secret / 企业ID 明文）
COMPANY_PROFILES = {
    "上海麦汇信息科技有限公司": {
        "app_id": "69c9def37c12e5933cd9ca4f",
        "app_secret": "x6FKGCHbRhc9rmZEMMzRHjVVNTNe6Vfo",
        "tenant_id": "5e2558954f68db000132597c",
    },
}


def apply_company_to_session(company_name: str) -> None:
    """根据所选企业将凭证写入 session_state（不在页面渲染这些字段）。"""
    if company_name not in COMPANY_PROFILES:
        return
    profile = COMPANY_PROFILES[company_name]
    st.session_state["app_id"] = profile["app_id"]
    st.session_state["app_secret"] = profile["app_secret"]
    st.session_state["tenant_id"] = profile["tenant_id"]
    st.session_state["selected_company"] = company_name


def sign_app_access_jwt(app_id: str, app_secret: str, periodical: int = 3600) -> str:
    """
    使用 appSecret 签发「应用授权凭证」JWT（HS256），供换取 app_access_token 时使用。
    算法与 @tng/teambition-openapi-sdk / tws-auth 的 signAppToken 一致。
    """
    iat = int(time.time() / periodical) * periodical
    payload = {
        "iat": iat,
        "exp": iat + int(1.1 * periodical),
        "_appId": app_id,
    }
    return jwt.encode(payload, app_secret, algorithm="HS256")


def get_app_token(app_id: str, app_secret: str) -> str:
    """
    通过 appId 和 appSecret 获取应用 Token（app_access_token）。

    请求方式：POST {OPEN_API_BASE}{APP_TOKEN_PATH}
    - Header: Authorization: Bearer <应用 JWT>
    - Body: {"appId", "appSecret"}

    Args:
        app_id: 应用 ID
        app_secret: 应用密钥

    Returns:
        app_token: 访问令牌
    """
    url = f"{OPEN_API_BASE}{APP_TOKEN_PATH}"
    app_jwt = sign_app_access_jwt(app_id, app_secret)
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Content-Type": "application/json",
    }
    payload = {
        "appId": app_id,
        "appSecret": app_secret,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    try:
        result = response.json()
    except ValueError:
        raise Exception(f"获取 Token 失败: 非 JSON 响应 (HTTP {response.status_code})") from None

    if isinstance(result, dict) and result.get("message") and result.get("error"):
        raise Exception(f"获取 Token 失败: {result.get('message')}")

    code = result.get("code") if isinstance(result, dict) else None
    if code is not None and code not in (0, 200):
        raise Exception(
            f"获取 Token 失败: {result.get('errorMessage', result)} (code: {code})"
        )

    if not isinstance(result, dict):
        raise Exception(f"获取 Token 失败: {result}")

    token = None
    inner = result.get("result")
    if isinstance(inner, dict):
        token = inner.get("appToken")
    if not token:
        token = result.get("appToken")

    if not token:
        raise Exception(f"获取 Token 失败: {result}")

    return token


def sidebar():
    """侧栏不再展示应用凭证；凭证在「认证」页通过企业下拉注入。保留函数供兼容。"""
    return st.session_state.get("token", ""), st.session_state.get("tenant_id", "")