"""Debug log retrieval."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from teambition_client import TeambitionAPI
from teambition_client.debug_format import build_curl_from_request, format_api_debug_bundle

from app.debug_store import clear_logs, get_logs
from app.deps import get_teambition_client

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/logs")
def get_debug_logs(
    _client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
    session_id: str = Query(..., description="与请求头 X-Debug-Session 相同"),
):
    logs = get_logs(session_id)
    bundles = [format_api_debug_bundle(x) for x in logs]
    curls = [build_curl_from_request(x) for x in logs]
    return {"logs": logs, "bundles": bundles, "curls": curls}


@router.delete("/logs")
def delete_debug_logs(
    _client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
    session_id: str = Query(...),
):
    clear_logs(session_id)
    return {"ok": True}
