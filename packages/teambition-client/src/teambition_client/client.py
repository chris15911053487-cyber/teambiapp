"""Teambition Open API HTTP client (framework-agnostic)."""

from __future__ import annotations

import copy
import datetime as dt
import json
from collections.abc import Callable
from typing import Any, Optional

import requests

from teambition_client.defaults import DEFAULT_API_CONFIGS
from teambition_client.helpers import (
    api_result_list,
    coerce_api_json_dict,
    dedupe_camel_snake_query_aliases,
    merge_snake_to_camel_for_path,
    strip_query_params_bound_to_path_template,
)
from teambition_client.resolvers import resolve_param

RequestLogCallback = Callable[[dict], None]


class TeambitionAPI:
    BASE_URL = "https://open.teambition.com/api"

    def __init__(
        self,
        token: str,
        tenant_id: str,
        *,
        api_configs: Optional[list[dict]] = None,
        debug: bool = False,
        on_request_log: Optional[RequestLogCallback] = None,
        max_debug_logs: int = 20,
    ) -> None:
        self.token = token
        self.tenant_id = tenant_id
        self._api_configs = copy.deepcopy(api_configs or DEFAULT_API_CONFIGS)
        self._debug = debug
        self._on_request_log = on_request_log
        self._max_debug_logs = max_debug_logs

    def set_api_configs(self, configs: list[dict]) -> None:
        self._api_configs = copy.deepcopy(configs)

    def get_api_configs(self) -> list[dict]:
        return copy.deepcopy(self._api_configs)

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Tenant-type": "organization",
            "X-Tenant-Id": self.tenant_id,
        }

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        request_log: Optional[dict] = None
        if self._debug and self._on_request_log is not None:
            timestamp = dt.datetime.now().strftime("%H:%M:%S")
            params = kwargs.get("params", {})
            display_headers = headers.copy()
            if "Authorization" in display_headers:
                auth = display_headers["Authorization"]
                display_headers["Authorization"] = (
                    auth[:20] + "..." if len(auth) > 20 else auth
                )
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

        response: Optional[requests.Response] = None
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            try:
                result = response.json()
            except ValueError:
                result = {"_parse_error": "响应非 JSON", "text": response.text[:2000]}

            code = result.get("code") if isinstance(result, dict) else None
            error_message = result.get("errorMessage", "") if isinstance(result, dict) else ""

            if request_log is not None:
                request_log["http_status"] = response.status_code
                request_log["status"] = code if code is not None else response.status_code
                request_log["response_code"] = code
                request_log["error_message"] = error_message
                request_log["response_json"] = (
                    result if isinstance(result, dict) else {"_raw": str(result)}
                )
                if isinstance(result, dict) and "result" in result:
                    request_log["response_summary"] = f"{len(str(result.get('result', '')))} chars"
                self._on_request_log(request_log)

            if code is not None and code not in [0, 200]:
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
                    raise RuntimeError(error_detail)
                raise RuntimeError(f"API 错误: {error_message} (code: {code})")

            return result  # type: ignore[return-value]

        except requests.RequestException as e:
            if request_log is not None:
                resp = getattr(e, "response", None)
                request_log["http_status"] = resp.status_code if resp is not None else None
                request_log["status"] = "request_error"
                request_log["response_code"] = None
                request_log["error_message"] = str(e)
                body = None
                if resp is not None:
                    try:
                        body = resp.text[:2000]
                    except Exception:
                        body = None
                request_log["response_json"] = {
                    "_client_error": type(e).__name__,
                    "detail": str(e),
                    **({"response_text": body} if body else {}),
                }
                self._on_request_log(request_log)
            raise

        except Exception as err:
            if request_log is not None and request_log.get("status") == "pending":
                request_log["http_status"] = (
                    getattr(response, "status_code", None) if response is not None else None
                )
                request_log["status"] = "client_error"
                request_log["response_code"] = None
                request_log["error_message"] = str(err)
                request_log["response_json"] = {
                    "_exception": type(err).__name__,
                    "detail": str(err),
                }
                self._on_request_log(request_log)
            raise

    @staticmethod
    def project_query_next_token(result: dict) -> Optional[str]:
        if not result:
            return None
        return (
            result.get("nextPageToken")
            or result.get("next_page_token")
            or result.get("nextToken")
        )

    def get_org_info(self) -> dict:
        return self.call("get_org_info")

    def query_projects_page(self, page_size: int = 50, page_token: Optional[str] = None) -> dict:
        context: dict = {"pageSize": page_size}
        if page_token:
            context["pageToken"] = page_token
        return self.call("query_projects", **context)

    def get_projects(self, page_size: int = 50) -> list:
        all_projects: list = []
        page_token: Optional[str] = None
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

    def get_project_tasks(self, project_id: str, page_size: int = 50) -> list:
        all_tasks: list = []
        page_token: Optional[str] = None
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
                    raise RuntimeError("任务分页异常：连续两批首条任务 ID 相同，疑似未正确翻页。")
                prev_first_id = first_id
            all_tasks.extend(tasks)
            page_token = self.project_query_next_token(result)
            if not page_token:
                break
        return all_tasks

    def search_project_stages(self, project_id: str, page_size: int = 50) -> list:
        params = {"pageSize": page_size}
        result = self._request("GET", f"/v3/project/{project_id}/stage/search", params=params)
        return api_result_list(result)

    @staticmethod
    def _comma_separated_ids(ids: Any) -> Optional[str]:
        if ids is None:
            return None
        if isinstance(ids, (list, tuple)):
            return ",".join(str(x) for x in ids)
        return str(ids).strip()

    def query_tasks(
        self,
        project_id: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None,
        *,
        stage_id: Optional[str] = None,
        task_ids: Any = None,
        short_ids: Any = None,
        parent_task_id: Optional[str] = None,
        operator_id: Optional[str] = None,
    ) -> tuple[list, Optional[str]]:
        extra_headers = {"x-operator-id": operator_id} if operator_id else None

        if project_id:
            filter_obj: dict = {"projectId": project_id}
            if stage_id:
                filter_obj["stageId"] = stage_id
            params = {
                "pageSize": page_size,
                "filter": json.dumps(filter_obj),
            }
            if page_token:
                params["pageToken"] = page_token
            req_kwargs: dict = {"params": params}
            if extra_headers:
                req_kwargs["headers"] = extra_headers
            result = self._request("GET", "/v3/task/query", **req_kwargs)
            return api_result_list(result), self.project_query_next_token(result)

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
        return api_result_list(result), None

    def get_all_project_tasks(self, projects: list, page_size: int = 50) -> dict:
        all_tasks_data: dict = {}
        for project in projects:
            project_id = project.get("id")
            project_name = project.get("name", "未命名")
            try:
                stages = self.search_project_stages(project_id, page_size)
                stage_map = {
                    s.get("id"): s.get("name", "未命名")
                    for s in stages
                    if isinstance(s, dict)
                }
                tasks: list = []
                pt: Optional[str] = None
                while True:
                    page_tasks, next_token = self.query_tasks(
                        project_id=project_id,
                        page_token=pt,
                        page_size=page_size,
                    )
                    tasks.extend(page_tasks)
                    pt = next_token
                    if not pt:
                        break
                all_tasks_data[project_id] = {
                    "name": project_name,
                    "tasks": tasks,
                    "stages": stages,
                    "stage_map": stage_map,
                }
            except Exception as e:
                raise RuntimeError(f"项目 [{project_name}] 任务获取失败: {str(e)}") from e
        return all_tasks_data

    def get_task_worktime(self, task_id: str) -> list:
        result = self._request("GET", f"/worktime/aggregation/task/{task_id}")
        return api_result_list(result)

    def get_config(self, name: str) -> dict:
        for config in self._api_configs:
            if config.get("name") == name:
                return copy.deepcopy(config)
        for config in DEFAULT_API_CONFIGS:
            if config.get("name") == name:
                return copy.deepcopy(config)
        raise ValueError(f"未找到 API 配置: {name}")

    def resolve_endpoint(self, endpoint: str, context: dict) -> str:
        for key, value in list(context.items()):
            if value is None:
                continue
            for placeholder in [f"{{{key}}}", f"{{{key.lower()}}}", f"{{{key.upper()}}}"]:
                if placeholder in endpoint:
                    endpoint = endpoint.replace(placeholder, str(value))
        return endpoint

    def call(self, name: str, **context: Any) -> Any:
        config = self.get_config(name)
        method = config["method"]
        path_ctx = merge_snake_to_camel_for_path(context)
        endpoint = self.resolve_endpoint(config["endpoint"], path_ctx)

        params_or_body = coerce_api_json_dict(config.get("default_params"), "default_params")
        resolvers_map = coerce_api_json_dict(config.get("resolvers"), "resolvers")
        runtime = {"token": self.token, "tenant_id": self.tenant_id}
        for param_name, resolver_name in resolvers_map.items():
            value = resolve_param(
                resolver_name, {**path_ctx, "api_name": name}, config, runtime=runtime
            )
            if value is not None:
                params_or_body[param_name] = value

        _internal_ctx_keys = frozenset({"api_name", "extract_key"})
        for k, v in context.items():
            if k in _internal_ctx_keys:
                continue
            params_or_body[k] = v

        if method.upper() == "GET":
            dedupe_camel_snake_query_aliases(params_or_body)
            strip_query_params_bound_to_path_template(config["endpoint"], params_or_body)

        kwargs = (
            {"params": params_or_body} if method.upper() == "GET" else {"json": params_or_body}
        )

        result = self._request(method, endpoint, **kwargs)

        if isinstance(result, dict) and context.get("extract_key"):
            return result.get(context.get("extract_key"), result)
        return result
