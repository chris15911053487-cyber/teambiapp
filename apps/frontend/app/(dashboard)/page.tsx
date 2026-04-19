import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-zinc-800 bg-gradient-to-br from-blue-950/80 via-zinc-950 to-zinc-950 p-8 shadow-xl">
        <h1 className="text-3xl font-bold tracking-tight text-white">Teambition 数据工作台</h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          前后端分离版本：FastAPI 提供 Open API 代理与导出，Next.js 提供现代化界面与 TanStack
          Query 数据流。
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/auth">开始认证</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/data">数据中心</Link>
          </Button>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>快速迭代</CardTitle>
            <CardDescription>接口配置存 Redis，动态 call 与调试日志</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-zinc-400">
            在「接口配置」中编辑 registry，保存后立即影响下一次请求。
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>美观 UX</CardTitle>
            <CardDescription>暗色主题、表格排序、卡片布局</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-zinc-400">
            Radix + Tailwind 组件，与 Streamlit 版能力对齐并更易扩展。
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>API 调试</CardTitle>
            <CardDescription>完整报文与 cURL</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-zinc-400">
            打开记录开关后，集中查看请求并在 Postman 中复现。
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
