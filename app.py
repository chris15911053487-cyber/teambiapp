#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teambition API Web 应用
使用 Streamlit 构建图形界面
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv
from config_sidebar import get_app_token
from streamlit_extras.card import card
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="Teambition 数据工作台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://open.teambition.com',
        'Report a bug': "https://github.com/your-repo/issues",
        'About': "# Teambition API Tool"
    }
)

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #0f172a; margin-bottom: 0.35rem; }
    .subtle { color: #64748b; font-size: 0.95rem; margin-bottom: 1.25rem; }
    .hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #3b82f6 100%);
        color: #fff;
        border-radius: 14px;
        padding: 1.35rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 10px 30px rgba(37, 99, 235, 0.22);
    }
    .hero h1 { margin: 0; font-size: 1.65rem; font-weight: 700; letter-spacing: -0.02em; }
    .hero p { margin: 0.45rem 0 0 0; opacity: 0.92; font-size: 0.98rem; }
    .panel {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        background: #f8fafc;
        margin-bottom: 0.75rem;
    }
    .card {
        border-radius: 12px;
        padding: 18px;
        margin: 10px 0;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
        border: 1px solid #e2e8f0;
        background: #fff;
    }
    div[data-testid="stTabs"] button { font-weight: 600; }
</style>
""", unsafe_allow_html=True)



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

    @staticmethod
    def project_query_next_token(result: dict):
        """解析「查询项目」响应中的下一页游标（兼容多种字段名）。"""
        if not result:
            return None
        return (
            result.get("nextPageToken")
            or result.get("next_page_token")
            or result.get("nextToken")
        )

    def query_projects_page(self, page_size: int = 50, page_token=None):
        """
        单次调用「查询项目」。
        Teambition Open API v3 的 /v3/project/query 使用 pageToken / nextPageToken 游标分页；
        使用 page 数字分页在多数环境下会被忽略，导致每页都返回同一批数据，表现为页数暴涨、条数重复。
        """
        params: dict = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return self._request("GET", "/v3/project/query", params=params)

    def get_projects(self, page_size: int = 50):
        """获取全部项目（游标分页，直至无 nextPageToken）。"""
        all_projects = []
        page_token = None
        prev_first_id = None

        while True:
            result = self.query_projects_page(page_size, page_token)
            projects = result.get("result") or []

            if projects:
                first_id = projects[0].get("id")
                if prev_first_id is not None and first_id == prev_first_id:
                    raise RuntimeError(
                        "分页异常：连续两页首条项目 ID 相同，疑似接口未正确翻页（请勿仅使用 page 数字）。"
                        "已中止，请检查是否使用 nextPageToken / pageToken。"
                    )
                prev_first_id = first_id

            all_projects.extend(projects)
            page_token = self.project_query_next_token(result)
            if not page_token:
                break

        return all_projects
    
    def get_project_tasks(self, project_id: str, page_size: int = 50):
        """获取项目任务（游标分页，与查询项目一致）。"""
        all_tasks = []
        page_token = None
        prev_first_id = None

        while True:
            params = {"pageSize": page_size}
            if page_token:
                params["pageToken"] = page_token
            result = self._request("GET", f"/v3/project/{project_id}/task/query", params=params)
            tasks = result.get("result") or []
            if tasks:
                first_id = tasks[0].get("id")
                if prev_first_id is not None and first_id == prev_first_id:
                    raise RuntimeError(
                        "任务分页异常：连续两批首条任务 ID 相同，疑似未正确翻页。"
                    )
                prev_first_id = first_id
            all_tasks.extend(tasks)
            page_token = self.project_query_next_token(result)
            if not page_token:
                break

        return all_tasks
    
    def get_task_worktime(self, task_id: str):
        """获取任务工时"""
        result = self._request("GET", f"/worktime/aggregation/task/{task_id}")
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


def app_menu():
    """侧边栏主导航"""
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center;padding:0.25rem 0 0.75rem 0;'>"
            "<div style='font-size:1.15rem;font-weight:700;color:#1e40af;'>Teambition</div>"
            "<div style='color:#64748b;font-size:0.85rem;margin-top:2px;'>数据工作台</div></div>",
            unsafe_allow_html=True,
        )

        selected = option_menu(
            menu_title="导航",
            options=["工作台", "数据", "配置", "关于"],
            icons=["house", "bar-chart", "gear", "info-circle"],
            menu_icon="window-sidebar",
            default_index=0,
            styles={
                "container": {"padding": "6px 4px", "border-radius": "12px", "background-color": "#f1f5f9"},
                "icon": {"color": "#2563eb", "font-size": "18px"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "4px 0",
                    "padding": "10px 14px",
                },
                "nav-link-selected": {"background-color": "#2563eb", "color": "white"},
            },
        )

        st.markdown("---")
        st.caption("连接状态")
        has_token = "已配置" if st.session_state.get("token") else "未配置"
        has_tenant = "已填写" if st.session_state.get("tenant_id") else "未填写"
        st.markdown(f"**Token**：{has_token}  \n**企业 ID**：{has_tenant}")

    return selected


def config_page():
    """配置页面"""
    st.markdown('<h1 class="main-header">⚙️ 应用配置</h1>', unsafe_allow_html=True)
    st.markdown("在此页面配置 App ID、App Secret、Access Token 和企业 ID。")

    # 固定配置值（不显示给用户）
    app_id = "69c9def37c12e5933cd9ca4f"
    app_secret = "x6FKGCHbRhc9rmZEMMzRHjVVNTNe6Vfo"
    tenant_id = "5e2558954f68db000132597c"
    
    # 保存到 session state
    st.session_state['app_id'] = app_id
    st.session_state['app_secret'] = app_secret
    st.session_state['tenant_id'] = tenant_id

    # 使用 form 来处理暗号验证和 token 获取
    with st.form(key='password_form'):
        st.markdown("### 请输入暗号")
        password = st.text_input("暗号", type="password")
        submit_button = st.form_submit_button("验证并获取 Token")
        
        if submit_button:
            # 验证暗号
            import datetime
            today = datetime.datetime.now().strftime("%Y%m%d")
            if password == today:
                with st.spinner("获取 Token 中..."):
                    try:
                        token = get_app_token(app_id, app_secret)
                        st.session_state['token'] = token
                        st.success("✅ Token 获取成功!")
                        st.caption("以下为完整 Access Token，可全选复制：")
                        st.code(token, language=None)
                    except Exception as e:
                        st.error(f"❌ 错误: {e}")
            else:
                st.error("❌ 暗号错误，请重新输入")

    st.markdown("---")
    st.subheader("📊 当前配置状态")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Access Token", "已设置" if st.session_state.get('token') else "未设置")
    with col2:
        st.metric("企业 ID", tenant_id or "未设置")
    with col3:
        st.metric("App ID", app_id[:10] + "..." if app_id else "未设置")
    with col4:
        st.metric("App Secret", "已设置" if app_secret else "未设置")

    style_metric_cards()


def about_page():
    """关于页面"""
    st.markdown('<h1 class="main-header">📘 关于 Teambition API 工具</h1>', unsafe_allow_html=True)
    st.markdown("这是一个基于 Streamlit 的 Teambition API 数据工具，支持获取企业、项目和任务数据，并导出 Excel。")

    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            card(
                title="🚀 主要功能",
                text="获取企业信息、项目列表和任务数据，并导出 Excel",
                image="",
                url=""
            )

        with col2:
            card(
                title="⚙️ 配置管理",
                text="独立配置页面，便于管理 API 凭证",
                image="",
                url=""
            )

    st.markdown("---")
    st.markdown("**使用说明**")
    st.markdown("""
    1. 先进入"配置"页面配置凭证。
    2. 切换到"数据"页面获取企业信息和项目数据。
    3. 点击导出生成 Excel 文件。
    """)

    st.markdown("---")
    st.markdown("**技术栈**")
    tech_col1, tech_col2, tech_col3 = st.columns(3)
    with tech_col1:
        st.markdown("**前端**: Streamlit")
    with tech_col2:
        st.markdown("**后端**: Python")
    with tech_col3:
        st.markdown("**数据**: Pandas, OpenPyXL")


def main_page():
    """数据主页面：操作、项目拉取、展示与导出分区"""

    st.info("**使用提示**：请先在侧边栏选择「配置」，输入当日暗号并获取 Token。")

    client = get_api_client()
    if not client:
        st.warning("⚠️ 请先在「配置」中完成 Token 与企业 ID（已内置默认值）。")
        st.markdown(
            """
            **配置步骤**
            1. 打开「配置」页面  
            2. 输入当日暗号（格式 `YYYYMMDD`）并获取 Token  
            3. 返回本页开始拉取数据  
            """
        )
        return

    fetch_org = False
    fetch_projects = False
    fetch_all = False
    fetch_worktime = False

    if "show_projects_ui" not in st.session_state:
        st.session_state.show_projects_ui = False
    if "confirm_projects_fetch" not in st.session_state:
        st.session_state.confirm_projects_fetch = False
    if "projects_estimated_pages" not in st.session_state:
        st.session_state.projects_estimated_pages = 0
    if "projects_data" not in st.session_state:
        st.session_state.projects_data = None
    if "projects_analysis_ready" not in st.session_state:
        st.session_state.projects_analysis_ready = False
    if "projects_analysis_api_response" not in st.session_state:
        st.session_state.projects_analysis_api_response = None

    st.markdown(
        """
        <div class="hero">
            <h1>Teambition 数据工作台</h1>
            <p>企业 · 项目 · 任务 · 工时 · Excel 导出</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_ops, tab_data, tab_export = st.tabs(["操作面板", "数据展示", "导出 Excel"])

    with tab_ops:
        st.markdown('<p class="subtle">先拉取企业/项目，再拉任务；「获取全部数据」会依次拉取企业、全部项目、全部任务与工时。</p>', unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("获取全部数据", use_container_width=True, type="primary"):
                fetch_all = True
        with b2:
            st.caption("导出请切换到「导出 Excel」标签页。")

        st.markdown("#### 分步获取")
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.markdown('<div class="panel"><strong>企业信息</strong><br/><span style="color:#64748b;font-size:0.9rem;">企业档案与基础字段</span></div>', unsafe_allow_html=True)
            if st.button("拉取企业信息", key="fetch_org_card", use_container_width=True):
                fetch_org = True
        with r1c2:
            st.markdown('<div class="panel"><strong>项目列表</strong><br/><span style="color:#64748b;font-size:0.9rem;">游标分页，可先预估再整表拉取</span></div>', unsafe_allow_html=True)
            if st.button("项目清单向导", key="fetch_projects_card", use_container_width=True):
                st.session_state.show_projects_ui = True
                st.session_state.confirm_projects_fetch = False
                st.session_state.projects_analysis_ready = False
                st.session_state.projects_analysis_api_response = None
                st.session_state.projects_estimated_pages = 0

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.markdown('<div class="panel"><strong>任务详情</strong><br/><span style="color:#64748b;font-size:0.9rem;">需先有项目列表，再按项目拉任务</span></div>', unsafe_allow_html=True)
            if st.button("拉取全部项目任务", key="fetch_tasks_card", use_container_width=True):
                fetch_all = True
        with r2c2:
            st.markdown('<div class="panel"><strong>工时统计</strong><br/><span style="color:#64748b;font-size:0.9rem;">依赖已拉取的任务数据</span></div>', unsafe_allow_html=True)
            if st.button("拉取工时", key="fetch_worktime_card", use_container_width=True):
                fetch_worktime = True
    
        # 项目清单获取专门界面
        if st.session_state.show_projects_ui:
            st.markdown("""
            <div style="border-radius: 16px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 30px;">
                <h2 style="color: #1e293b; margin-top: 0; margin-bottom: 20px;">📂 项目清单获取</h2>
            </div>
            """, unsafe_allow_html=True)
            
            if not st.session_state.confirm_projects_fetch:
                st.markdown("### 📊 分析预估")
                
                # 先获取第一页来估算总页数（结果写入 session_state；确认按钮必须在 if analyze_btn 之外渲染，否则点击确认时 analyze_btn 为 False，按钮不在树上，点击无效）
                col1, col2 = st.columns([1, 1])
                with col1:
                    analyze_btn = st.button("开始分析", type="primary", use_container_width=True, key="projects_start_analyze")
                
                if analyze_btn:
                    with st.spinner("分析中..."):
                        try:
                            first_page = client.query_projects_page(50, None)
                            total = (
                                first_page.get("total")
                                or first_page.get("totalSize")
                                or first_page.get("total_size")
                                or 0
                            )
                            if total:
                                total = int(total)
                            projects = first_page.get("result", [])
                            if total > 0:
                                estimated_pages = (total + 50 - 1) // 50
                            elif len(projects) > 0:
                                # 接口未给 total 时无法预估总页数；旧版写死 10 页会误导（实际可能上百页）
                                estimated_pages = None
                            else:
                                estimated_pages = 1
                            st.session_state.projects_estimated_pages = estimated_pages
                            st.session_state.projects_analysis_api_response = first_page
                            st.session_state.projects_analysis_ready = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 分析失败: {e}")
                            with st.expander("🔍 查看错误详情"):
                                st.exception(e)
                            if st.button("重试", key="projects_retry_analyze", use_container_width=True):
                                st.rerun()
                
                if st.session_state.projects_analysis_ready and st.session_state.projects_analysis_api_response is not None:
                    first_page = st.session_state.projects_analysis_api_response
                    projects = first_page.get("result", [])
                    estimated_pages = st.session_state.projects_estimated_pages
                    total = (
                        first_page.get("total")
                        or first_page.get("totalSize")
                        or first_page.get("total_size")
                        or 0
                    )
                    if total:
                        total = int(total)
                    with st.expander("🔍 查看API响应详情"):
                        st.json(first_page)
                    if not total and len(projects) > 0:
                        st.info(
                            "💡 **API 未返回总条数**时无法预估批次数；项目列表使用 **nextPageToken 游标**翻页，"
                            "直至响应中无下一页令牌为止（与「每页是否满 50 条」无必然关系）。"
                        )
                    st.success("✅ 分析完成！")
                    pages_line = (
                        f"<p style=\"margin: 5px 0;\"><strong>预估总页数：</strong>{estimated_pages} 页</p>"
                        if estimated_pages is not None
                        else (
                            "<p style=\"margin: 5px 0;\"><strong>预估总页数：</strong>未知（接口未返回总数；"
                            "将按游标拉取直至无 nextPageToken）</p>"
                        )
                    )
                    st.markdown(f"""
                    <div style="border: 1px solid #86efac; border-radius: 8px; padding: 15px; margin: 15px 0;">
                        <h4 style="color: #166534; margin-top: 0; margin-bottom: 10px;">📋 预估信息</h4>
                        <p style="margin: 5px 0;"><strong>第一页项目数：</strong>{len(projects)} 个</p>
                        {pages_line}
                        <p style="margin: 5px 0;"><strong>每页数据量：</strong>50 个项目</p>
                    </div>
                    """, unsafe_allow_html=True)
                    col_confirm, col_cancel = st.columns([1, 1])
                    with col_confirm:
                        if st.button("✅ 确认开始获取", type="primary", use_container_width=True, key="projects_confirm_fetch"):
                            st.session_state.confirm_projects_fetch = True
                            st.rerun()
                    with col_cancel:
                        if st.button("❌ 取消", use_container_width=True, key="projects_cancel_analysis"):
                            st.session_state.show_projects_ui = False
                            st.session_state.projects_analysis_ready = False
                            st.session_state.projects_analysis_api_response = None
                            st.rerun()
                elif not analyze_btn:
                    st.info("💡 点击\"开始分析\"按钮，系统会先获取第一页数据来预估需要调用的接口次数")
                    if st.button("返回主界面", use_container_width=True, key="projects_back_before_analyze"):
                        st.session_state.show_projects_ui = False
                        st.session_state.projects_analysis_ready = False
                        st.session_state.projects_analysis_api_response = None
                        st.rerun()
            
            if st.session_state.confirm_projects_fetch:
                # 检查是否已经有获取结果
                if st.session_state.projects_data is None or len(st.session_state.projects_data) == 0:
                    st.markdown("### 🔄 获取进度")
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        all_projects = []
                        page_token = None
                        batch = 0
                        estimated_pages = st.session_state.projects_estimated_pages
                        prev_first_id = None
    
                        while True:
                            batch += 1
                            if estimated_pages:
                                status_text.text(f"正在获取第 {batch} / 约 {estimated_pages} 批（游标分页）…")
                            else:
                                status_text.text(f"正在获取第 {batch} 批（游标分页，无 nextPageToken 即结束）…")
    
                            result = client.query_projects_page(50, page_token)
                            projects = result.get("result") or []
                            if projects:
                                first_id = projects[0].get("id")
                                if prev_first_id is not None and first_id == prev_first_id:
                                    raise RuntimeError(
                                        "分页异常：连续两批首条项目相同，疑似未正确使用游标翻页。"
                                        "若曾出现数百「页」而实际项目仅数百个，多为旧版误用 page 参数导致重复拉取。"
                                    )
                                prev_first_id = first_id
    
                            all_projects.extend(projects)
    
                            if estimated_pages and estimated_pages > 0:
                                progress = min(batch / estimated_pages, 0.95)
                            else:
                                progress = min(0.95, batch / (batch + 1))
                            progress_bar.progress(progress)
    
                            page_token = TeambitionAPI.project_query_next_token(result)
                            if not page_token:
                                break
                        
                        st.session_state.projects_data = all_projects
                        progress_bar.progress(1.0)
                        status_text.text("✅ 获取完成！")
                        st.success(f"✅ 成功获取 {len(all_projects)} 个项目！")
                        st.rerun()  # 重新渲染以显示表格
                    
                    except Exception as e:
                        st.error(f"❌ 获取失败: {e}")
                        with st.expander("🔍 查看错误详情"):
                            st.exception(e)
                        if st.button("重试", use_container_width=True):
                            st.rerun()
                        if st.button("返回主界面", key="projects_fetch_err_back", use_container_width=True):
                            st.session_state.show_projects_ui = False
                            st.session_state.confirm_projects_fetch = False
                            st.session_state.projects_analysis_ready = False
                            st.session_state.projects_analysis_api_response = None
                            st.rerun()
                else:
                    # 显示获取结果和分页表格
                    all_projects = st.session_state.projects_data
                    st.success(f"✅ 成功获取 {len(all_projects)} 个项目！")
                    
                    # 分页表格显示
                    st.markdown("### 📊 项目列表（分页显示）")
                    
                    # 初始化分页状态
                    if 'projects_page' not in st.session_state:
                        st.session_state.projects_page = 0
                    
                    # 分页控制
                    total_pages = (len(all_projects) + 49) // 50
                    col_prev, col_info, col_next = st.columns([1, 2, 1])
                    
                    with col_prev:
                        if st.session_state.projects_page > 0:
                            if st.button("⬅️ 上一页", key="prev_page", use_container_width=True):
                                st.session_state.projects_page -= 1
                                st.rerun()
                    
                    with col_info:
                        st.markdown(f"""<div style='text-align: center; color: #64748b;'>
                            <strong>第 {st.session_state.projects_page + 1} 页 / 共 {total_pages} 页</strong><br>
                            <small>每页显示 50 个项目，共 {len(all_projects)} 个项目</small>
                        </div>""", unsafe_allow_html=True)
                    
                    with col_next:
                        if st.session_state.projects_page < total_pages - 1:
                            if st.button("➡️ 下一页", key="next_page", use_container_width=True):
                                st.session_state.projects_page += 1
                                st.rerun()
                    
                    # 显示当前页的数据
                    start_idx = st.session_state.projects_page * 50
                    end_idx = min(start_idx + 50, len(all_projects))
                    current_page_projects = all_projects[start_idx:end_idx]
                    
                    # 转换为DataFrame并显示主要列
                    import pandas as pd
                    
                    # 提取主要列
                    project_data = []
                    for idx, project in enumerate(current_page_projects):
                        project_data.append({
                            '序号': start_idx + idx + 1,
                            '项目ID': project.get('id', ''),
                            '项目名称': project.get('name', '未命名'),
                            '项目状态': project.get('status', '未知'),
                            '创建时间': project.get('created', ''),
                            '负责人': project.get('ownerId', '')
                        })
                    
                    if project_data:
                        df = pd.DataFrame(project_data)
                        
                        # 设置表格样式
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                '序号': st.column_config.NumberColumn(width='small'),
                                '项目ID': st.column_config.TextColumn(width='medium'),
                                '项目名称': st.column_config.TextColumn(width='large'),
                                '项目状态': st.column_config.TextColumn(width='small'),
                                '创建时间': st.column_config.TextColumn(width='medium'),
                                '负责人': st.column_config.TextColumn(width='medium')
                            }
                        )
                    
                    # 返回按钮
                    if st.button("返回主界面", type="primary", use_container_width=True, key="projects_done_back"):
                        st.session_state.show_projects_ui = False
                        st.session_state.confirm_projects_fetch = False
                        st.session_state.projects_page = 0
                        st.session_state.projects_data = None
                        st.session_state.projects_analysis_ready = False
                        st.session_state.projects_analysis_api_response = None
                        st.rerun()
        
    # 数据存储
    if 'org_data' not in st.session_state:
        st.session_state.org_data = None
    if 'projects_data' not in st.session_state:
        st.session_state.projects_data = None
    if 'tasks_data' not in st.session_state:
        st.session_state.tasks_data = {}
    if 'worktime_data' not in st.session_state:
        st.session_state.worktime_data = {}
    
    # 获取企业信息
    if fetch_org or fetch_all:
        with st.spinner("获取企业信息中..."):
            try:
                org_info = client.get_org_info()
                st.session_state.org_data = org_info.get('result', {})
                st.success("✅ 企业信息获取成功!")
            except Exception as e:
                st.error(f"❌ 错误: {e}")
    
    # 获取项目列表（只在fetch_all时直接获取）
    if fetch_all:
        with st.spinner("获取项目列表中..."):
            try:
                projects = client.get_projects(page_size=50)
                st.session_state.projects_data = projects
                st.success(f"✅ 找到 {len(projects)} 个项目!")
                if len(projects) > 50:
                    st.info(f"💡 为了避免界面卡顿，在数据展示中只显示前 50 个项目。")
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
    
    # 获取工时信息
    if fetch_worktime or fetch_all:
        if st.session_state.tasks_data:
            worktime_data = {}
            total_tasks = sum(len(t['tasks']) for t in st.session_state.tasks_data.values())
            current_task = 0
            progress_bar = st.progress(0)
            
            for project_id, project_data in st.session_state.tasks_data.items():
                project_name = project_data['name']
                tasks = project_data['tasks']
                
                for task in tasks:
                    task_id = task.get('id')
                    task_name = task.get('name', '未命名')
                    
                    try:
                        worktime = client.get_task_worktime(task_id)
                        if worktime:
                            worktime_data[task_id] = {
                                'project_name': project_name,
                                'task_name': task_name,
                                'worktime': worktime
                            }
                    except Exception as e:
                        pass  # 忽略工时获取失败的情况
                    
                    current_task += 1
                    progress_bar.progress(current_task / total_tasks)
            
            st.session_state.worktime_data = worktime_data
            st.success(f"✅ 共获取 {len(worktime_data)} 个任务的工时信息!")
            progress_bar.empty()
        else:
            st.warning("⚠️ 请先获取任务数据，再获取工时信息")
    
    with tab_data:
        display_data()
    with tab_export:
        export_data()


