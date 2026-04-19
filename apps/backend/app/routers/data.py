"""Data endpoints (org, projects, tasks)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from teambition_client import TeambitionAPI

from app.deps import get_teambition_client
from app.task_fetch_jobs import (
    cancel_job,
    create_job,
    get_job,
    run_step,
    try_resume_job,
)

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


@router.post("/tasks/fetch/jobs")
def start_fetch_job(
    body: FetchAllTasksBody,
    client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    """Create a server-side job: load project list once; client calls ``/step`` until ``done``."""
    job = create_job(client, page_size=body.page_size)
    return {
        "jobId": job.job_id,
        "projectCount": len(job.projects),
        "status": job.status,
    }


@router.post("/tasks/fetch/jobs/{job_id}/step")
def fetch_job_step(
    job_id: str,
    client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    """Execute one Teambition API unit (stages or one task page)."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期（仅保存在服务器内存中）")
    return run_step(client, job)


@router.get("/tasks/fetch/jobs/{job_id}")
def fetch_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return {
        "jobId": job.job_id,
        "status": job.status,
        "error": job.error,
        "progress": job.progress_payload(),
        "tasksByProject": job.merged_tasks_by_project(),
    }


@router.post("/tasks/fetch/jobs/{job_id}/cancel")
def fetch_job_cancel(job_id: str):
    job = cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return {"jobId": job.job_id, "status": job.status}


@router.post("/tasks/fetch/jobs/{job_id}/resume")
def fetch_job_resume(job_id: str):
    job, err = try_resume_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    if err == "not_cancelled":
        raise HTTPException(status_code=400, detail="当前任务未处于已停止状态，无法恢复")
    return {"jobId": job.job_id, "status": job.status}


class TeambitionCallBody(BaseModel):
    name: str
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/teambition/call")
def teambition_dynamic_call(
    body: TeambitionCallBody,
    client: Annotated[TeambitionAPI, Depends(get_teambition_client)],
):
    return client.call(body.name, **body.context)
