"""Data endpoints (org, projects, tasks)."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from teambition_client import TeambitionAPI

from app.deps import get_teambition_client

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/org")
def get_org(client: Annotated[TeambitionAPI, Depends(get_teambition_client)]):
    return client.get_org_info()


@router.get("/projects")
def list_projects(client: Annotated[TeambitionAPI, Depends(get_teambition_client)]):
    return {"projects": client.get_projects()}


@router.get("/projects/{project_id}/stages")
def project_stages(
    project_id: str,
    client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    return {"stages": client.search_project_stages(project_id)}


@router.get("/projects/{project_id}/tasks")
def project_tasks(
    project_id: str,
    client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
    page_size: int = 50,
):
    return {"tasks": client.get_project_tasks(project_id, page_size=page_size)}


class FetchAllTasksBody(BaseModel):
    page_size: int = Field(default=50, ge=1, le=200)


@router.post("/tasks/fetch-all")
def fetch_all_tasks(
    body: FetchAllTasksBody,
    client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    projects = client.get_projects()
    data = client.get_all_project_tasks(projects, page_size=body.page_size)
    return {"projectsCount": len(projects), "tasksByProject": data}


class TeambitionCallBody(BaseModel):
    name: str
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/teambition/call")
def teambition_dynamic_call(
    body: TeambitionCallBody,
    client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    return client.call(body.name, **body.context)
