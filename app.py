#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teambition API Web 应用
使用 Streamlit 构建图形界面
"""

import json
import re
import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from datetime import datetime
from io import BytesIO
from urllib.parse import urlencode
from dotenv import load_dotenv
from config_sidebar import apply_company_to_session, get_app_token, COMPANY_PROFILES
from streamlit_extras.card import card
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

# 加载环境变量
load_dotenv()


def _build_curl_from_request(req: dict) -> str:
    """生成可粘贴到 Postman（Import > Raw text）的 cURL。"""
    method = req.get("method", "GET")
    full_h = req.get("headers_full") or req.get("headers") or {}
    params = req.get("params") or {}
    base = req.get("full_url", "")
    if params:
        q = urlencode(params)
        sep = "&" if "?" in base else "?"
        url = f"{base}{sep}{q}"
    else:
        url = base
    lines = [f"curl -sS -X {method}"]
    for k, v in full_h.items():
        val = str(v).replace("'", "'\\''")
        lines.append(f"  -H '{k}: {val}'")
    lines.append(f"  '{url}'")
    return " \\\n".join(lines)


def format_api_debug_bundle(req: dict) -> str:
    """组装完整调试报文：请求/响应 + cURL，便于 Postman 与人工对照。"""
    lines = [
        "=== Teambition Open API 调试报文 ===",
        f"时间: {req.get('timestamp', '')}",
        "",
        "--- HTTP 请求 ---",
        f"{req.get('method', 'GET')} {req.get('full_url', '')}",
        "",
        "Headers:",
    ]
    full_h = req.get("headers_full") or req.get("headers") or {}
    for k, v in full_h.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    params = req.get("params") or {}
    lines.append("Query 参数:")
    if params:
        for k, v in params.items():
            lines.append(f"  {k}: {v}")
    else:
        lines.append("  (无)")
    lines.extend(["", "--- HTTP 响应 ---"])
    lines.append(f"HTTP 状态码: {req.get('http_status', 'N/A')}")
    lines.append(f"业务 code: {req.get('response_code', req.get('status', 'N/A'))}")
    if req.get("error_message"):
        lines.append(f"errorMessage: {req['error_message']}")
    lines.extend(["", "响应 JSON:"])
    rj = req.get("response_json")
    if rj is not None:
        try:
            lines.append(json.dumps(rj, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            lines.append(str(rj))
    else:
        lines.append("(暂无)")
    lines.extend(["", "--- cURL（Postman：Import → Raw text 粘贴下面整段）---", _build_curl_from_request(req)])
    return "\n".join(lines)


def render_copy_debug_bundle_button(bundle_text: str) -> None:
    """浏览器剪贴板一键复制（无需服务器端 pyperclip）。"""
    js_literal = json.dumps(bundle_text)
    components.html(
        f"""
        <div style="font-family: system-ui, sans-serif;">
            <button type="button"
                style="padding: 0.35rem 0.75rem; cursor: pointer; border-radius: 6px;
                border: 1px solid #2563eb; background: #eff6ff; color: #1e40af; font-size: 13px;"
                onclick="navigator.clipboard.writeText({js_literal}).then(function() {{
                    alert('已复制到剪贴板，可粘贴到 Postman（Import → Raw text）或记事本');
                }}).catch(function() {{
                    alert('复制失败，请改用下方「备用纯文本」全选复制');
                }});"
            >📋 一键复制完整报文</button>
        </div>
        """,
        height=52,
    )


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
    /* 与系统/浏览器深色主题及 Streamlit 暗色主题对齐，避免大块白底 */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-color, #f1f5f9);
        margin-bottom: 0.35rem;
    }
    .subtle {
        color: var(--secondary-text-color, #94a3b8);
        font-size: 0.95rem;
        margin-bottom: 1.25rem;
    }
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
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        background: rgba(30, 41, 59, 0.55);
        margin-bottom: 0.75rem;
    }
    .card {
        border-radius: 12px;
        padding: 18px;
        margin: 10px 0;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
        border: 1px solid #334155;
        background: rgba(30, 41, 59, 0.65);
    }
    div[data-testid="stTabs"] button { font-weight: 600; }
    /* st.metric：避免白底卡片 */
    [data-testid="stMetricContainer"],
    div[data-testid="stMetricContainer"] {
        background-color: rgba(30, 41, 59, 0.85) !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
    }
    [data-testid="stMetricContainer"] [data-testid="stMetricLabel"] p,
    [data-testid="stMetricContainer"] label p {
        color: #94a3b8 !important;
    }
    [data-testid="stMetricContainer"] [data-testid="stMetricValue"] {
        color: #f1f5f9 !important;
    }
    /* 表单 / 子标题在暗色下的可读性 */
    .stMarkdown h2, .stMarkdown h3 { color: var(--text-color, #e2e8f0); }
</style>
""", unsafe_allow_html=True)


# ========================================
# API 配置系统 (新架构核心)
# ========================================

# API 配置 Schema:
# - name: 唯一标识 (用于调用)
# - description: 描述
# - method: GET/POST
# - endpoint: 相对路径 (支持 {projectId} 模板)
# - default_params: 默认 query/body 参数 (dict)
# - resolvers: 参数名 -> resolver 函数名 (动态取值，如 token, project_id, filter builder)
# - response_key: 响应中数据所在键 (通常 "result")
# - pagination: 是否支持游标分页 (nextPageToken 等)

