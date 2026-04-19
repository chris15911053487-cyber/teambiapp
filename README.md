# Teambition 数据工作台

通过 [Teambition 开放平台](https://open.teambition.com/docs) 拉取企业、项目、任务（含阶段）与工时，并导出 Excel。本仓库提供 **两种使用方式**：

| 方式 | 说明 | 默认端口 |
|------|------|----------|
| **Streamlit** | 单文件应用，适合快速试用与配置化接口 | `8501` |
| **Next.js + FastAPI** | Turborepo 单体仓库中的前后端分离栈 | 前端 `3000`，后端 `8000` |

共享逻辑在 `packages/teambition-client`（Python Open API 客户端）。

---

## 功能一览

### Streamlit（`app.py`）

- **认证**：选择企业（凭证在服务端/配置中绑定，界面不展示 AppId/Secret/企业ID），暗号换票；暗号为密码输入。
- **数据中心**：企业信息、项目列表（游标分页）、任务 + 阶段映射、工时聚合；支持单项目明细与动态 `TeambitionAPI.call(...)`。
- **接口配置**：维护 endpoint、参数、resolver，可测试调用与 JSON 持久化。
- **API 记录**：请求/响应/cURL 集中展示，支持搜索与复制（列表中 Header 脱敏，一键复制含完整 Token）。
- **导出 Excel**：多 Sheet（企业、项目、任务、工时、阶段），pandas + openpyxl。

### 现代栈（`apps/frontend` + `apps/backend`）

- **认证 / 工作区**：换票后缓存 Token 与拉取结果。
- **任务**：分步拉取（进度、表格预览、停止/恢复），见下文「分步拉取任务」。
- **导出 Excel**：使用工作区缓存数据生成文件（与 Streamlit 思路一致）。

---

## Streamlit 快速开始

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器：<http://localhost:8501>

### Docker（Streamlit）

```bash
docker build -t teambition-app .
docker run -p 8501:8501 teambition-app
# 或
docker compose up -d
```

### 界面导航（与 `app.py` 一致）

| 菜单 | 作用 |
|------|------|
| 工作台 | 总览与快捷操作 |
| 数据 | 项目、任务、工时批量拉取 |
| 任务 | 阶段（Kanban 列）+ 任务；单项目快速查询 |
| 配置 | 暗号换票 |
| 关于 | 说明 |

侧边栏可开启 **「显示 API 请求报文」**：记录约 20 条请求；**任务** 页可展开查看。遇权限问题时，用报文与开放平台调试页逐项对照（URL、`X-Tenant-Id`、`filter`、`pageToken` 等）。**一键复制** 含完整 Bearer Token，请勿外泄。

### 认证与凭证

- 多企业在 `config_sidebar.py` 的 `COMPANY_PROFILES` 中配置；换票：`appSecret` 签发 HS256 应用 JWT → `POST https://open.teambition.com/api/appToken`。
- 开放平台需勾选项目阶段列表、任务等相关权限；**保存权限后须重新换票**。

### 数据页标签

1. **操作面板**：一键全量，或分步（企业、项目向导、全项目任务、工时等）。
2. **数据展示**：表格与折叠区（项目列表可能仅预览部分以控制性能）。
3. **导出 Excel**：生成后浏览器下载（文件名带时间戳）。

---

## 现代栈（Next.js + FastAPI）

Monorepo：`apps/frontend`、`apps/backend`、`packages/teambition-client`、`packages/types`。Streamlit 入口仍保留在仓库根目录。

### 环境变量（后端）

运行前配置 `TB_COMPANY_PROFILES_JSON`（JSON 数组，每项含 `name`、`app_id`、`app_secret`、`tenant_id`）。勿将真实密钥提交到公开仓库。可选：`REDIS_URL`、`JWT_SECRET`、`CORS_ORIGINS`。

前端：`NEXT_PUBLIC_API_URL` 指向后端（如 `http://127.0.0.1:8000`）。

### 本地开发

```bash
python3 -m pip install -e ./packages/teambition-client
python3 -m pip install -r apps/backend/requirements.txt -r apps/backend/requirements-dev.txt

# 终端 1：API
cd apps/backend && PYTHONPATH=../../packages/teambition-client/src python3 -m uvicorn app.main:app --reload --port 8000

# 终端 2：Web
cd apps/frontend && echo 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000' > .env.local && npm install && npm run dev

# 或仓库根目录（需已安装 turbo）
npm run dev
```

### 分步拉取任务

大量项目时，一次性 `POST /api/v1/data/tasks/fetch-all` 会长时间阻塞。可使用 **分步任务**（每步一次开放平台调用：某项目的阶段，或一页任务）：

| 端点 | 说明 |
|------|------|
| `POST /api/v1/data/tasks/fetch/jobs` | Body：`{ "page_size": 50 }`。返回 `jobId`、`projectCount`（会先拉项目列表）。 |
| `POST /api/v1/data/tasks/fetch/jobs/{jobId}/step` | 执行一步；返回 `done`、`cancelled`、`failed`、`tasksByProject`、`progress`。循环直至结束。 |
| `GET /api/v1/data/tasks/fetch/jobs/{jobId}` | 当前进度与合并后的数据。 |
| `POST .../cancel` | 停止；已拉数据保留。 |
| `POST .../resume` | 仅 **已停止** 时可从断点继续。 |

**注意**：`jobId` 仅存于 **后端进程内存**；重启后需重新「开始拉取」。兼容保留 `POST /data/tasks/fetch-all`。

前端路径 **`/tasks`**：进度条、阶段说明、前 200 行表格预览、开始/停止/恢复；数据进 Zustand，**导出 Excel** 页共用。

相关代码：`apps/backend/app/task_fetch_jobs.py`、`apps/backend/app/routers/data.py`、`apps/frontend/app/(dashboard)/tasks/page.tsx`。

### Docker（现代栈）

```bash
docker compose --profile modern up --build
```

默认 `docker compose up` 仅 **Streamlit（8501）**。`--profile modern` 可启动 Redis、后端、前端；`--profile worker` 可启 Celery 示例任务。

---

## 技术说明

### 任务：`GET /v3/task/query`

与官方 **[查询任务](https://open.teambition.com/docs/apis/6321c6d2912d20d3b5a4a7b8)** 同一路径。

- **按项目列表**：`filter`（JSON，含 `projectId`，可选 `stageId`）+ `pageSize` + `pageToken` 游标分页。
- **按 ID 查详情**：`taskId` / `shortIds` / `parentTaskId`（与 `filter` 分页二选一）。

### 项目分页

`/v3/project/query` 使用 **游标**（`pageToken` / `nextPageToken`），勿仅依赖数字 `page` 翻页。

### 阶段与任务

- 阶段：`/v3/project/{projectId}/stage/search`（`search_project_stages`）。
- 任务列表：同上 `/v3/task/query`，参数不同而已。

实现参考：`app.py` 与 `packages/teambition-client` 中的 `TeambitionAPI`。

---

## 目录结构

```
teambition-app/
├── app.py                    # Streamlit 主程序
├── config_sidebar.py         # 换票与企业配置
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── tests.py                  # Streamlit 相关测试
├── apps/
│   ├── backend/              # FastAPI（app/main.py, routers/, task_fetch_jobs.py）
│   └── frontend/             # Next.js App Router
├── packages/
│   ├── teambition-client/    # 共享 Python 客户端
│   └── types/                  # 共享 TS 类型
└── README.md
```

---

## 测试与 CI

本地：

```bash
pip install -r requirements-dev.txt
pytest
```

后端单独（与 CI 一致）：

```bash
cd apps/backend && PYTHONPATH=../../packages/teambition-client/src:. python3 -m pytest tests -q
```

GitHub Actions（`.github/workflows/ci-cd.yml`）：根目录 pytest、client 包测试、backend 测试；主分支可选构建镜像与部署。Secrets（镜像仓库、SSH 等）见工作流注释。

---

## 常见问题

**Token 过期？**  
在 Streamlit **配置** 页或现代栈认证流程重新换票。

**数据存在哪？**  
Streamlit：会话状态；现代栈：浏览器侧状态 + 导出文件下载到本机。分步任务的 `jobId` 仅服务端内存。

**容器日志**

```bash
docker logs -f teambition-app
docker compose logs -f
```

---

## 安全提示

1. 勿将 App Secret、Token 提交到公开仓库；生产环境用环境变量或密钥管理。  
2. 生产建议 HTTPS 与访问控制。  
3. 示例中的「暗号」仅作演示，正式环境请换更安全的鉴权。

---

## 文档与反馈

- Teambition 开放平台：<https://open.teambition.com/docs>  
- Issue：本仓库

## 许可证

MIT License
