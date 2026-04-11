#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teambition API 配置侧边栏模块
"""

import streamlit as st
import requests


def get_app_token(app_id: str, app_secret: str) -> str:
    """
    通过 appId 和 appSecret 获取 Token

    Args:
        app_id: 应用 ID
        app_secret: 应用密钥

    Returns:
        app_token: 访问令牌
    """
    url = "https://open.teambition.com/api/appToken"
    payload = {
        "appId": app_id,
        "appSecret": app_secret
    }

    response = requests.post(url, json=payload, timeout=10)
    result = response.json()

    if "appToken" not in result:
        raise Exception(f"获取 Token 失败: {result}")

    return result["appToken"]


def sidebar():
    """侧边栏配置"""
    st.sidebar.title("⚙️ 配置")

    # 应用凭证配置
    st.sidebar.subheader("🔑 应用凭证")

    app_id = st.sidebar.text_input(
        "App ID",
        value=st.session_state.get('app_id', '69d216d0639800db95c6a7f8'),
        help="Teambition 应用的 App ID"
    )

    app_secret = st.sidebar.text_input(
        "App Secret",
        value=st.session_state.get('app_secret', 'j2lu9G3bfsWarbci9oA3cUFehEOP7CIM'),
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
        value=st.session_state.get('tenant_id', '69c9f3992912b1e898c974f3'),
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

    **Token 有效期**: 约 30 分钟
    """)

    return token, tenant_id