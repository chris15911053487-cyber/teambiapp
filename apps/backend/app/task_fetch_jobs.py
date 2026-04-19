"""In-memory incremental fetch for all projects' stages + tasks (stop / resume)."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from teambition_client import TeambitionAPI

JobStatus = Literal["running", "cancelled", "completed", "failed"]


@dataclass
class FetchTaskJob:
    job_id: str
    status: JobStatus
    page_size: int
    projects: list[dict[str, Any]]
    project_index: int
    tasks_by_project: dict[str, Any]
    current_project_id: str | None
    current_project_name: str
    cur_stages: list | None
    cur_stage_map: dict[str, str] | None
    cur_tasks: list
    cur_page_token: str | None
    error: str | None = None

    def merged_tasks_by_project(self) -> dict[str, Any]:
        """Completed projects + current project (if stages loaded)."""
        out: dict[str, Any] = dict(self.tasks_by_project)
        pid = self.current_project_id
        if (
            pid
            and self.cur_stages is not None
            and self.project_index < len(self.projects)
        ):
            out[pid] = {
                "name": self.current_project_name,
                "tasks": list(self.cur_tasks),
                "stages": self.cur_stages,
                "stage_map": dict(self.cur_stage_map or {}),
            }
        return out

    def progress_payload(self) -> dict[str, Any]:
        total = len(self.projects)
        idx = min(self.project_index, total)
        pid = self.current_project_id
        phase: str
        if self.status == "completed" or (total > 0 and self.project_index >= total):
            phase = "done"
        elif pid and self.cur_stages is None:
            phase = "stages"
        elif pid:
            phase = "tasks"
        else:
            phase = "idle"

        return {
            "projectIndex": idx,
            "projectTotal": total,
            "currentProjectId": pid,
            "currentProjectName": self.current_project_name or None,
            "currentProjectTaskCount": len(self.cur_tasks),
            "apiPhase": phase,
            "status": self.status,
        }


_store: dict[str, FetchTaskJob] = {}
_lock = threading.Lock()


def create_job(client: TeambitionAPI, page_size: int) -> FetchTaskJob:
    projects = client.get_projects()
    job_id = uuid.uuid4().hex
    if not projects:
        job = FetchTaskJob(
            job_id=job_id,
            status="completed",
            page_size=page_size,
            projects=[],
            project_index=0,
            tasks_by_project={},
            current_project_id=None,
            current_project_name="",
            cur_stages=None,
            cur_stage_map=None,
            cur_tasks=[],
            cur_page_token=None,
        )
        with _lock:
            _store[job_id] = job
        return job

    p0 = projects[0]
    job = FetchTaskJob(
        job_id=job_id,
        status="running",
        page_size=page_size,
        projects=projects,
        project_index=0,
        tasks_by_project={},
        current_project_id=p0.get("id"),
        current_project_name=p0.get("name", "未命名"),
        cur_stages=None,
        cur_stage_map=None,
        cur_tasks=[],
        cur_page_token=None,
    )
    with _lock:
        _store[job_id] = job
    return job


def get_job(job_id: str) -> FetchTaskJob | None:
    with _lock:
        return _store.get(job_id)


def cancel_job(job_id: str) -> FetchTaskJob | None:
    with _lock:
        job = _store.get(job_id)
        if job is None:
            return None
        if job.status == "completed":
            return job
        job.status = "cancelled"
        return job


def try_resume_job(job_id: str) -> tuple[FetchTaskJob | None, str | None]:
    """Resume a cancelled job. Returns (job, error) where error is not_found | not_cancelled | None."""
    with _lock:
        job = _store.get(job_id)
        if job is None:
            return None, "not_found"
        if job.status != "cancelled":
            return job, "not_cancelled"
        if not job.projects:
            job.status = "completed"
            return job, None
        job.status = "running"
        job.error = None
        return job, None


def _finalize_current_project(job: FetchTaskJob) -> None:
    pid = job.current_project_id
    if not pid:
        return
    job.tasks_by_project[pid] = {
        "name": job.current_project_name,
        "tasks": list(job.cur_tasks),
        "stages": job.cur_stages or [],
        "stage_map": dict(job.cur_stage_map or {}),
    }
    job.project_index += 1
    job.cur_stages = None
    job.cur_stage_map = None
    job.cur_tasks = []
    job.cur_page_token = None

    if job.project_index < len(job.projects):
        p = job.projects[job.project_index]
        job.current_project_id = p.get("id")
        job.current_project_name = p.get("name", "未命名")
    else:
        job.current_project_id = None
        job.current_project_name = ""
        job.status = "completed"


def run_step(client: TeambitionAPI, job: FetchTaskJob) -> dict[str, Any]:
    """Perform one API unit (stages for a project, or one task page). Mutates job."""
    if job.status == "completed":
        return {
            "done": True,
            "cancelled": False,
            "failed": False,
            "error": None,
            "tasksByProject": job.merged_tasks_by_project(),
            "progress": job.progress_payload(),
        }

    if job.status == "failed":
        return {
            "done": False,
            "cancelled": False,
            "failed": True,
            "error": job.error,
            "tasksByProject": job.merged_tasks_by_project(),
            "progress": job.progress_payload(),
        }

    if job.status == "cancelled":
        return {
            "done": False,
            "cancelled": True,
            "failed": False,
            "error": None,
            "tasksByProject": job.merged_tasks_by_project(),
            "progress": job.progress_payload(),
        }

    if not job.projects:
        job.status = "completed"
        return {
            "done": True,
            "cancelled": False,
            "failed": False,
            "error": None,
            "tasksByProject": {},
            "progress": job.progress_payload(),
        }

    if job.project_index >= len(job.projects):
        job.status = "completed"
        return {
            "done": True,
            "cancelled": False,
            "failed": False,
            "error": None,
            "tasksByProject": job.merged_tasks_by_project(),
            "progress": job.progress_payload(),
        }

    pid = job.current_project_id
    if not pid:
        job.status = "failed"
        job.error = "内部状态错误：缺少 current_project_id"
        return {
            "done": False,
            "cancelled": False,
            "failed": True,
            "error": job.error,
            "tasksByProject": job.merged_tasks_by_project(),
            "progress": job.progress_payload(),
        }

    try:
        if job.cur_stages is None:
            stages = client.search_project_stages(pid, job.page_size)
            job.cur_stages = stages
            job.cur_stage_map = {
                s.get("id"): s.get("name", "未命名")
                for s in stages
                if isinstance(s, dict)
            }
        else:
            page_tasks, next_t = client.query_tasks(
                project_id=pid,
                page_token=job.cur_page_token,
                page_size=job.page_size,
            )
            job.cur_tasks.extend(page_tasks)
            if next_t is None:
                _finalize_current_project(job)
            else:
                job.cur_page_token = next_t
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        return {
            "done": False,
            "cancelled": False,
            "failed": True,
            "error": job.error,
            "tasksByProject": job.merged_tasks_by_project(),
            "progress": job.progress_payload(),
        }

    done = job.status == "completed"
    return {
        "done": done,
        "cancelled": False,
        "failed": False,
        "error": None,
        "tasksByProject": job.merged_tasks_by_project(),
        "progress": job.progress_payload(),
    }
