"""Shared helpers (ported from legacy app.py)."""

from __future__ import annotations

import ast
import json
import re
from typing import Any


def camel_to_snake(name: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def merge_snake_to_camel_for_path(context: dict) -> dict:
    ctx = dict(context)
    if ctx.get("project_id") is not None and "projectId" not in ctx:
        ctx["projectId"] = ctx["project_id"]
    if ctx.get("task_id") is not None and "taskId" not in ctx:
        ctx["taskId"] = ctx["task_id"]
    return ctx


def strip_query_params_bound_to_path_template(endpoint_template: str, params: dict) -> None:
    for raw in re.findall(r"\{([^}]+)\}", endpoint_template):
        keys = {raw}
        snake = camel_to_snake(raw)
        if snake != raw:
            keys.add(snake)
        for k in keys:
            params.pop(k, None)


def dedupe_camel_snake_query_aliases(params: dict) -> None:
    for camel, snake in (
        ("projectId", "project_id"),
        ("taskId", "task_id"),
        ("pageToken", "page_token"),
    ):
        if camel in params and snake in params:
            del params[snake]


def api_result_list(payload: Any, key: str = "result") -> list:
    if not isinstance(payload, dict):
        return []
    val = payload.get(key)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def coerce_api_json_dict(value: Any, field_label: str = "字段") -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError) as e:
                raise ValueError(
                    f"{field_label} 不是合法 JSON 对象（需双引号键名，或使用 Python 字典字面量）: {e}"
                ) from e
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_label} 应为 JSON 对象，当前为 {type(parsed).__name__}")
        return parsed
    raise ValueError(f"{field_label} 类型不支持: {type(value).__name__}")
