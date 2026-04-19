"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { getOrCreateDebugSessionId } from "@/lib/debug-session";
import { useSessionStore } from "@/store/session-store";
import { useWorkspaceStore } from "@/store/workspace-store";

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

export default function ExportPage() {
  const token = useSessionStore((s) => s.teambitionToken);
  const tenant = useSessionStore((s) => s.tenantId);
  const org = useWorkspaceStore((s) => s.org);
  const projects = useWorkspaceStore((s) => s.projects);
  const tasksByProject = useWorkspaceStore((s) => s.tasksByProject);
  const worktimeByTask = useWorkspaceStore((s) => s.worktimeByTask);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const download = async () => {
    const session = buildSession();
    if (!session) {
      setMsg("请先认证");
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const body = {
        org,
        projects: projects || [],
        tasksByProject: tasksByProject || {},
        worktimeByTask: worktimeByTask || {},
      };
      const res = await apiFetch(
        "/export/excel",
        { method: "POST", body: JSON.stringify(body) },
        session,
      );
      if (!res.ok) {
        setMsg(await res.text());
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "teambition_export.xlsx";
      a.click();
      URL.revokeObjectURL(url);
      setMsg("已开始下载。");
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!token || !tenant) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>需要认证</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">导出 Excel</h1>
        <p className="text-sm text-zinc-400">
          使用工作区缓存的数据生成多 Sheet 文件（与 Streamlit 导出思路一致）。
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>生成文件</CardTitle>
          <CardDescription>
            企业：{org ? "有" : "无"} · 项目：{projects?.length ?? 0} · 任务项目数：{" "}
            {tasksByProject ? Object.keys(tasksByProject).length : 0}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button type="button" onClick={download} disabled={busy}>
            {busy ? "生成中…" : "生成并下载 Excel"}
          </Button>
          {msg && <p className="text-sm text-zinc-400">{msg}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
