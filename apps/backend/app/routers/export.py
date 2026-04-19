"""Excel export."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from teambition_client import TeambitionAPI

from app.deps import get_teambition_client
from app.services.export_service import build_excel_workbook

router = APIRouter(prefix="/export", tags=["export"])


class ExportBody(BaseModel):
    org: Optional[Any] = None
    projects: Optional[list[Any]] = None
    tasksByProject: Optional[dict[str, Any]] = None
    worktimeByTask: Optional[dict[str, Any]] = None


@router.post("/excel")
def post_excel(
    body: ExportBody,
    _client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    """Requires auth. JSON body: org, projects, tasksByProject, worktimeByTask."""
    data = build_excel_workbook(body.model_dump(exclude_none=True))
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="teambition_export.xlsx"'},
    )