DEFAULT_API_CONFIGS = [
    {
        "name": "get_org_info",
        "description": "获取企业信息",
        "method": "GET",
        "endpoint": "/org/info",
        "default_params": {},
        "resolvers": {},
        "response_key": "result",
        "pagination": False
    },
    {
        "name": "query_projects",
        "description": "查询项目列表 (游标分页)",
        "method": "GET",
        "endpoint": "/v3/project/query",
        "default_params": {"pageSize": 50},
        "resolvers": {
            "pageToken": "from_context"
        },
        "response_key": "result",
        "pagination": True
    },
    {
        "name": "search_project_stages",
        "description": "查询项目阶段 (Kanban列)",
        "method": "GET",
        "endpoint": "/v3/project/{projectId}/stage/search",
        "default_params": {"pageSize": 50},
        "resolvers": {
            "projectId": "from_context"
        },
        "response_key": "result",
        "pagination": True
    },
    {
        "name": "query_tasks",
        "description": "查询任务详情 (支持 filter.projectId)",
        "method": "GET",
        "endpoint": "/v3/task/query",
        "default_params": {"pageSize": 50},
        "resolvers": {
            "filter": "build_task_filter",
            "pageToken": "from_context"
        },
        "response_key": "result",
        "pagination": True
    },
    {
        "name": "get_task_worktime",
        "description": "获取任务工时聚合",
        "method": "GET",
        "endpoint": "/worktime/aggregation/task/{taskId}",
        "default_params": {},
        "resolvers": {
            "taskId": "from_context"
        },
        "response_key": "result",
        "pagination": False
    },
]


def _camel_to_snake(name: str) -> str:
    """projectId -> project_id（用于路径占位符与 query 别名的统一剥离）。"""
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def _merge_snake_to_camel_for_path(context: dict) -> dict:
    """resolve_endpoint 按 key 替换 {{projectId}}；调用侧常传 project_id，需补全 camelCase。"""
    ctx = dict(context)
    if ctx.get("project_id") is not None and "projectId" not in ctx:
        ctx["projectId"] = ctx["project_id"]
    if ctx.get("task_id") is not None and "taskId" not in ctx:
        ctx["taskId"] = ctx["task_id"]
    return ctx


def _strip_query_params_bound_to_path_template(endpoint_template: str, params: dict) -> None:
    """路径中已使用 {{projectId}} 等占位符时，不应再作为 GET query 重复提交。"""
    for raw in re.findall(r"\{([^}]+)\}", endpoint_template):
        keys = {raw}
        snake = _camel_to_snake(raw)
        if snake != raw:
            keys.add(snake)
        for k in keys:
            params.pop(k, None)


def _dedupe_camel_snake_query_aliases(params: dict) -> None:
    """同一语义只保留 Teambition 常用的 camelCase query 键。"""
    for camel, snake in (
        ("projectId", "project_id"),
        ("taskId", "task_id"),
        ("pageToken", "page_token"),
    ):
        if camel in params and snake in params:
            del params[snake]


# Resolver 函数注册表 - 动态解析参数
def resolve_param(resolver_name: str, context: dict, api_config: dict = None):
    """根据 resolver 类型从 context 或 session_state 解析参数值"""
    if resolver_name == "from_context":
        # 从调用上下文获取 (e.g. project_id, pageToken, taskId)
        for key in context:
            if key.lower() in ["projectid", "project_id", "id", "taskid", "task_id", "token", "tenant_id", "pagetoken"]:
                return context.get(key)
        return None
    elif resolver_name == "build_task_filter":
        # 构建 task/query 的 filter JSON
        project_id = context.get("project_id") or context.get("projectId")
        if project_id:
            filter_dict = {"projectId": project_id}
            # 可扩展 stageId 等
            if "stage_id" in context or "stageId" in context:
                filter_dict["stageId"] = context.get("stage_id") or context.get("stageId")
            return json.dumps(filter_dict)
        return json.dumps({"projectId": "all"})  # fallback
    elif resolver_name == "get_token":
        return st.session_state.get("token", "")
    elif resolver_name == "get_tenant_id":
        return st.session_state.get("tenant_id", "")
    return context.get(resolver_name)  # default fallback


# 初始化 session state 中的 API 配置
def init_session_state():
    if "api_configs" not in st.session_state:
        st.session_state.api_configs = DEFAULT_API_CONFIGS.copy()
    if "api_requests" not in st.session_state:
        st.session_state.api_requests = []
    if "org_data" not in st.session_state:
        st.session_state.org_data = None
    if "projects_data" not in st.session_state:
        st.session_state.projects_data = None
    if "tasks_data" not in st.session_state:
        st.session_state.tasks_data = {}
    if "worktime_data" not in st.session_state:
        st.session_state.worktime_data = None
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    # 企业凭证：默认选中首个企业，并将 AppId/Secret/企业ID 写入 session（不在 UI 展示）
    if COMPANY_PROFILES:
        if (
            "selected_company" not in st.session_state
            or st.session_state.get("selected_company") not in COMPANY_PROFILES
        ):
            st.session_state.selected_company = next(iter(COMPANY_PROFILES))
        apply_company_to_session(st.session_state.selected_company)


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
        """统一请求方法，增强权限错误提示 + 可选请求报文记录"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        # 记录请求报文（调试模式）
        if st.session_state.get("debug_mode"):
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            params = kwargs.get("params", {})

            # 脱敏 Authorization（只显示前20字符）
            display_headers = headers.copy()
            if "Authorization" in display_headers:
                auth = display_headers["Authorization"]
                display_headers["Authorization"] = auth[:20] + "..." if len(auth) > 20 else auth

            request_log = {
                "timestamp": timestamp,
                "method": method,
                "endpoint": endpoint,
                "full_url": url,
                "headers": display_headers,
                "headers_full": dict(headers),
                "params": params,
                "status": "pending",
            }

            if 'api_requests' not in st.session_state:
                st.session_state.api_requests = []
            st.session_state.api_requests.insert(0, request_log)
            # 保留最近20条
            if len(st.session_state.api_requests) > 20:
                st.session_state.api_requests = st.session_state.api_requests[:20]

        response = requests.request(method, url, headers=headers, **kwargs)
        try:
            result = response.json()
        except ValueError:
            result = {"_parse_error": "响应非 JSON", "text": response.text[:2000]}

        code = result.get("code") if isinstance(result, dict) else None
        error_message = result.get("errorMessage", "") if isinstance(result, dict) else ""

        # 更新最后一条请求的状态（调试模式）
        if st.session_state.get("debug_mode") and st.session_state.get("api_requests"):
            last_request = st.session_state.api_requests[0]
            last_request["http_status"] = response.status_code
            last_request["status"] = code if code is not None else response.status_code
            last_request["response_code"] = code
            last_request["error_message"] = error_message
            last_request["response_json"] = result if isinstance(result, dict) else {"_raw": str(result)}
            if isinstance(result, dict) and "result" in result:
                last_request["response_summary"] = f"{len(str(result.get('result', '')))} chars"

        if code is not None and code not in [0, 200]:
            # 增强权限错误提示
            if code in [403, 10133] or "permission" in error_message.lower() or "权限" in error_message or "authorization" in error_message.lower():
                error_detail = f"""
