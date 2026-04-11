#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teambition API Web 应用
使用 Streamlit 构建图形界面
"""

import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="Teambition API 工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


class TeambitionAPI:
    """Teambition API 客户端"""
    
    BASE_URL = "https://open.teambition.com/api"
    
    def __init__(self, token: str, tenant_id: str):
        self.token = token
        self.tenant_id = tenant_id
        
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Tenant-type": "organization",
            "X-Tenant-Id": self.tenant_id
        }
    
    def _request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        response = requests.request(method, url, headers=headers, **kwargs)
        result = response.json()
        
        code = result.get("code")
        if code is not None and code not in [0, 200]:
            raise Exception(f"API 错误: {result.get('errorMessage')} (code: {code})")
            
        return result
    
    def get_org_info(self):
        """获取企业信息"""
        return self._request("GET", "/org/info")
    
    def get_projects(self, page_size: int = 50):
        """获取项目列表"""
        result = self._request("GET", "/v3/project/query", 
                              params={"pageSize": page_size})
        return result.get("result", [])
    
    def get_project_tasks(self, project_id: str, page_size: int = 50):
        """获取项目任务"""
        result = self._request("GET", f"/v3/project/{project_id}/task/query",
                              params={"pageSize": page_size})
        return result.get("result", [])


def get_api_client():
    """获取 API 客户端"""
    token = st.session_state.get('token', '')
    tenant_id = st.session_state.get('tenant_id', '')
    
    if not token or not tenant_id:
        return None
    
    return TeambitionAPI(token, tenant_id)


def to_excel(df_list, sheet_names):
    """将多个 DataFrame 导出为 Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for df, sheet_name in zip(df_list, sheet_names):
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


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


def main_page():
    """主页面"""
    st.title("📊 Teambition API 工具")
    st.markdown("获取企业信息、项目列表和任务数据，并导出到 Excel")
    
    # 检查配置
    client = get_api_client()
    if not client:
        st.warning("⚠️ 请在左侧边栏配置 Token 和企业 ID")
        return
    
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fetch_org = st.button("🏢 获取企业信息", use_container_width=True)
    with col2:
        fetch_projects = st.button("📁 获取项目列表", use_container_width=True)
    with col3:
        fetch_all = st.button("🚀 获取全部数据", use_container_width=True, type="primary")
    
    # 数据存储
    if 'org_data' not in st.session_state:
        st.session_state.org_data = None
    if 'projects_data' not in st.session_state:
        st.session_state.projects_data = None
    if 'tasks_data' not in st.session_state:
        st.session_state.tasks_data = {}
    
    # 获取企业信息
    if fetch_org or fetch_all:
        with st.spinner("获取企业信息中..."):
            try:
                org_info = client.get_org_info()
                st.session_state.org_data = org_info.get('result', {})
                st.success("✅ 企业信息获取成功!")
            except Exception as e:
                st.error(f"❌ 错误: {e}")
    
    # 获取项目列表
    if fetch_projects or fetch_all:
        with st.spinner("获取项目列表中..."):
            try:
                projects = client.get_projects(page_size=50)
                st.session_state.projects_data = projects
                st.success(f"✅ 找到 {len(projects)} 个项目!")
            except Exception as e:
                st.error(f"❌ 错误: {e}")
    
    # 获取所有项目的任务
    if fetch_all and st.session_state.projects_data:
        tasks_data = {}
        progress_bar = st.progress(0)
        
        for i, project in enumerate(st.session_state.projects_data):
            project_id = project.get('id')
            project_name = project.get('name', '未命名')
            
            try:
                tasks = client.get_project_tasks(project_id, page_size=50)
                tasks_data[project_id] = {
                    'name': project_name,
                    'tasks': tasks
                }
                progress_bar.progress((i + 1) / len(st.session_state.projects_data))
            except Exception as e:
                st.warning(f"获取项目 [{project_name}] 的任务失败: {e}")
        
        st.session_state.tasks_data = tasks_data
        total_tasks = sum(len(t['tasks']) for t in tasks_data.values())
        st.success(f"✅ 共获取 {total_tasks} 个任务!")
        progress_bar.empty()
    
    # 显示数据
    display_data()
    
    # 导出功能
    export_data()


def display_data():
    """显示获取的数据"""
    
    # 显示企业信息
    if st.session_state.org_data:
        st.markdown("---")
        st.subheader("🏢 企业信息")
        org = st.session_state.org_data
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("企业名称", org.get('name', 'N/A'))
        with col2:
            st.metric("企业 ID", org.get('orgId', 'N/A'))
        with col3:
            st.metric("创建时间", org.get('created', 'N/A'))
        
        with st.expander("查看详细信息"):
            st.json(org)
    
    # 显示项目列表
    if st.session_state.projects_data:
        st.markdown("---")
        st.subheader(f"📁 项目列表 (共 {len(st.session_state.projects_data)} 个)")
        
        # 转换为 DataFrame 显示
        projects_df = pd.DataFrame(st.session_state.projects_data)
        if not projects_df.empty:
            display_cols = ['name', 'description', 'created', 'id']
            available_cols = [c for c in display_cols if c in projects_df.columns]
            st.dataframe(projects_df[available_cols], use_container_width=True)
        
        # 显示每个项目的任务
        if st.session_state.tasks_data:
            st.markdown("---")
            st.subheader("📋 项目任务")
            
            for project_id, data in st.session_state.tasks_data.items():
                project_name = data['name']
                tasks = data['tasks']
                
                with st.expander(f"📂 {project_name} ({len(tasks)} 个任务)"):
                    if tasks:
                        tasks_df = pd.DataFrame(tasks)
                        st.dataframe(tasks_df, use_container_width=True)
                    else:
                        st.info("暂无任务")


def export_data():
    """导出数据到 Excel"""
    
    # 检查是否有数据可以导出
    has_data = (st.session_state.org_data or 
                st.session_state.projects_data or 
                st.session_state.tasks_data)
    
    if not has_data:
        return
    
    st.markdown("---")
    st.subheader("📥 导出数据")
    
    if st.button("📊 生成 Excel 文件", use_container_width=True):
        with st.spinner("生成 Excel 文件中..."):
            df_list = []
            sheet_names = []
            
            # 企业信息
            if st.session_state.org_data:
                org_df = pd.DataFrame([st.session_state.org_data])
                df_list.append(org_df)
                sheet_names.append("企业信息")
            
            # 项目列表
            if st.session_state.projects_data:
                projects_df = pd.DataFrame(st.session_state.projects_data)
                df_list.append(projects_df)
                sheet_names.append("项目列表")
            
            # 任务数据（每个项目一个 sheet）
            if st.session_state.tasks_data:
                for project_id, data in st.session_state.tasks_data.items():
                    tasks = data['tasks']
                    project_name = data['name']
                    if tasks:
                        tasks_df = pd.DataFrame(tasks)
                        # 限制 sheet 名称长度
                        sheet_name = f"任务-{project_name[:20]}"
                        df_list.append(tasks_df)
                        sheet_names.append(sheet_name)
            
            # 生成 Excel
            if df_list:
                excel_data = to_excel(df_list, sheet_names)
                
                # 下载按钮
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"teambition_data_{timestamp}.xlsx"
                
                st.download_button(
                    label="⬇️ 下载 Excel 文件",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                st.success(f"✅ 文件生成成功: {filename}")
            else:
                st.warning("没有数据可以导出")


def main():
    """主函数"""
    # 侧边栏
    sidebar()
    
    # 主页面
    main_page()
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888;'>
        Teambition API Tool | Built with Streamlit
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
