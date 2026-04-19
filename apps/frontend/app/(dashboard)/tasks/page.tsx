"use client";

import { type ColumnDef } from "@tanstack/react-table";
import { useCallback, useRef, useState } from "react";

import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, apiJson } from "@/lib/api";
import { getOrCreateDebugSessionId } from "@/lib/debug-session";
import { useSessionStore } from "@/store/session-store";
import { useWorkspaceStore, type TasksBundle } from "@/store/workspace-store";

function buildSession() {
  const s = useSessionStore.getState();
  if (!s.teambitionToken || !s.tenantId) return undefined;
  return {
    token: s.teambitionToken,
    tenantId: s.tenantId,
    debugEnabled: s.debugEnabled,
    debugSessionId: s.debugEnabled ? getOrCreateDebugSessionId() : undefined,
  };
}

type FetchProgress = {
  projectIndex: number;
  projectTotal: number;
  currentProjectId: string | null;
  currentProjectName: string | null;
  currentProjectTaskCount: number;
  apiPhase: string;
  status: string;
};

type StepResponse = {
  done: boolean;
  cancelled: boolean;
  failed: boolean;
  error: string | null;
  tasksByProject: Record<string, TasksBundle>;
  progress: FetchProgress;
};

type StartResponse = { jobId: string; projectCount: number; status: string };

type JobSnapshot = {
  jobId: string;
  status: string;
  error: string | null;
  progress: FetchProgress;
  tasksByProject: Record<string, TasksBundle>;
};

type PreviewRow = { project: string; taskId: string; title: string };

const PREVIEW_LIMIT = 200;

function flattenPreview(tasksByProject: Record<string, TasksBundle> | null): PreviewRow[] {
  if (!tasksByProject) return [];
  const rows: PreviewRow[] = [];
  for (const [pid, bundle] of Object.entries(tasksByProject)) {
    const pname = bundle.name || pid;
    for (const t of bundle.tasks || []) {
      if (!t || typeof t !== "object") continue;
      const o = t as Record<string, unknown>;
      const content = o.content ?? o.title ?? "";
      rows.push({
        project: pname,
        taskId: String(o.id ?? ""),
        title: typeof content === "string" ? content : JSON.stringify(content),
      });
      if (rows.length >= PREVIEW_LIMIT) return rows;
    }
  }
  return rows;
}

const previewColumns: ColumnDef<PreviewRow>[] = [
  { accessorKey: "project", header: "项目" },
  { accessorKey: "taskId", header: "任务 ID" },
  { accessorKey: "title", header: "标题 / 内容" },
];

