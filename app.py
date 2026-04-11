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
from config_sidebar import sidebar

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


def main_page():
    """主页面"""
    st.title("📊 Teambition API 工具")
    st.markdown("获取企业信息、项目列表和任务数据，并导出到 Excel")

    # 欢迎信息和说明
    st.info("💡 **使用提示**: 请先在左侧边栏配置 API 凭证，然后点击下方按钮获取数据")

    # 检查配置
    client = get_api_client()
    if not client:
        st.warning("⚠️ 请在左侧边栏配置 Token 和企业 ID")
        st.markdown("""
        ### 配置步骤:
        1. 输入您的 App ID 和 App Secret
        2. 点击"获取 Token"按钮
        3. 或者直接输入已有的 Access Token
        4. 输入企业 ID (Tenant ID)
        """)
        return

    # 状态指示器
    st.success("✅ API 配置完成，可以开始获取数据")

    # 操作按钮区域
    st.markdown("---")
    st.subheader("🚀 数据获取操作")

    # 操作按钮 - 使用更好的布局
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🏢 企业信息**")
        st.markdown("获取当前企业的基本信息")
        fetch_org = st.button("获取企业信息", use_container_width=True, key="fetch_org")

    with col2:
        st.markdown("**📁 项目列表**")
        st.markdown("获取企业下的所有项目")
        fetch_projects = st.button("获取项目列表", use_container_width=True, key="fetch_projects")

    with col3:
        st.markdown("**🚀 全部数据**")
        st.markdown("获取企业信息、项目和所有任务")
        fetch_all = st.button("获取全部数据", use_container_width=True, type="primary", key="fetch_all")
    
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

    # 检查是否有数据
    has_data = (st.session_state.org_data or
                st.session_state.projects_data or
                st.session_state.tasks_data)

    if not has_data:
        st.info("ℹ️ 暂无数据，请先获取数据")
        return

    st.markdown("---")
    st.subheader("📊 数据展示")

    # 显示企业信息
    if st.session_state.org_data:
        with st.container():
            st.markdown("### 🏢 企业信息")
            org = st.session_state.org_data

            # 使用卡片式布局
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("企业名称", org.get('name', 'N/A'))
            with col2:
                st.metric("企业 ID", org.get('orgId', 'N/A'))
            with col3:
                st.metric("创建时间", org.get('created', 'N/A'))

            with st.expander("📋 查看完整企业信息"):
                st.json(org)

    # 显示项目列表
    if st.session_state.projects_data:
        with st.container():
            st.markdown(f"### 📁 项目列表 (共 {len(st.session_state.projects_data)} 个)")

            # 转换为 DataFrame 显示
            projects_df = pd.DataFrame(st.session_state.projects_data)
            if not projects_df.empty:
                display_cols = ['name', 'description', 'created', 'id']
                available_cols = [c for c in display_cols if c in projects_df.columns]
                st.dataframe(projects_df[available_cols], use_container_width=True,
                           column_config={
                               "name": st.column_config.TextColumn("项目名称", width="medium"),
                               "description": st.column_config.TextColumn("描述", width="large"),
                               "created": st.column_config.TextColumn("创建时间", width="medium"),
                               "id": st.column_config.TextColumn("项目ID", width="small")
                           })

    # 显示项目任务
    if st.session_state.tasks_data:
        with st.container():
            total_tasks = sum(len(data['tasks']) for data in st.session_state.tasks_data.values())
            st.markdown(f"### 📋 项目任务详情 (共 {total_tasks} 个任务)")

            for project_id, data in st.session_state.tasks_data.items():
                project_name = data['name']
                tasks = data['tasks']

                with st.expander(f"📂 {project_name} ({len(tasks)} 个任务)"):
                    if tasks:
                        tasks_df = pd.DataFrame(tasks)
                        # 选择要显示的列
                        task_cols = ['name', 'content', 'executor', 'stage', 'created', 'updated']
                        available_task_cols = [c for c in task_cols if c in tasks_df.columns]
                        st.dataframe(tasks_df[available_task_cols], use_container_width=True)
                    else:
                        st.info("📝 此项目暂无任务")


def export_data():
    """导出数据到 Excel"""

    # 检查是否有数据可以导出
    has_data = (st.session_state.org_data or
                st.session_state.projects_data or
                st.session_state.tasks_data)

    if not has_data:
        st.info("ℹ️ 暂无数据可以导出，请先获取数据")
        return

    st.markdown("---")
    st.subheader("📥 数据导出")

    # 显示数据统计
    with st.container():
        st.markdown("### 📈 数据统计")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            has_org = 1 if st.session_state.org_data else 0
            st.metric("企业信息", f"{has_org} 条")

        with col2:
            project_count = len(st.session_state.projects_data) if st.session_state.projects_data else 0
            st.metric("项目数量", f"{project_count} 个")

        with col3:
            task_count = sum(len(data['tasks']) for data in st.session_state.tasks_data.values()) if st.session_state.tasks_data else 0
            st.metric("任务总数", f"{task_count} 个")

        with col4:
            sheet_count = has_org + (1 if st.session_state.projects_data else 0) + len([data for data in st.session_state.tasks_data.values() if data['tasks']])
            st.metric("Excel工作表", f"{sheet_count} 个")

    # 导出按钮
    if st.button("📊 生成并下载 Excel 文件", use_container_width=True, type="primary"):
        with st.spinner("正在生成 Excel 文件..."):
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
                        # 限制 sheet 名称长度，避免特殊字符
                        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        sheet_name = f"任务-{safe_name[:15]}" if safe_name else f"任务-{project_id[:8]}"
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

                st.success(f"✅ Excel 文件生成成功!")
                st.info(f"📁 文件名: {filename}")
                st.info(f"📊 包含 {len(df_list)} 个工作表: {', '.join(sheet_names)}")
            else:
                st.warning("⚠️ 没有有效数据可以导出")


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