def display_data():
    """显示获取的数据"""

    # 检查是否有数据
    has_data = (st.session_state.org_data or
                st.session_state.projects_data or
                st.session_state.tasks_data or
                st.session_state.worktime_data)

    if not has_data:
        st.info("ℹ️ 暂无数据，请先获取数据")
        return

    st.markdown("---")
    st.subheader("📊 数据展示")

    # 显示企业信息
    if st.session_state.org_data:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

    # 显示项目列表
    if st.session_state.projects_data:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"### 📁 项目列表 (共 {len(st.session_state.projects_data)} 个)")

            # 转换为 DataFrame 显示
            projects_df = pd.DataFrame(st.session_state.projects_data)
            if not projects_df.empty:
                total_projects = len(projects_df)
                st.markdown(f"**项目总数**: {total_projects} 个")
                st.markdown(f"**显示**: 前 50 个项目")
                
                # 只显示前50个项目
                display_df = projects_df.head(50)
                
                display_cols = ['name', 'status', 'created', 'id']
                available_cols = [c for c in display_cols if c in display_df.columns]
                st.dataframe(display_df[available_cols], use_container_width=True,
                           column_config={
                               "name": st.column_config.TextColumn("项目名称", width="medium"),
                               "status": st.column_config.TextColumn("项目状态", width="small"),
                               "created": st.column_config.TextColumn("创建时间", width="medium"),
                               "id": st.column_config.TextColumn("项目ID", width="small")
                           })
                if total_projects > 50:
                    st.info(f"💡 为了避免界面卡顿，只显示了前 50 个项目。导出 Excel 时会包含所有 {total_projects} 个项目。")
            st.markdown('</div>', unsafe_allow_html=True)

    # 显示项目任务
    if st.session_state.tasks_data:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

    # 显示工时信息
    if st.session_state.worktime_data:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"### ⏱️ 工时信息 (共 {len(st.session_state.worktime_data)} 个任务)")
            
            # 转换为 DataFrame 显示
            worktime_list = []
            for task_id, data in st.session_state.worktime_data.items():
                for worktime_item in data['worktime']:
                    worktime_list.append({
                        '项目名称': data['project_name'],
                        '任务名称': data['task_name'],
                        '对象ID': worktime_item.get('objectId', 'N/A'),
                        '对象类型': worktime_item.get('objectType', 'N/A'),
                        '工时(毫秒)': worktime_item.get('worktime', 0),
                        '记录数量': worktime_item.get('count', 0)
                    })
            
            if worktime_list:
                worktime_df = pd.DataFrame(worktime_list)
                st.dataframe(worktime_df, use_container_width=True)
            else:
                st.info("📝 暂无工时信息")
            st.markdown('</div>', unsafe_allow_html=True)