export default function TasksPage() {
  const token = useSessionStore((s) => s.teambitionToken);
  const tenant = useSessionStore((s) => s.tenantId);
  const setTasks = useWorkspaceStore((s) => s.setTasksByProject);
  const tasksByProject = useWorkspaceStore((s) => s.tasksByProject);
  const [message, setMessage] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<FetchProgress | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [lastStatus, setLastStatus] = useState<string | null>(null);
  const stopRequestedRef = useRef(false);

  const runSteps = useCallback(
    async (jid: string) => {
      const session = buildSession();
      if (!session) return;
      stopRequestedRef.current = false;
      setIsRunning(true);
      setMessage(null);
      try {
        while (!stopRequestedRef.current) {
          const r = await apiJson<StepResponse>(
            `/data/tasks/fetch/jobs/${jid}/step`,
            { method: "POST" },
            session,
          );
          setTasks(r.tasksByProject || {});
          setProgress(r.progress);
          setLastStatus(r.progress.status);

          if (r.failed) {
            setMessage(r.error || "拉取失败");
            break;
          }
          if (r.cancelled) {
            setMessage("已停止；可点击「恢复」从断点继续（服务器内存中的任务）。");
            break;
          }
          if (r.done) {
            setMessage("拉取完成；数据已写入工作区，可在「导出 Excel」页生成文件。");
            break;
          }
          await new Promise((res) => setTimeout(res, 0));
        }
      } catch (e) {
        setMessage((e as Error).message);
      } finally {
        setIsRunning(false);
      }
    },
    [setTasks],
  );

  const startFetch = async () => {
    const session = buildSession();
    if (!session) {
      setMessage("未认证");
      return;
    }
    setMessage(null);
    setProgress(null);
    try {
      const start = await apiJson<StartResponse>(
        "/data/tasks/fetch/jobs",
        { method: "POST", body: JSON.stringify({ page_size: 50 }) },
        session,
      );
      setJobId(start.jobId);
      setLastStatus(start.status);
      if (start.projectCount === 0) {
        setTasks({});
        setMessage("当前企业下没有项目。");
        return;
      }
      await runSteps(start.jobId);
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const stopFetch = async () => {
    const session = buildSession();
    if (!session || !jobId) return;
    stopRequestedRef.current = true;
    try {
      await apiFetch(`/data/tasks/fetch/jobs/${jobId}/cancel`, { method: "POST" }, session);
      const snap = await apiJson<JobSnapshot>(`/data/tasks/fetch/jobs/${jobId}`, {}, session);
      setTasks(snap.tasksByProject || {});
      setProgress(snap.progress);
      setLastStatus(snap.status);
      setMessage("已停止；可点击「恢复」继续拉取剩余项目。");
    } catch {
      /* ignore */
    }
  };

  const resumeFetch = async () => {
    const session = buildSession();
    if (!session || !jobId) return;
    try {
      await apiJson(`/data/tasks/fetch/jobs/${jobId}/resume`, { method: "POST" }, session);
      await runSteps(jobId);
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  if (!token || !tenant) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>需要认证</CardTitle>
          <CardDescription>请先在「认证」页完成换票。</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const totalTasks = tasksByProject
    ? Object.values(tasksByProject).reduce((n, b) => n + (b.tasks?.length || 0), 0)
    : 0;

  const pt = progress?.projectTotal ?? 0;
  const pi = progress?.projectIndex ?? 0;
  const phase = progress?.apiPhase ?? "";
  const barPct =
    pt > 0
      ? Math.min(
          100,
          (100 *
            (pi +
              (phase === "tasks" ? 0.35 : phase === "stages" ? 0.1 : phase === "done" ? 0 : 0))) /
            pt,
        )
      : 0;

  const previewRows = flattenPreview(tasksByProject);

  const canResume = Boolean(jobId && lastStatus === "cancelled" && !isRunning);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">任务</h1>
        <p className="text-sm text-zinc-400">
          使用分步接口拉取阶段与任务：每步一次开放平台调用，可查看进度、预览表格数据，并支持停止与恢复。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>批量拉取（分步）</CardTitle>
          <CardDescription>
            POST /api/v1/data/tasks/fetch/jobs → /jobs/&#123;jobId&#125;/step（循环）· 停止 · 恢复
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void startFetch()} disabled={isRunning}>
              {isRunning ? "拉取中…" : "开始拉取"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void stopFetch()}
              disabled={!isRunning}
            >
              停止
            </Button>
            <Button type="button" variant="outline" onClick={() => void resumeFetch()} disabled={!canResume}>
              恢复
            </Button>
          </div>

          {progress && pt > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-zinc-400">
                <span>
                  已完成项目 {phase === "done" ? pt : pi} / {pt} · 阶段 {phase}
                  {progress.currentProjectName ? ` · ${progress.currentProjectName}` : ""}
                </span>
                <span>当前项目已累积任务 {progress.currentProjectTaskCount} 条</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded bg-zinc-800">
                <div
                  className="h-full rounded bg-blue-600 transition-[width] duration-300"
                  style={{ width: `${barPct}%` }}
                />
              </div>
            </div>
          )}

          {jobId && (
            <p className="font-mono text-xs text-zinc-500">
              jobId: {jobId} · 状态 {lastStatus ?? "—"}
            </p>
          )}

          {message && <p className="text-sm text-zinc-300">{message}</p>}
          <p className="text-sm text-zinc-500">
            工作区缓存：{tasksByProject ? Object.keys(tasksByProject).length : 0} 个项目，约 {totalTasks}{" "}
            条任务（与导出 Excel 使用同一数据结构）。
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>表格预览（Excel 行数据）</CardTitle>
          <CardDescription>展示前 {PREVIEW_LIMIT} 行，字段与导出任务 Sheet 同源。</CardDescription>
        </CardHeader>
        <CardContent>
          {previewRows.length === 0 ? (
            <p className="text-sm text-zinc-500">尚无任务数据，请先开始拉取。</p>
          ) : (
            <DataTable data={previewRows} columns={previewColumns} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
