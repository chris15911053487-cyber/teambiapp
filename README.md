# Teambition 数据工作台

基于 [Streamlit](https://streamlit.io) 的 Teambition Open API 图形化工具，用于拉取企业、项目、任务与工时数据，并导出为 Excel。

## 功能特性 (重构后)

- **认证**：在页面选择企业（应用凭证由服务端绑定，界面不展示 AppId/Secret/企业ID），再输入暗号换票；暗号输入为密码框且不提示生成规则。
- **数据中心**：统一拉取企业信息、项目列表 (游标分页)、任务查询 (filter + stage mapping)、工时聚合。支持单个项目明细查询。
- **API记录**：所有请求 (URL, Headers, Params, Response, cURL) 集中显示，支持搜索、复制、过滤、清空。
- **接口配置**：**新** 可视化 UI 维护端点、参数、resolver (动态参数解析如 build_task_filter)。支持测试调用、JSON 持久化，无需修改代码即可扩展接口。
- **导出 Excel**：多 Sheet (企业、项目、任务、工时、阶段)，使用 pandas/openpyxl。
- **权限友好**：保留增强错误提示 (具体权限指引)。
- **动态客户端**： `TeambitionAPI.call("query_tasks", project_id=xxx)` 使用 registry + resolvers。
- **Docker**：支持容器化部署。

**核心改进**：消除「数据」和「任务」菜单重叠；接口地址/参数/取值方法可通过 UI 配置维护；API 记录独立页面。所有调用自动调试记录。

**核心解决**：权限问题通过详细指引和记录快速排查；配置化使维护更灵活。

---

## 界面说明（与当前 `app.py` 一致）

### 左侧导航

| 菜单 | 说明 |
|------|------|
| **工作台** | 数据总览与快捷操作 |
| **数据** | 项目、任务、工时批量拉取 |
| **任务** | **新增**：专注任务查询，支持按项目拉取阶段（Kanban列）+ 任务，支持单个项目快速查询 |
| **配置** | 暗号验证后获取 Access Token（见下文） |
| **关于** | 简要说明与技术栈 |

侧边栏底部会显示 **Token / 企业 ID** 是否已配置。

其下 **调试工具** 区域：

| 开关 | 说明 |
|------|------|
| **显示 API 请求报文** | 开启后，每次通过 `TeambitionAPI._request` 调用开放平台接口时，会记录最近约 20 条请求；在 **「任务」** 页以折叠面板展示。界面中的 JSON 仍为 **脱敏** Headers；点击 **「一键复制完整报文」** 可复制含 **完整 Authorization**、响应体与 **cURL** 的纯文本（另提供文本框备用全选复制）。可一键清空记录。 |

**重要**：**任务页面** 专门优化了权限问题，如果遇到「没有权限」，请重点检查开放平台应用权限配置；同时打开上述开关，将报文与 [开放平台](https://open.teambition.com) 调试页对比（应用 ID、租户 ID、路径与参数是否一致）。

### 数据页主区域标签

1. **操作面板**  
   - **获取全部数据**：依次拉取企业信息、全部项目、全部项目任务，并在有任务数据时拉取工时。  
   - **分步操作**：拉取企业信息、项目清单向导、拉取全部项目任务、拉取工时等。  
   - **项目清单向导**：先请求第一页做预估，确认后再按游标分页拉取完整项目列表，并支持本地分页表格浏览。

2. **数据展示**  
   表格与折叠区展示已拉取的企业、项目（界面为控制性能可能仅预览部分项目）、各项目任务、工时等。

3. **导出 Excel**  
   查看导出统计，点击生成后出现浏览器 **下载** 按钮；文件名带时间戳。

---

## 快速开始

### 本地运行（开发）

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器访问：<http://localhost:8501>

### Docker

```bash
docker build -t teambition-app .
docker run -p 8501:8501 teambition-app
```

或使用 Compose：

```bash
docker-compose up -d
```

访问：<http://localhost:8501>

---

## 使用流程

### 1. 获取 Token（认证页）

1. 在 **「认证」** 页选择企业（多企业时在 `config_sidebar.py` 的 `COMPANY_PROFILES` 中维护；界面仅显示公司名，不展示 AppId/Secret/企业ID）。
2. 输入暗号并提交 **「验证并获取 Token」**（暗号为密码输入，界面不说明生成规则）。  
   换票逻辑：本地用 `appSecret` 签发 HS256 应用 JWT，再 `POST https://open.teambition.com/api/appToken`（与 `@tng/teambition-openapi-sdk` 的 `getAppAccessToken` 思路一致）。

成功后会写入会话中的 **Access Token**；可在展开区查看完整 Token（请勿外泄）。

### 2. 企业与凭证

各企业凭证在 `config_sidebar.py` 的 `COMPANY_PROFILES` 中配置；前台不渲染这些字段。

### 使用流程 (新菜单)

1. **认证** 页：选择公司 → 输入暗号 → 获取 Token（凭证随所选企业自动写入会话，不在界面展示）。
2. **数据中心** 页：
   - 操作面板：点击按钮拉取企业信息、项目、全部任务+阶段、工时。
   - 数据明细：选择项目查询详情 (使用动态 call)。
   - 导出 Excel：生成多 Sheet 文件。
3. **接口配置** 页：查看/编辑接口 (endpoint, resolvers, params)，测试调用。
4. **API记录** 页：查看所有请求日志、复制 cURL 用于 Postman 调试。

**权限问题解决**：错误提示具体到所需权限 (`tb-core:project.stage:list` 等)；结合 API记录页对比开放平台调试结果。保存权限后重新在认证页获取 Token。

### 4. 查看发往 Teambition 的请求报文（可选）

排查「调试器里成功、本应用里 403」等问题时：

1. 在侧边栏打开 **「显示 API 请求报文」**。
2. 进入 **「任务」** 页，执行一次「拉取全部项目任务和阶段」或「单个项目快速查询」。
3. 在页面顶部 **「API 请求记录」** 中展开条目，核对：
   - 完整 URL 是否与文档一致（如 `/api/v3/project/{projectId}/stage/search`）；
   - `X-Tenant-Id`、`X-Tenant-type` 是否与预期企业一致；
   - Query 中的 `filter`（JSON）、`pageSize`、`pageToken` 等；
   - 响应中的 `code` 与 `errorMessage`（与开放平台返回对照）。
4. 点击 **「一键复制完整报文」**，将整段文本粘贴到 **Postman** → **Import** → **Raw text**（可识别其中的 **cURL**），或与开放平台调试结果逐字段对比。

说明：列表里 JSON 展示的 `Authorization` 仍为脱敏；**一键复制内容含完整 Bearer Token**，请勿泄露。若浏览器拦截剪贴板 API，请用同一条目下的文本框 **Ctrl+A / Cmd+A** 全选复制。会话内最多保留约 20 条，刷新页面或清空记录可重置。

---

## 技术说明

### 任务接口：`GET /v3/task/query`

统一使用 **[查询任务详情](https://open.teambition.com/docs/apis/6321c6d2912d20d3b5a4a7b8)** 同一路径：`https://open.teambition.com/api/v3/task/query`。

- **按项目拉任务列表**：query 使用 `filter`（JSON 字符串，内含 `projectId`，可选 `stageId`）+ `pageSize` + `pageToken` 游标分页。实现见 `get_project_tasks()`、`query_tasks(project_id=...)`。
- **按已知任务 ID 查详情**：query 使用文档中的 `taskId` / `shortIds` / `parentTaskId`（与 `filter` 分页模式二选一调用）。实现见 `query_tasks(task_ids=...)` 等。

若开放平台返回参数错误，请在调试面板核对 `filter` 是否与线上一致，并确认已勾选任务/项目相关权限。

---

- **项目分页**：Open API v3 的 `/v3/project/query` 使用 **游标分页** (`pageToken`/`nextPageToken`)。
- **任务查询**：`search_project_stages()`（`/v3/project/{projectId}/stage/search`）和 `query_tasks()` / `get_project_tasks()`，任务请求 URL 均为 `/v3/task/query`，区别在 query 参数（见上）。
  - 自动获取阶段信息并映射到任务的 `stageName`。
  - 增强 `_request()` + 调试面板（一键复制含完整 Token 的 cURL，便于 Postman 导入）。
- **新增「任务」菜单**：独立页面，专注任务+阶段查询，解决常见「已授权但提示无权限」问题。
- **Excel**：使用 `pandas` + `openpyxl` 多 Sheet 导出（新增阶段信息 sheet）。

主要文件：

- `app.py`：界面、增强的 `TeambitionAPI` 类（新增 `search_project_stages`、`query_tasks`、`get_all_project_tasks`）、`tasks_page()`  
- `config_sidebar.py`：Token 获取逻辑

**权限关键点**：必须在开放平台为应用勾选「项目自定义列表查看权限」和「任务相关权限」，保存后重新生成 Token。

---

## CI/CD 自动化

本项目可使用 GitHub Actions 做测试与部署（以仓库内 `.github/workflows` 为准）。

### 自动化流程（示例）

- **PR / 推送**：运行测试与质量检查  
- **主分支**：可选构建镜像并部署（取决于你的工作流配置）

### GitHub Secrets（若使用腾讯云镜像 + SSH 部署）

在仓库 **Settings → Secrets and variables → Actions** 中配置，例如：

**镜像仓库**

- `REGISTRY`：如 `ccr.ccs.tencentyun.com`  
- `TENCENT_CLOUD_ID`、`PASSWORD`：登录凭据  
- `IMAGE_NAME`：完整镜像路径  

**服务器**

- `SERVER_HOST`、`SERVER_USER`、`SSH_PRIVATE_KEY`、`SERVER_PORT`（可选）

具体步骤与脚本以仓库内 `deploy.sh`、工作流 YAML 为准。

### 测试

```bash
pip install -r requirements-dev.txt
pytest
```

---

## 项目结构（重构后）

```
teambition-app/
├── app.py                 # 主应用（Streamlit UI + TeambitionAPI + 新 dynamic call / pages: auth_page, data_center_page, api_config_page, api_records_page）
├── config_sidebar.py      # Token 获取 (JWT, get_app_token) - 集成到认证页
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pytest.ini
├── deploy.sh
├── tests.py
└── README.md
```

**主要变更**：
- `TeambitionAPI` 扩展了 `call(name, **context)` 动态方法 + registry (DEFAULT_API_CONFIGS, resolve_param)。
- 新页面：`api_config_page()` (data_editor + test), `data_center_page()` (合并), `api_records_page()`, `auth_page()`。
- Session state 管理 api_configs, 所有调用自动调试。

---

## 环境变量（可选）

可参考 `.env.example`。是否在应用启动时自动读取 Token / Tenant，取决于你是否在代码中接入 `python-dotenv` 与对应变量名；当前主流程以页面会话为准。

---

## 常见问题

**Q：Token 过期怎么办？**  
A：应用 Token 有效期以开放平台为准，过期后回到 **配置** 页用当日暗号重新获取。

**Q：数据存在哪里？**  
A：拉取结果在 Streamlit **会话状态**中；Excel 通过浏览器下载到本机下载目录。Docker 若挂载 `./data`，用途以你的 Compose 配置为准。

**Q：如何看容器日志？**  

```bash
docker logs -f teambition-app
# 或
docker-compose logs -f
```

---

## 安全提示

1. **不要将真实 App Secret、Token 提交到公开仓库。** 若代码中含固定凭证，部署前请改为环境变量或私密配置，并轮换密钥。  
2. 生产环境建议 **HTTPS**、访问控制（防火墙 / 认证）。  
3. 暗号仅用于当前示例的日更校验，正式环境请改用更安全的登录或密钥管理。

---

## 前后端分离（Next.js + FastAPI + Turborepo）

仓库根目录包含 **Turborepo** 工作区：`apps/frontend`（Next.js）、`apps/backend`（FastAPI）、`packages/teambition-client`（可复用 Open API 客户端）、`packages/types`（共享 TS 类型）。原有 **Streamlit** 入口（`app.py`）仍保留。

### 环境变量（后端）

在运行后端前配置 `TB_COMPANY_PROFILES_JSON`（JSON 数组，每项含 `name`、`app_id`、`app_secret`、`tenant_id`）。不要将真实密钥提交到公开仓库。可选：`REDIS_URL`（接口配置缓存）、`JWT_SECRET`（返回包装会话 JWT）、`CORS_ORIGINS`。

### 本地开发

```bash
# 安装 Python 依赖（建议在 venv 中，Python 3.10+）
python3 -m pip install -e ./packages/teambition-client
python3 -m pip install -r apps/backend/requirements.txt -r apps/backend/requirements-dev.txt

# 终端 1：后端（需 PYTHONPATH 指向 teambition-client 源码，或使用 editable install）
cd apps/backend && PYTHONPATH=../../packages/teambition-client/src python3 -m uvicorn app.main:app --reload --port 8000

# 终端 2：前端
cd apps/frontend && echo 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000' > .env.local && npm install && npm run dev

# 根目录一键（需已安装 turbo）
npm run dev
```

### 分步拉取任务（FastAPI + Next.js）

大量项目时，一次性 `POST /data/tasks/fetch-all` 会长时间占用连接且无法观察进度。现提供 **分步任务**（每步一次开放平台调用：拉取某项目的阶段，或拉取一页任务）：

| 端点 | 说明 |
|------|------|
| `POST /api/v1/data/tasks/fetch/jobs` | 创建任务；Body：`{ "page_size": 50 }`。返回 `jobId`、`projectCount`。会先请求一次项目列表。 |
| `POST /api/v1/data/tasks/fetch/jobs/{jobId}/step` | 执行一步；返回 `done`、`cancelled`、`failed`、`tasksByProject`（已合并部分结果）、`progress`。循环调用直至 `done` 或 `cancelled`/`failed`。 |
| `GET /api/v1/data/tasks/fetch/jobs/{jobId}` | 查询当前进度与合并后的 `tasksByProject`。 |
| `POST /api/v1/data/tasks/fetch/jobs/{jobId}/cancel` | 停止：后续 `step` 不再调用 Teambition，并保留已拉取数据。 |
| `POST /api/v1/data/tasks/fetch/jobs/{jobId}/resume` | 仅当任务为 **已停止** 时可恢复，从断点继续 `step`。 |

**说明**：`jobId` 状态仅保存在 **后端进程内存** 中；进程重启或部署后任务丢失，需重新「开始拉取」。保留接口 `POST /data/tasks/fetch-all` 作为一次性全量拉取兼容。

前端 **「任务」** 页（`/tasks`）提供：进度条与阶段文案、与导出一致的 **表格预览**（前 200 行）、**开始 / 停止 / 恢复** 按钮；数据写入 Zustand 工作区，与 **「导出 Excel」** 页共用。

实现文件：`apps/backend/app/task_fetch_jobs.py`（状态机）、`apps/backend/app/routers/data.py`（路由）、`apps/frontend/app/(dashboard)/tasks/page.tsx`。

### Docker（现代栈）

```bash
docker compose --profile modern up --build
```

默认 `docker compose up` 仍为 **Streamlit** 服务（端口 8501）。`--profile modern` 启动 Redis、后端（8000）、前端（3000）；`--profile worker` 额外启动 Celery worker（示例任务 `teambition.ping`）。

### 文档与反馈

- Teambition 开放平台：<https://open.teambition.com/docs>  
- 问题反馈：在本仓库提交 Issue  

## 许可证

MIT License
