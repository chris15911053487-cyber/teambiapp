"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { apiFetch, apiJson } from "@/lib/api";
import { getOrCreateDebugSessionId } from "@/lib/debug-session";
import { useSessionStore } from "@/store/session-store";
import type { DebugLogEntry } from "@teambition/types";

type LogsResponse = {
  logs: DebugLogEntry[];
  bundles: string[];
  curls: string[];
};

function buildSession(debug: boolean) {
  const s = useSessionStore.getState();
  if (!s.teambitionToken || !s.tenantId) return undefined;
  return {
    token: s.teambitionToken,
    tenantId: s.tenantId,
    debugEnabled: debug,
    debugSessionId: debug ? getOrCreateDebugSessionId() : undefined,
  };
}

export default function ApiDebugPage() {
  const token = useSessionStore((s) => s.teambitionToken);
  const tenant = useSessionStore((s) => s.tenantId);
  const debugEnabled = useSessionStore((s) => s.debugEnabled);
  const setDebugEnabled = useSessionStore((s) => s.setDebugEnabled);
  const [copied, setCopied] = useState<number | null>(null);

  const [sessionId, setSessionId] = useState("");
  useEffect(() => {
    setSessionId(getOrCreateDebugSessionId());
  }, []);

  const logsQuery = useQuery({
    queryKey: ["debug-logs", sessionId, token, tenant, debugEnabled],
    enabled: !!token && !!tenant && debugEnabled && !!sessionId,
    queryFn: async () => {
      const session = buildSession(true)!;
      return apiJson<LogsResponse>(
        `/debug/logs?session_id=${encodeURIComponent(sessionId)}`,
        {},
        session,
      );
    },
    refetchInterval: debugEnabled ? 2500 : false,
  });

  const clearMutation = async () => {
    const session = buildSession(true);
    if (!session) return;
    const res = await apiFetch(
      `/debug/logs?session_id=${encodeURIComponent(sessionId)}`,
      { method: "DELETE" },
      session,
    );
    if (!res.ok) return;
    logsQuery.refetch();
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
        <h1 className="text-2xl font-semibold text-white">API 调试</h1>
        <p className="text-sm text-zinc-400">
          打开记录后，所有带 <code className="text-blue-300">X-Debug-Session</code> 的 Teambition
          请求会写入后端环形缓冲（最近 20 条），并在此展示完整报文与 cURL。
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>记录开关</CardTitle>
          <CardDescription>Session ID: {sessionId || "（刷新后生成）"}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              id="dbg"
              type="checkbox"
              className="size-4 accent-blue-600"
              checked={debugEnabled}
              onChange={(e) => setDebugEnabled(e.target.checked)}
            />
            <Label htmlFor="dbg">记录 API 请求</Label>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => clearMutation()}>
            清空记录
          </Button>
        </CardContent>
      </Card>
      {!debugEnabled ? (
        <p className="text-sm text-zinc-500">开启「记录 API 请求」后，发起数据中心等操作即可看到日志。</p>
      ) : logsQuery.isLoading ? (
        <p className="text-sm text-zinc-400">加载中…</p>
      ) : logsQuery.isError ? (
        <p className="text-sm text-red-400">{(logsQuery.error as Error).message}</p>
      ) : (
        <div className="space-y-3">
          {(logsQuery.data?.logs || []).map((log, i) => (
            <Card key={i}>
              <CardHeader className="py-3">
                <CardTitle className="text-sm font-medium text-zinc-200">
                  {String(log.method)} {String(log.endpoint)}{" "}
                  <span className="text-zinc-500">HTTP {log.http_status}</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={async () => {
                      const curl = logsQuery.data?.curls?.[i];
                      if (curl) {
                        await navigator.clipboard.writeText(curl);
                        setCopied(i);
                        setTimeout(() => setCopied(null), 2000);
                      }
                    }}
                  >
                    {copied === i ? "已复制 cURL" : "复制 cURL"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={async () => {
                      const b = logsQuery.data?.bundles?.[i];
                      if (b) {
                        await navigator.clipboard.writeText(b);
                        setCopied(i + 1000);
                        setTimeout(() => setCopied(null), 2000);
                      }
                    }}
                  >
                    {copied === i + 1000 ? "已复制完整报文" : "复制完整报文"}
                  </Button>
                </div>
                <pre className="max-h-48 overflow-auto rounded-lg bg-zinc-900 p-3 text-xs text-zinc-400">
                  {(logsQuery.data?.bundles?.[i] || "").slice(0, 4000)}
                </pre>
              </CardContent>
            </Card>
          ))}
          {(logsQuery.data?.logs || []).length === 0 && (
            <p className="text-sm text-zinc-500">暂无记录。请在「数据中心」发起请求。</p>
          )}
        </div>
      )}
    </div>
  );
}
