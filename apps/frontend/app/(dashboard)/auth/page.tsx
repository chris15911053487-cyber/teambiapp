"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiJson } from "@/lib/api";
import { useSessionStore } from "@/store/session-store";
import type { TokenResponse } from "@teambition/types";

export default function AuthPage() {
  const setAuth = useSessionStore((s) => s.setAuth);
  const clear = useSessionStore((s) => s.clear);
  const companyName = useSessionStore((s) => s.companyName);
  const [company, setCompany] = useState("");
  const [passphrase, setPassphrase] = useState("");

  const companiesQuery = useQuery({
    queryKey: ["companies"],
    queryFn: () => apiJson<{ companies: { name: string }[] }>("/companies"),
  });

  const tokenMutation = useMutation({
    mutationFn: (body: { company_name: string; passphrase: string }) =>
      apiJson<TokenResponse>("/auth/token", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      setAuth(data);
      setPassphrase("");
    },
  });

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">认证</h1>
        <p className="mt-1 text-sm text-zinc-400">
          选择企业并输入当日暗号（YYYYMMDD）换取 Access Token。凭证由服务端环境变量注入，不在此展示。
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>企业</CardTitle>
          <CardDescription>来自后端 TB_COMPANY_PROFILES_JSON</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {companiesQuery.isError && (
            <p className="text-sm text-red-400">
              无法加载企业列表（请确认后端已配置 TB_COMPANY_PROFILES_JSON 且已启动）。
            </p>
          )}
          <div className="space-y-2">
            <Label htmlFor="company">公司</Label>
            <select
              id="company"
              className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-100"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            >
              <option value="">请选择</option>
              {(companiesQuery.data?.companies || []).map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="pass">暗号</Label>
            <Input
              id="pass"
              type="password"
              autoComplete="off"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              disabled={!company || !passphrase || tokenMutation.isPending}
              onClick={() =>
                tokenMutation.mutate({ company_name: company, passphrase })
              }
            >
              {tokenMutation.isPending ? "获取中…" : "验证并获取 Token"}
            </Button>
            <Button type="button" variant="outline" onClick={() => clear()}>
              清除会话
            </Button>
          </div>
          {tokenMutation.isError && (
            <p className="text-sm text-red-400">
              {(tokenMutation.error as Error).message || "换票失败"}
            </p>
          )}
          {tokenMutation.isSuccess && (
            <p className="text-sm text-emerald-400">Token 已写入本地会话。</p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>当前状态</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-zinc-400">
          已选企业展示名：<span className="text-zinc-100">{companyName || "—"}</span>
        </CardContent>
      </Card>
    </div>
  );
}
