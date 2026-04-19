"""Unit tests for incremental task fetch job (no HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.task_fetch_jobs import FetchTaskJob, run_step


def test_run_step_stages_then_tasks_then_complete():
    client = MagicMock()
    client.search_project_stages.return_value = [{"id": "s1", "name": "Col1"}]
    client.query_tasks.side_effect = [
        ([{"id": "t1", "content": "A"}], None),
    ]

    job = FetchTaskJob(
        job_id="j1",
        status="running",
        page_size=50,
        projects=[{"id": "p1", "name": "Proj"}],
        project_index=0,
        tasks_by_project={},
        current_project_id="p1",
        current_project_name="Proj",
        cur_stages=None,
        cur_stage_map=None,
        cur_tasks=[],
        cur_page_token=None,
    )

    r1 = run_step(client, job)
    assert r1["failed"] is False
    assert r1["done"] is False
    assert job.cur_stages is not None
    client.search_project_stages.assert_called_once()

    r2 = run_step(client, job)
    assert r2["done"] is True
    assert job.status == "completed"
    assert "p1" in r2["tasksByProject"]
    assert len(r2["tasksByProject"]["p1"]["tasks"]) == 1


def test_cancelled_skips_api():
    client = MagicMock()
    job = FetchTaskJob(
        job_id="j2",
        status="cancelled",
        page_size=50,
        projects=[{"id": "p1", "name": "Proj"}],
        project_index=0,
        tasks_by_project={},
        current_project_id="p1",
        current_project_name="Proj",
        cur_stages=None,
        cur_stage_map=None,
        cur_tasks=[],
        cur_page_token=None,
    )
    r = run_step(client, job)
    assert r["cancelled"] is True
    client.search_project_stages.assert_not_called()
