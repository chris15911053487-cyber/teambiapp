"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Database,
  FileSpreadsheet,
  KeyRound,
  ListTree,
  Settings2,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useSessionStore } from "@/store/session-store";

const nav = [
  { href: "/auth", label: "认证", icon: KeyRound },
  { href: "/data", label: "数据中心", icon: Database },
  { href: "/tasks", label: "任务", icon: ListTree },
  { href: "/api-debug", label: "API 调试", icon: Sparkles },
  { href: "/config", label: "接口配置", icon: Settings2 },
  { href: "/export", label: "导出", icon: FileSpreadsheet },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const token = useSessionStore((s) => s.teambitionToken);
  const tenant = useSessionStore((s) => s.tenantId);
  const company = useSessionStore((s) => s.companyName);

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950/95 p-4 md:flex">
        <div className="mb-6 rounded-lg bg-gradient-to-br from-blue-900/80 to-blue-700/60 p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-blue-200/90">
            Teambition
          </div>
          <div className="text-lg font-semibold text-white">数据工作台</div>
          <p className="mt-1 text-xs text-blue-100/80">Next.js + FastAPI</p>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-600 text-white"
                    : "text-zinc-300 hover:bg-zinc-900 hover:text-white",
                )}
              >
                <Icon className="size-4 opacity-90" />
                {label}
              </Link>
            );
          })}
        </nav>
        <Separator className="my-4 bg-zinc-800" />
        <div className="space-y-2 text-xs text-zinc-400">
          <div className="flex flex-wrap items-center gap-2">
            <span>Token</span>
            <Badge variant={token ? "success" : "outline"}>
              {token ? "已配置" : "未配置"}
            </Badge>
          </div>
          <div className="truncate" title={company || ""}>
            企业：{company || "—"}
          </div>
          <div className="truncate font-mono text-[10px]" title={tenant || ""}>
            Tenant：{tenant ? `${tenant.slice(0, 8)}…` : "—"}
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-6xl px-4 py-8 md:px-8">{children}</div>
      </main>
    </div>
  );
}