API 权限错误: {error_message} (code: {code})

常见原因及解决办法：
1. 在 Teambition 开放平台该应用中，需开启以下权限：
   - 项目自定义列表查看权限 (tb-core:project.stage:list) —— 用于 /stage/search
   - 项目任务查看权限 (tb-core:project.task:list) —— 用于 /task/query
   - 任务相关读取权限
2. 保存权限变更后，**必须重新生成 Token**（重新在「配置」页验证暗号）
3. 确认 X-Tenant-Id 与 Token 所属企业一致
4. 检查项目是否在应用可见范围内
                """.strip()
                raise Exception(error_detail)
            else:
                raise Exception(f"API 错误: {error_message} (code: {code})")

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
        """获取某项目下任务列表（游标分页）。

        统一使用开放平台 ``GET /v3/task/query``，query 中通过 ``filter`` JSON 传入
        ``projectId``，并配合 ``pageSize`` / ``pageToken`` 分页。
        """
        all_tasks = []
        page_token = None
        prev_first_id = None

        while True:
            params = {
                "pageSize": page_size,
                "filter": json.dumps({"projectId": project_id}),
            }
            if page_token:
                params["pageToken"] = page_token
            result = self._request("GET", "/v3/task/query", params=params)
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

    def search_project_stages(self, project_id: str, page_size: int = 50):
        """搜索项目下的任务列表/阶段 (Kanban 列)。
        对应文档：/v3/project/{projectId}/stage/search
        需要权限：tb-core:project.stage:list
        """
        params = {"pageSize": page_size}
        result = self._request("GET", f"/v3/project/{project_id}/stage/search", params=params)
        return result.get("result", [])

    @staticmethod
    def _comma_separated_ids(ids):
        if ids is None:
            return None
        if isinstance(ids, (list, tuple)):
            return ",".join(str(x) for x in ids)
        return str(ids).strip()

    def query_tasks(
        self,
        project_id: str = None,
        page_size: int = 50,
        page_token=None,
        *,
        stage_id: str = None,
        task_ids=None,
        short_ids=None,
        parent_task_id: str = None,
        operator_id: str = None,
    ):
        """任务查询（统一 ``GET /v3/task/query``）。

        - **按项目分页列表**：query 使用 ``filter``（JSON 字符串）包含 ``projectId``，可选
          ``stageId``，以及 ``pageSize`` / ``pageToken``。
        - **按已知任务 ID 查详情**：见
          https://open.teambition.com/docs/apis/6321c6d2912d20d3b5a4a7b8
          —— ``taskId``、``shortIds``、``parentTaskId``（``taskId`` 与 ``parentTaskId`` 二选一），
          不与 ``filter`` 混用。
        可选请求头 ``x-operator-id``（``operator_id``）。
        """
        extra_headers = {"x-operator-id": operator_id} if operator_id else None

        if project_id:
            filter_obj = {"projectId": project_id}
            if stage_id:
                filter_obj["stageId"] = stage_id
            params = {
                "pageSize": page_size,
                "filter": json.dumps(filter_obj),
            }
            if page_token:
                params["pageToken"] = page_token
            req_kwargs = {"params": params}
            if extra_headers:
                req_kwargs["headers"] = extra_headers
            result = self._request("GET", "/v3/task/query", **req_kwargs)
            return result.get("result", []), self.project_query_next_token(result)

        tid = self._comma_separated_ids(task_ids)
        sid = self._comma_separated_ids(short_ids)
        if tid and parent_task_id:
            raise ValueError("官方文档：taskId 与 parentTaskId 不能同时使用")
        if not tid and not sid and not parent_task_id:
            raise ValueError(
                "全局 /v3/task/query 须提供 task_ids、short_ids 或 parent_task_id 之一；"
                "拉取某项目下全部任务请传入 project_id（将使用 filter.projectId 分页）"
            )

        params = {}
        if tid:
            params["taskId"] = tid
        if sid:
            params["shortIds"] = sid
        if parent_task_id:
            params["parentTaskId"] = parent_task_id

        req_kwargs = {"params": params}
        if extra_headers:
            req_kwargs["headers"] = extra_headers
        result = self._request("GET", "/v3/task/query", **req_kwargs)
        # 文档未描述该接口的分页字段；按 ID 查询一般为单次结果
        return result.get("result", []), None

    def get_all_project_tasks(self, projects, page_size: int = 50):
        """获取所有项目的任务（增强版，支持阶段信息）"""
        all_tasks_data = {}
        for project in projects:
            project_id = project.get('id')
            project_name = project.get('name', '未命名')

            try:
                # 先获取该项目的阶段（可选，用于丰富任务展示）
                stages = self.search_project_stages(project_id, page_size)
                stage_map = {s.get('id'): s.get('name', '未命名') for s in stages}

                # 获取任务
                tasks = []
                page_token = None
                while True:
                    page_tasks, next_token = self.query_tasks(
                        project_id=project_id,
                        page_token=page_token,
                        page_size=page_size
                    )
                    tasks.extend(page_tasks)
                    page_token = next_token
                    if not page_token:
                        break

                all_tasks_data[project_id] = {
                    'name': project_name,
                    'tasks': tasks,
                    'stages': stages,
                    'stage_map': stage_map
                }
            except Exception as e:
                # 让上层捕获并显示友好提示
                raise Exception(f"项目 [{project_name}] 任务获取失败: {str(e)}") from e

        return all_tasks_data

    def get_task_worktime(self, task_id: str):
        """获取任务工时"""
        result = self._request("GET", f"/worktime/aggregation/task/{task_id}")
        return result.get("result", [])

    # ====================== 新增：API Registry & Dynamic Call ======================
    def get_config(self, name: str) -> dict:
        """从 session_state 或 DEFAULT 获取 API 配置"""
        configs = st.session_state.get("api_configs", DEFAULT_API_CONFIGS)
        for config in configs:
            if config.get("name") == name:
                return config.copy()
        # Fallback to defaults
        for config in DEFAULT_API_CONFIGS:
            if config.get("name") == name:
                return config.copy()
        raise ValueError(f"未找到 API 配置: {name}")

    def resolve_endpoint(self, endpoint: str, context: dict) -> str:
        """替换 endpoint 中的 {var} 模板 (e.g. {projectId})"""
        for key, value in list(context.items()):
            if value is None:
                continue
            for placeholder in [f"{{{key}}}", f"{{{key.lower()}}}", f"{{{key.upper()}}}"]:
                if placeholder in endpoint:
                    endpoint = endpoint.replace(placeholder, str(value))
        return endpoint

    def call(self, name: str, **context):
        """动态调用配置化的 API (核心方法)
        - 查找配置
        - 使用 resolvers 解析参数 (支持 context 覆盖)
        - 处理 endpoint 模板
        - 调用 _request 并提取 response_key
        - 自动记录调试日志 (通过 _request)
        """
        config = self.get_config(name)
        method = config["method"]
        path_ctx = _merge_snake_to_camel_for_path(context)
        endpoint = self.resolve_endpoint(config["endpoint"], path_ctx)

        # 构建参数 (default + resolved + context override)
        params_or_body = config.get("default_params", {}).copy()
        for param_name, resolver_name in config.get("resolvers", {}).items():
            value = resolve_param(resolver_name, {**path_ctx, "api_name": name}, config)
            if value is not None:
                params_or_body[param_name] = value

        # Context 覆盖 (优先级最高)；不传内部键到 HTTP query/body
        _internal_ctx_keys = frozenset({"api_name", "extract_key"})
        for k, v in context.items():
            if k in _internal_ctx_keys:
                continue
            params_or_body[k] = v

        if method.upper() == "GET":
            _dedupe_camel_snake_query_aliases(params_or_body)
            _strip_query_params_bound_to_path_template(config["endpoint"], params_or_body)

        # 调用 (GET 用 params, 其他用 json body)
        kwargs = {"params": params_or_body} if method.upper() == "GET" else {"json": params_or_body}

        result = self._request(method, endpoint, **kwargs)

        # 返回完整响应 (兼容旧代码 + 测试)；调用者可自行提取 result.get("result")
        # 可通过 context.get("extract_key") 自定义提取
        if isinstance(result, dict) and context.get("extract_key"):
            return result.get(context.get("extract_key"), result)
        return result

    # 为向后兼容，更新部分核心方法使用 dynamic call
    def get_org_info(self):
        """获取企业信息 (新架构)"""
        return self.call("get_org_info")

    def query_projects_page(self, page_size: int = 50, page_token=None):
        """查询项目页 (使用配置)"""
        context = {"pageSize": page_size}
        if page_token:
            context["pageToken"] = page_token
        return self.call("query_projects", **context)  # 注意：call 返回 data, 旧代码期望 full response

    # 注意：部分复杂方法 (get_projects, get_all_project_tasks) 暂保留原有逻辑，
    # 后续可逐步迁移到使用 call + 循环处理 pagination。


def get_api_client():
    """获取 API 客户端 (初始化 session 并使用 dynamic registry)"""
    init_session_state()  # 确保 API configs 和其他状态初始化
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
            "<div style='font-size:1.15rem;font-weight:700;color:#60a5fa;'>Teambition</div>"
            "<div style='color:#94a3b8;font-size:0.85rem;margin-top:2px;'>数据工作台</div></div>",
            unsafe_allow_html=True,
        )

        selected = option_menu(
            menu_title="导航",
            options=["认证", "数据中心", "API记录", "接口配置", "关于"],
            icons=["key", "database", "list", "settings", "info-circle"],
            menu_icon="window-sidebar",
            default_index=0,
            styles={
                "container": {
                    "padding": "6px 4px",
                    "border-radius": "12px",
                    "background-color": "#0f172a",
                    "border": "1px solid #334155",
                },
                "icon": {"color": "#60a5fa", "font-size": "18px"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "4px 0",
                    "padding": "10px 14px",
                    "color": "#e2e8f0",
                    "background-color": "transparent",
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


def auth_page():
    """认证页：选择企业（凭证仅服务端注入）→ 输入暗号换票；不展示 AppId/Secret/企业ID，不提示暗号规则。"""
    st.markdown('<h1 class="main-header">🔑 认证与 Token</h1>', unsafe_allow_html=True)
    st.markdown("请先选择企业，再输入暗号完成换票。应用凭证不在页面展示。")

    init_session_state()

    st.subheader("企业")
    company_names = list(COMPANY_PROFILES.keys())
    st.selectbox(
        "选择公司",
        company_names,
        key="selected_company",
        help="可选企业列表将随业务扩展；选中后自动绑定对应应用凭证。",
        label_visibility="visible",
    )
    if st.session_state.get("selected_company") in COMPANY_PROFILES:
        apply_company_to_session(st.session_state.selected_company)

    st.subheader("暗号验证")
    with st.form(key="password_form"):
        st.markdown("### 请输入暗号")
        passphrase = st.text_input(
            "暗号",
            type="password",
            autocomplete="off",
            label_visibility="visible",
        )
        submit_button = st.form_submit_button("验证并获取 Token", type="primary")

        if submit_button:
            import datetime

            today = datetime.datetime.now().strftime("%Y%m%d")
            app_id = st.session_state.get("app_id")
            app_secret = st.session_state.get("app_secret")
            if not app_id or not app_secret:
                st.error("请先选择企业。")
            elif passphrase == today:
                with st.spinner("获取 Token 中..."):
                    try:
                        token = get_app_token(app_id, app_secret)
                        st.session_state["token"] = token
                        st.success("✅ Token 获取成功。连接状态见左侧。")
                        with st.expander("查看 Access Token（请勿外泄）", expanded=False):
                            st.code(token, language=None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 获取 Token 失败: {e}")
            else:
                st.error("暗号错误，请重试。")

    st.markdown("---")
    st.subheader("📊 当前状态")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Access Token", "✅ 已配置" if st.session_state.get("token") else "❌ 未配置")
    with col2:
        st.metric(
            "当前企业",
            st.session_state.get("selected_company") or "未选择",
        )

    st.caption("应用凭证与组织标识由所选企业自动绑定，不在界面显示。")

    style_metric_cards(
        background_color="#1e293b",
        border_color="#334155",
        border_radius_px=12,
        border_left_color="#3b82f6",
        box_shadow=False,
    )


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
    if 'api_requests' not in st.session_state:
        st.session_state.api_requests = []
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    
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
    
    # 获取所有项目的任务（增强版：同时获取阶段信息）
    if fetch_all and st.session_state.projects_data:
        progress_bar = st.progress(0)
        try:
            with st.spinner("正在按项目拉取任务和阶段信息...（这可能需要较长时间）"):
                tasks_data = client.get_all_project_tasks(
                    st.session_state.projects_data,
                    page_size=50
                )
                st.session_state.tasks_data = tasks_data
                total_tasks = sum(len(data['tasks']) for data in tasks_data.values())
                st.success(f"✅ 共获取 {total_tasks} 个任务! (来自 {len(tasks_data)} 个项目)")
                progress_bar.empty()
        except Exception as e:
            st.error(f"❌ 获取任务失败: {str(e)}")
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
                org_id = org.get("orgId") or org.get("id") or st.session_state.get("tenant_id")
                st.metric("企业 ID", org_id or "N/A")
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

    # 显示项目任务（增强版：显示阶段信息）
    if st.session_state.tasks_data:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            total_tasks = sum(len(data['tasks']) for data in st.session_state.tasks_data.values())
            st.markdown(f"### 📋 项目任务详情 (共 {total_tasks} 个任务)")

            for project_id, data in st.session_state.tasks_data.items():
                project_name = data.get('name', '未命名')
                tasks = data.get('tasks', [])
                stages = data.get('stages', [])
                stage_map = data.get('stage_map', {})

                stage_rows = [s for s in (stages or []) if isinstance(s, dict)]
                stage_info = f" | {len(stage_rows)} 个阶段" if stage_rows else ""
                with st.expander(f"📂 {project_name} ({len(tasks)} 个任务{stage_info})"):
                    if stage_rows:
                        st.markdown("**📍 项目阶段 (Kanban 列):**")
                        stage_df = pd.DataFrame(
                            [
                                {
                                    "阶段ID": s.get("id"),
                                    "阶段名称": s.get("name"),
                                    "tasklistId": s.get("tasklistId"),
                                }
                                for s in stage_rows
                            ]
                        )
                        st.dataframe(stage_df, use_container_width=True, hide_index=True)

                    if tasks:
                        tasks_df = pd.DataFrame(tasks)
                        # 增强显示：如果有 stageId，映射为阶段名称
                        if 'stageId' in tasks_df.columns and stage_map:
                            tasks_df['stageName'] = tasks_df['stageId'].map(stage_map).fillna(tasks_df.get('stageId', ''))
                            display_cols = ['name', 'stageName', 'content', 'executor', 'created', 'updated']
                        else:
                            display_cols = ['name', 'content', 'executor', 'stage', 'created', 'updated']

                        available_cols = [c for c in display_cols if c in tasks_df.columns or c == 'stageName']
                        st.dataframe(
                            tasks_df[available_cols] if 'stageName' in available_cols else tasks_df[available_cols],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "name": st.column_config.TextColumn("任务名称", width="large"),
                                "stageName": st.column_config.TextColumn("阶段", width="medium"),
                                "content": st.column_config.TextColumn("内容", width="large"),
                                "executor": st.column_config.TextColumn("执行者", width="medium"),
                            }
                        )
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

        style_metric_cards(
            background_color="#1e293b",
            border_color="#334155",
            border_radius_px=12,
            border_left_color="#3b82f6",
            box_shadow=False,
        )

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





def tasks_page():
    """专用任务查询页面 - 聚焦于按项目/阶段查询任务"""
    st.markdown('<h1 class="main-header">📋 任务查询</h1>', unsafe_allow_html=True)
    st.markdown("""
    任务数据统一走开放平台 **`GET /api/v3/task/query`**（与[查询任务详情](https://open.teambition.com/docs/apis/6321c6d2912d20d3b5a4a7b8)同一路径）：
    - **拉取某项目下全部任务**：query 中带 `filter`（JSON，内含 `projectId`）+ `pageSize` / `pageToken` 分页
    - **按任务 ID 查详情**：query 中带 `taskId` / `shortIds` / `parentTaskId`（见文档）

    流程：
    1. `/v3/project/{projectId}/stage/search` 获取项目**阶段**（Kanban 列）
    2. `GET /v3/task/query` + `filter.projectId` 获取该项目下的**全部任务**（游标分页）

    **权限提示**：如果仍提示「没有权限」，请在 [Teambition 开放平台](https://open.teambition.com) 的应用设置中开启：
    - `tb-core:project.stage:list`（项目自定义列表查看权限）
    - `tb-core:project.task:list`（项目任务查看权限）
    保存权限后**必须重新获取 Token**（在「配置」页重新验证暗号）。
    """)

    client = get_api_client()
    if not client:
        st.warning("⚠️ 请先在「配置」中完成 Token 与企业 ID 配置。")
        return

    # API 请求报文调试面板
    if st.session_state.get("debug_mode") and st.session_state.get("api_requests"):
        with st.expander("📡 API 请求记录 (最近20条；含一键复制，便于 Postman Raw text 导入)", expanded=True):
            for i, req in enumerate(st.session_state.api_requests[:20]):
                rc = req.get("response_code")
                if req.get("status") == "pending":
                    status_color = "🟡"
                elif rc in (0, 200):
                    status_color = "🟢"
                else:
                    status_color = "🔴"
                rc_show = rc if rc is not None else req.get("status", "N/A")
                title = f"{status_color} {req['timestamp']} {req['method']} {req['endpoint']} (业务code: {rc_show})"
                with st.expander(title, expanded=False):
                    bundle = format_api_debug_bundle(req)
                    render_copy_debug_bundle_button(bundle)
                    st.caption("备用：若浏览器拦截剪贴板，请展开下方文本框后 **Ctrl+A / Cmd+A** 全选复制。")
                    st.text_area(
                        "完整报文（纯文本）",
                        value=bundle,
                        height=220,
                        key=f"api_dbg_txt_{i}_{req.get('timestamp', i)}",
                        label_visibility="collapsed",
                    )
                    st.code(f"URL: {req['full_url']}", language="text")
                    st.json({
                        "headers（界面脱敏）": req["headers"],
                        "params": req.get("params", {}),
                    })
                    if req.get("error_message"):
                        st.error(f"错误: {req['error_message']}")
                    if req.get("response_summary"):
                        st.info(f"响应摘要: {req['response_summary']}")
            if st.button("🗑️ 清空请求记录", key="clear_api_requests_btn"):
                st.session_state.api_requests = []
                st.rerun()

    # 操作按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 拉取全部项目任务和阶段（推荐）", type="primary", use_container_width=True, key="fetch_all_tasks_btn"):
            if st.session_state.get('projects_data'):
                try:
                    with st.spinner("正在批量拉取所有项目的任务和阶段信息..."):
                        tasks_data = client.get_all_project_tasks(st.session_state.projects_data, page_size=30)
                        st.session_state.tasks_data = tasks_data
                        total_tasks = sum(len(d.get('tasks', [])) for d in tasks_data.values())
                        st.success(f"✅ 成功！共获取 **{total_tasks}** 个任务（来自 {len(tasks_data)} 个项目）")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ {str(e)}")
            else:
                st.error("请先在「数据」页面获取项目列表")
                st.info("💡 切换到「数据」页 → 点击「获取全部数据」或「拉取全部项目任务」")

    with col2:
        if st.button("🧹 清空任务缓存", use_container_width=True, key="clear_tasks_btn"):
            st.session_state.tasks_data = {}
            st.success("任务数据已清空")
            st.rerun()

    # 单个项目查询
    if st.session_state.get('projects_data'):
        st.markdown("### 🎯 单个项目快速查询")
        project_options = [f"{p.get('name', '未命名')} ({p.get('id')[:8]}...)" for p in st.session_state.projects_data[:15]]
        selected_idx = st.selectbox(
            "选择项目",
            range(len(project_options)),
            format_func=lambda x: project_options[x],
            key="task_project_select"
        )
        selected_project = st.session_state.projects_data[selected_idx]
        project_id = selected_project.get('id')
        project_name = selected_project.get('name', '未命名')

        if st.button(f"🔍 查询「{project_name}」的任务和阶段", type="secondary", key="single_project_query"):
            try:
                with st.spinner(f"查询 {project_name} ..."):
                    stages = client.search_project_stages(project_id)
                    tasks = client.get_project_tasks(project_id, page_size=100)
                    stage_map = {s.get('id'): s.get('name', '未命名阶段') for s in stages}

                    st.session_state.tasks_data = {
                        project_id: {
                            'name': project_name,
                            'tasks': tasks,
                            'stages': stages,
                            'stage_map': stage_map
                        }
                    }
                    st.success(f"✅ 获取到 **{len(tasks)}** 个任务，**{len(stages)}** 个阶段")
                    st.rerun()
            except Exception as e:
                st.error(f"查询失败: {str(e)}")

    # 显示结果
    if st.session_state.get('tasks_data'):
        display_data()
    else:
        st.info("👆 点击上方按钮开始查询任务。\n\n"
                "本页面专门优化了**阶段 + 任务**的查询流程，能更好地解决权限问题。")


def api_config_page():
    """接口配置页面 - 维护所有API的地址、参数、resolver (核心新功能)"""
    st.markdown('<h1 class="main-header">🔧 接口配置</h1>', unsafe_allow_html=True)
    st.markdown("维护 Teambition API 端点、默认参数、动态取值方法 (resolvers)。支持测试调用和持久化。")

    init_session_state()
    client = get_api_client()

    # Tabs for config management and test
    tab_config, tab_test, tab_docs = st.tabs(["配置管理", "API 测试", "使用说明"])

    with tab_config:
        st.subheader("当前接口配置")
        # Use data_editor for editable list (nested JSON handled via column config)
        edited_configs = st.data_editor(
            st.session_state.api_configs,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "name": st.column_config.TextColumn("名称", required=True, width="small"),
                "description": st.column_config.TextColumn("描述", width="medium"),
                "method": st.column_config.SelectboxColumn("Method", options=["GET", "POST"], width="small"),
                "endpoint": st.column_config.TextColumn("Endpoint", width="medium"),
                "default_params": st.column_config.TextColumn("默认参数 (JSON)", width="medium"),
                "resolvers": st.column_config.TextColumn("Resolver (JSON)", width="medium"),
                "response_key": st.column_config.TextColumn("响应键", default="result", width="small"),
                "pagination": st.column_config.CheckboxColumn("分页", default=False),
            },
            hide_index=True,
            key="api_config_editor"
        )

        # Sync back to session (data_editor returns edited df-like, convert back)
        if isinstance(edited_configs, pd.DataFrame):
            st.session_state.api_configs = edited_configs.to_dict('records')
        else:
            st.session_state.api_configs = edited_configs

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 保存配置为 JSON", use_container_width=True):
                config_json = json.dumps(st.session_state.api_configs, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载 api_configs.json",
                    data=config_json,
                    file_name="api_configs.json",
                    mime="application/json",
                )
        with col2:
            uploaded = st.file_uploader("📤 上传配置 JSON", type=["json"])
            if uploaded:
                try:
                    uploaded_configs = json.load(uploaded)
                    st.session_state.api_configs = uploaded_configs
                    st.success("✅ 配置已加载")
                    st.rerun()
                except Exception as e:
                    st.error(f"加载失败: {e}")
        with col3:
            if st.button("🔄 重置为默认", use_container_width=True):
                st.session_state.api_configs = DEFAULT_API_CONFIGS.copy()
                st.success("已重置为默认接口配置")
                st.rerun()

    with tab_test:
        st.subheader("测试选定接口")
        if not client:
            st.warning("请先在「认证」页完成 Token 配置")
            st.stop()

        api_names = [c["name"] for c in st.session_state.api_configs]
        selected_api = st.selectbox("选择接口", api_names, index=0)

        config = next((c for c in st.session_state.api_configs if c["name"] == selected_api), None)
        if config:
            st.json(config, expanded=False)

        test_context_str = st.text_area(
            "测试上下文 (JSON, e.g. {\"project_id\": \"xxx\", \"pageToken\": \"...\"})",
            value='{"project_id": "example-project-id"}',
            height=100
        )

        if st.button("🚀 执行调用", type="primary"):
            try:
                context = json.loads(test_context_str) if test_context_str.strip() else {}
                with st.spinner(f"调用 {selected_api}..."):
                    result = client.call(selected_api, **context)
                    st.success("✅ 调用成功")
                    st.json(result, expanded=True)

                    # Show recent debug if available
                    if st.session_state.get("api_requests"):
                        with st.expander("📡 最新请求记录"):
                            st.json(st.session_state.api_requests[0])
            except json.JSONDecodeError:
                st.error("上下文 JSON 格式错误")
            except Exception as e:
                st.error(f"调用失败: {str(e)}")
                with st.expander("错误详情"):
                    st.exception(e)

    with tab_docs:
        st.markdown("""
### 配置说明
- **name**: 唯一键，用于 `client.call("name", **context)`
- **resolvers**: 键值对，如 `{"filter": "build_task_filter", "projectId": "from_context"}` - 动态从 context/session 取值
- **default_params**: 默认 query 参数 (dict)
- **endpoint**: 支持模板如 `/v3/project/{projectId}/stage/search`
- 测试时提供 context JSON 来模拟参数 (project_id, pageToken 等)
- 所有调用自动通过 `_request` 记录调试日志 (在「API记录」页查看)

**预置接口** 已包含企业、项目、任务、阶段、工时。 可通过编辑器添加新接口而无需修改代码。
        """)

    st.caption("配置变更立即生效于 Dynamic Client。建议测试后保存 JSON 备份。")


def data_center_page():
    """数据中心 (合并原 main_page + tasks_page) - 拉取数据、查询明细、导出Excel"""
    st.markdown('<h1 class="main-header">📊 数据中心</h1>', unsafe_allow_html=True)
    st.info("**使用提示**：先在「认证」页获取 Token。支持拉取企业/项目/任务/工时、明细查询和 Excel 导出。使用动态 API 配置。")

    client = get_api_client()
    if not client:
        st.warning("⚠️ 请先在「认证」页完成 Token 与企业 ID 配置。")
        return

    # Tabs for operations, details, export (consolidated from old pages)
    tab_ops, tab_details, tab_export = st.tabs(["🚀 操作面板", "📋 数据明细", "📥 导出 Excel"])

    with tab_ops:
        st.subheader("批量拉取操作")
        if st.button("获取企业信息", type="primary"):
            try:
                org = client.call("get_org_info")
                # call() 返回完整响应；与 main_page 拉取逻辑一致，只存 result 供 display_data 使用
                st.session_state.org_data = (
                    org.get("result", {}) if isinstance(org, dict) else {}
                )
                st.success("✅ 企业信息获取成功")
                st.json(org)
            except Exception as e:
                st.error(str(e))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("拉取全部项目", key="fetch_projects_btn"):
                try:
                    projects = client.get_projects()  # keep old for compatibility
                    st.session_state.projects_data = projects
                    st.success(f"✅ 获取 {len(projects)} 个项目")
                except Exception as e:
                    st.error(str(e))
        with col2:
            if st.button("拉取全部项目任务和阶段 (推荐)", type="primary", key="fetch_all_tasks_btn"):
                if st.session_state.get('projects_data'):
                    try:
                        tasks_data = client.get_all_project_tasks(st.session_state.projects_data)
                        st.session_state.tasks_data = tasks_data
                        total = sum(len(d.get('tasks', [])) for d in tasks_data.values())
                        st.success(f"✅ 成功获取 {total} 个任务")
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.warning("请先拉取项目列表")

    with tab_details:
        st.subheader("数据明细查询")
        if st.session_state.get('projects_data'):
            project_options = [f"{p.get('name','')} ({p.get('id')[:8]}...)" for p in st.session_state.projects_data[:10]]
            selected_p = st.selectbox("选择项目查看任务", project_options, key="detail_project_select")
            if st.button("查询选中项目任务"):
                # Use dynamic
                idx = project_options.index(selected_p)
                proj = st.session_state.projects_data[idx]
                try:
                    # call() 默认返回完整响应；业务数据在 result，与 get_all_project_tasks 一致
                    stages = client.call(
                        "search_project_stages",
                        project_id=proj["id"],
                        extract_key="result",
                    )
                    tasks = client.call(
                        "query_tasks",
                        project_id=proj["id"],
                        extract_key="result",
                    )
                    if not isinstance(stages, list):
                        stages = []
                    if not isinstance(tasks, list):
                        tasks = []
                    st.session_state.tasks_data = {
                        proj["id"]: {
                            "name": proj.get("name"),
                            "tasks": tasks,
                            "stages": stages,
                        }
                    }
                    st.success("查询完成")
                    display_data()
                except Exception as e:
                    st.error(str(e))
        else:
            st.info("请先在操作面板拉取项目数据")

        if st.session_state.get('tasks_data') or st.session_state.get('org_data') or st.session_state.get('projects_data'):
            display_data()

    with tab_export:
        export_data()

    st.caption("所有操作均通过动态 API 配置调用，支持在「接口配置」页扩展新接口。")


def api_records_page():
    """API 请求记录页面 - 集中展示所有调试报文"""
    st.markdown('<h1 class="main-header">📡 API 请求记录</h1>', unsafe_allow_html=True)
    st.markdown("所有通过 TeambitionAPI 发出的请求记录在此 (含请求/响应/cURL)。")

    init_session_state()
    if not st.session_state.get("api_requests"):
        st.info("暂无记录。启用调试模式并执行操作后会自动记录。")
        if st.button("🪲 启用调试模式"):
            st.session_state.debug_mode = True
        return

    st.toggle("显示调试模式", value=st.session_state.get("debug_mode", False), key="debug_toggle")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("搜索 endpoint 或状态", "")
    with col2:
        if st.button("🗑️ 清空所有记录"):
            st.session_state.api_requests = []
            st.rerun()

    filtered = st.session_state.api_requests
    if search:
        filtered = [r for r in filtered if search.lower() in str(r.get('endpoint', '')).lower() or search.lower() in str(r.get('status', ''))]

    for i, req in enumerate(filtered[:30]):  # limit display
        status_emoji = "🟢" if req.get("status") in (0, 200, "success") else "🔴"
        title = f"{status_emoji} {req.get('timestamp', '')} {req.get('method','')} {req.get('endpoint','')}"
        with st.expander(title, expanded=i == 0):
            bundle = format_api_debug_bundle(req)
            render_copy_debug_bundle_button(bundle)
            st.text_area("完整报文 (备用复制)", value=bundle, height=200, label_visibility="collapsed")
            st.json({
                "headers (脱敏)": req.get("headers", {}),
                "params": req.get("params", {}),
                "response": req.get("response_json", {})
            })

    st.caption(f"共 {len(st.session_state.api_requests)} 条记录 (保留最近20条)")


def main():
    """主函数 - 更新为新菜单结构"""
    init_session_state()
    page = app_menu()

    if page == "认证":
        auth_page()
    elif page == "数据中心":
        data_center_page()
    elif page == "API记录":
        api_records_page()
    elif page == "接口配置":
        api_config_page()
    elif page == "关于":
        about_page()
    else:
        data_center_page()  # default

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888;'>
        Teambition 数据工作台 | 重构版 (认证 / 数据中心 / API记录 / 接口配置)
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
