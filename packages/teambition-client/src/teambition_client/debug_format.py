"""Format request logs for Postman / manual debugging (no Streamlit)."""

from __future__ import annotations

import json
from urllib.parse import urlencode


def build_curl_from_request(req: dict) -> str:
    """Build a cURL string suitable for Postman Import → Raw text."""
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
    """Full text bundle: HTTP request/response + cURL."""
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
    http_st = req.get("http_status")
    lines.append(f"HTTP 状态码: {http_st if http_st is not None else 'N/A'}")
    biz = req.get("response_code")
    if biz is not None:
        lines.append(f"业务 code: {biz}")
    else:
        lines.append(f"业务 code: {req.get('status', 'N/A')}")
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
    lines.extend(
        ["", "--- cURL（Postman：Import → Raw text 粘贴下面整段）---", build_curl_from_request(req)]
    )
    return "\n".join(lines)
