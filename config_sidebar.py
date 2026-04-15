#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teambition API 配置侧边栏模块
"""

import time

import jwt
import requests
import streamlit as st

# 与开放平台「应用授权凭证」及官方 OpenAPI 客户端一致：先签发应用 JWT，再换取 app_access_token。
# 网关地址见 https://open.teambition.com/docs —— 获取应用授权 Token 对应 POST /appToken（完整 URL 如下）。
OPEN_API_BASE = "https://open.teambition.com/api"
APP_TOKEN_PATH = "/appToken"


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
    """侧边栏配置"""
    st.sidebar.title("⚙️ 配置")

    # 应用凭证配置
    st.sidebar.subheader("🔑 应用凭证")

    app_id = st.sidebar.text_input(
        "App ID",
        value=st.session_state.get('app_id', ''),
        help="Teambition 应用的 App ID"
    )

    app_secret = st.sidebar.text_input(
        "App Secret",
        value=st.session_state.get('app_secret', ''),
        help="Teambition 应用的 App Secret",
        type="password"
    )

    # 保存到 session
    st.session_state['app_id'] = app_id
    st.session_state['app_secret'] = app_secret

    # 获取 Token 按钮
    if st.sidebar.button("🔄 获取 Token", use_container_width=True):
        with st.spinner("获取 Token 中..."):
            try:
                token = get_app_token(app_id, app_secret)
                st.session_state['token'] = token
                st.sidebar.success("✅ Token 获取成功!")
                st.sidebar.info(f"Token: {token[:30]}...")
            except Exception as e:
                st.sidebar.error(f"❌ 错误: {e}")

    st.sidebar.markdown("---")

    # Token 输入（可以手动输入或自动获取）
    token = st.sidebar.text_input(
        "Access Token (可选)",
        value=st.session_state.get('token', ''),
        help="自动获取失败时可手动输入",
        type="password"
    )

    # 企业 ID 输入
    tenant_id = st.sidebar.text_input(
        "企业 ID (Tenant ID)",
        value=st.session_state.get('tenant_id', ''),
        help="企业/组织的唯一标识"
    )

    # 保存到 session
    st.session_state['token'] = token
    st.session_state['tenant_id'] = tenant_id

    # 使用说明
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 📖 使用说明

    **方式一（推荐）**: 输入 App ID 和 App Secret，点击"获取 Token"

    **方式二**: 手动从开放平台复制 Token 粘贴

    **Token 有效期**: 以接口返回为准（应用 JWT 建议按文档约 1 小时轮换）
    """)

    return token, tenant_id