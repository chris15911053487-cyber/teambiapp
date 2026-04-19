"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiJson } from "@/lib/api";
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

export default function TasksPage() {
  const token = useSessionStore((s) => s.teambitionToken);
  const tenant = useSessionStore((s) => s.tenantId);
  const setTasks = useWorkspaceStore((s) => s.setTasksByProject);
  const tasksByProject = useWorkspaceStore((s) => s.tasksByProject);
  const [message, setMessage] = useState<string | null>(null);

  const fetchAll = useMutation({
    mutationFn: async () => {
      const session = buildSession();
      if (!session) throw new Error("未认证");
      return apiJson<{ tasksByProject: Record<string, TasksBundle>; projectsCount: number }>(
        "/data/tasks/fetch-all",
        { method: "POST", body: JSON.stringify({ page_size: 50 }) },
        session,
      );
    },
    onSuccess: (data) => {
      setTasks(data.tasksByProject || {});
      setMessage(`已拉取 ${data.projectsCount} 个项目的任务。`);
    },
    onError: (e: Error) => setMessage(e.message),
  });

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">任务</h1>
        <p className="text-sm text-zinc-400">
          调用后端聚合接口，按项目拉取阶段与任务（与 Streamlit 版逻辑一致）。大量项目时可能耗时较长。
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>批量拉取</CardTitle>
          <CardDescription>POST /api/v1/data/tasks/fetch-all</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            type="button"
            onClick={() => fetchAll.mutate()}
            disabled={fetchAll.isPending}
          >
            {fetchAll.isPending ? "拉取中…" : "拉取全部项目任务和阶段"}
          </Button>
          {message && <p className="text-sm text-zinc-300">{message}</p>}
          <p className="text-sm text-zinc-500">
            当前缓存：{tasksByProject ? Object.keys(tasksByProject).length : 0} 个项目，约{" "}
            {totalTasks} 条任务。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
