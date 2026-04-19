"""Excel export (pandas + openpyxl)."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

import pandas as pd


def build_excel_workbook(payload: dict[str, Any]) -> bytes:
    """
    Build xlsx from JSON snapshot (same general shape as legacy Streamlit session).

    Expected keys (all optional): org, projects, tasksByProject, worktimeByTask
    """
    df_list: list[pd.DataFrame] = []
    sheet_names: list[str] = []

    org = payload.get("org")
    if org:
        df_list.append(pd.DataFrame([org] if isinstance(org, dict) else org))
        sheet_names.append("企业信息")

    projects = payload.get("projects")
    if projects and isinstance(projects, list):
        df_list.append(pd.DataFrame(projects))
        sheet_names.append("项目列表")

    tasks_by = payload.get("tasksByProject") or {}
    if isinstance(tasks_by, dict):
        for _pid, bundle in tasks_by.items():
            if not isinstance(bundle, dict):
                continue
            tasks = bundle.get("tasks") or []
            name = bundle.get("name") or "project"
            if not tasks:
                continue
            tasks_df = pd.DataFrame(tasks)
            safe = re.sub(r"[^\w\- ]", "", str(name))[:15].strip() or "project"
            df_list.append(tasks_df)
            sheet_names.append(f"任务-{safe}")

    worktime = payload.get("worktimeByTask") or {}
    if isinstance(worktime, dict) and worktime:
        rows: list[dict] = []
        for _tid, data in worktime.items():
            if not isinstance(data, dict):
                continue
            p_name = data.get("project_name", "")
            t_name = data.get("task_name", "")
            for item in data.get("worktime") or []:
                if isinstance(item, dict):
                    rows.append(
                        {
                            "项目名称": p_name,
                            "任务名称": t_name,
                            "对象ID": item.get("objectId", ""),
                            "对象类型": item.get("objectType", ""),
                            "工时(毫秒)": item.get("worktime", 0),
                            "记录数量": item.get("count", 0),
                        }
                    )
        if rows:
            df_list.append(pd.DataFrame(rows))
            sheet_names.append("工时信息")

    if not df_list:
        raise ValueError("没有可导出的数据")

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for df, sn in zip(df_list, sheet_names):
            df.to_excel(writer, sheet_name=sn[:31], index=False)
    buf.seek(0)
    return buf.read()
