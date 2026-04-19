"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiJson } from "@/lib/api";
import { getOrCreateDebugSessionId } from "@/lib/debug-session";
import { useSessionStore } from "@/store/session-store";
import type { ApiConfigRow } from "@teambition/types";

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

export default function ConfigPage() {
  const token = useSessionStore((s) => s.teambitionToken);
  const tenant = useSessionStore((s) => s.tenantId);
  const [text, setText] = useState("[]");
  const [status, setStatus] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["api-configs", token, tenant],
    enabled: !!token && !!tenant,
    queryFn: async () => {
      const session = buildSession()!;
      return apiJson<{ configs: ApiConfigRow[] }>("/api-configs", {}, session);
    },
  });

  useEffect(() => {
    if (q.data?.configs) {
      setText(JSON.stringify(q.data.configs, null, 2));
    }
  }, [q.data]);

  const save = useMutation({
    mutationFn: async () => {
      const session = buildSession()!;
      let configs: ApiConfigRow[];
      try {
        configs = JSON.parse(text) as ApiConfigRow[];
      } catch {
        throw new Error("JSON 格式无效");
      }
      return apiJson("/api-configs", { method: "PUT", body: JSON.stringify({ configs }) }, session);
    },
    onSuccess: () => setStatus("已保存到 Redis（若已配置 REDIS_URL）。"),
    onError: (e: Error) => setStatus(e.message),
  });

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
        <h1 className="text-2xl font-semibold text-white">接口配置</h1>
        <p className="text-sm text-zinc-400">
          编辑 JSON 后保存；后端将写入 Redis 并在后续 Teambition 请求中使用（无 Redis 时仅内存默认）。
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>API registry</CardTitle>
          <CardDescription>GET/PUT /api/v1/api-configs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            className="min-h-[420px] w-full rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-200"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => q.refetch()} variant="outline">
              重新加载
            </Button>
            <Button type="button" onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending ? "保存中…" : "保存"}
            </Button>
          </div>
          {status && <p className="text-sm text-zinc-400">{status}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