def export_data():
    """导出数据到 Excel"""

    # 检查是否有数据可以导出
    has_data = (st.session_state.org_data or
                st.session_state.projects_data or
                st.session_state.tasks_data or
                st.session_state.worktime_data)

    if not has_data:
        st.info("ℹ️ 暂无数据可以导出，请先获取数据")
        return

    st.markdown("---")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📥 数据导出")

    # 显示数据统计
    with st.container():
        st.markdown("### 📈 数据统计")
        col1, col2, col3, col4, col5 = st.columns(5)

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
            worktime_count = len(st.session_state.worktime_data) if st.session_state.worktime_data else 0
            st.metric("工时记录", f"{worktime_count} 个")

        with col5:
            base_sheets = has_org + (1 if st.session_state.projects_data else 0)
            task_sheets = len([data for data in st.session_state.tasks_data.values() if data['tasks']])
            worktime_sheets = 1 if st.session_state.worktime_data else 0
            sheet_count = base_sheets + task_sheets + worktime_sheets
            st.metric("Excel工作表", f"{sheet_count} 个")

        style_metric_cards()

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
                # 只保留需要的字段
                desired_cols = ['name', 'status', 'created', 'id']
                available_cols = [c for c in desired_cols if c in projects_df.columns]
                projects_df = projects_df[available_cols]
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

            # 工时信息
            if st.session_state.worktime_data:
                worktime_list = []
                for task_id, data in st.session_state.worktime_data.items():
                    for worktime_item in data['worktime']:
                        worktime_list.append({
                            '项目名称': data['project_name'],
                            '任务名称': data['task_name'],
                            '对象ID': worktime_item.get('objectId', 'N/A'),
                            '对象类型': worktime_item.get('objectType', 'N/A'),
                            '工时(毫秒)': worktime_item.get('worktime', 0),
                            '记录数量': worktime_item.get('count', 0)
                        })
                if worktime_list:
                    worktime_df = pd.DataFrame(worktime_list)
                    df_list.append(worktime_df)
                    sheet_names.append("工时信息")

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
    st.markdown('</div>', unsafe_allow_html=True)





def main():
    """主函数"""
    page = app_menu()

    if page == "配置":
        config_page()
    elif page == "关于":
        about_page()
    elif page in ("工作台", "数据"):
        main_page()
    else:
        main_page()

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888;'>
        Teambition API Tool | Built with Streamlit
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
