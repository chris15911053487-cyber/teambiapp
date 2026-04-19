"""Parameter resolvers for dynamic API calls."""

from __future__ import annotations

import json
from typing import Any, Optional


def resolve_param(
    resolver_name: str,
    context: dict,
    api_config: Optional[dict] = None,
    *,
    runtime: Optional[dict] = None,
) -> Any:
    """
    Resolve a query/body parameter from context.

    `runtime` may supply ``token`` / ``tenant_id`` for resolvers like ``get_token``
    (legacy Streamlit used session_state).
    """
    runtime = runtime or {}
    if resolver_name == "from_context":
        for key in context:
            if key.lower() in [
                "projectid",
                "project_id",
                "id",
                "taskid",
                "task_id",
                "token",
                "tenant_id",
                "pagetoken",
            ]:
                return context.get(key)
        return None
    if resolver_name == "build_task_filter":
        project_id = context.get("project_id") or context.get("projectId")
        if project_id:
            filter_dict: dict = {"projectId": project_id}
            if "stage_id" in context or "stageId" in context:
                filter_dict["stageId"] = context.get("stage_id") or context.get("stageId")
            return json.dumps(filter_dict)
        return json.dumps({"projectId": "all"})
    if resolver_name == "get_token":
        return runtime.get("token", "")
    if resolver_name == "get_tenant_id":
        return runtime.get("tenant_id", "")
    return context.get(resolver_name)
