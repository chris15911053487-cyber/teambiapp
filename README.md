# Teambition 数据工作台

基于 [Streamlit](https://streamlit.io) 的 Teambition Open API 图形化工具，用于拉取企业、项目、任务与工时数据，并导出为 Excel。

## 功能特性

- **企业信息**：查看企业名称、组织 ID、创建时间等
- **项目列表**：支持游标分页（`pageToken` / `nextPageToken`）
- **任务查询**（**重点增强**）：新增独立「任务」菜单
  - 先调用 `/v3/project/{projectId}/stage/search` 获取**阶段**（Kanban 列）
  - 再调用 **`GET /v3/task/query`**（query 中 `filter` 含 `projectId`，并分页）拉取该项目下**任务列表**
  - 支持单个项目查询 + 全部项目批量查询
  - 自动关联阶段名称，提升数据可读性
- **工时汇总**：在已有任务数据的基础上，按任务拉取工时聚合
- **导出 Excel**：多 Sheet 导出（企业、项目、各项目任务、工时、阶段信息等）
- **权限友好**：增强错误提示，明确指出需要开启的权限（`tb-core:project.stage:list` 等）
- **API 请求调试**：侧边栏可开启「显示 API 请求报文」，在「任务」页查看每次发往 Teambition 的 URL、Headers（界面展示为脱敏）、Query 参数及响应；每条记录支持 **一键复制完整报文**（含**未脱敏** Headers、响应 JSON 与 **cURL**），便于粘贴到 **Postman**（Import → Raw text）或记事本对照
- **Docker**：支持容器化部署

**核心解决**：之前「给了权限仍提示没有权限」的问题，现在有专门页面和详细指引；配合请求报文可快速核对 `X-Tenant-Id`、项目 ID、换票后的 Token 是否一致。

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

### 1. 获取 Token（配置页）

在侧边栏进入 **「配置」**：

1. **暗号**为当天日期，格式 **`YYYYMMDD`**（与服务器当天日期一致）。
2. 点击 **「验证并获取 Token」**。  
   应用使用内置的 App ID / App Secret（见 `config_page` 内代码），在本地用 `appSecret` 签发 HS256 应用 JWT，再请求开放平台换票（与 `@tng/teambition-openapi-sdk` 的 `getAppAccessToken` 思路一致）。

- 可调用的换票地址：`POST https://open.teambition.com/api/appToken`  
- 请勿在浏览器直接打开易跳转登录页的文档路径；程序侧使用 **`/api/appToken`**，请求头 `Authorization: Bearer <应用 JWT>`，Body：`{"appId","appSecret"}`。

成功后会写入会话中的 **Access Token**，页面可复制完整 Token。

**备选**：也可在开放平台调试界面复制 Token，若你自行扩展界面支持手动粘贴，可写入会话使用（当前仓库以配置页暗号换票为主）。

### 2. 企业 ID（Tenant）

当前示例在代码中为 **固定企业 ID** 并写入会话；若你 fork 部署，请在 `app.py` 的 `config_page` 中改为自己的企业 ID，或改为从环境变量读取（需自行改代码）。

### 3. 拉取与导出

**推荐流程**：

1. 进入 **「配置」** 页输入当天日期暗号获取 Token。
2. 进入 **「数据」** 或 **「工作台」** 获取企业信息 + 项目列表。
3. 切换到 **「任务」** 页：
   - 点击「拉取全部项目任务和阶段」获取完整数据（推荐）
   - 或选择单个项目进行快速查询
4. 返回「数据」页查看结果，或直接在「任务」页浏览带阶段名称的任务表格。
5. 在 **导出 Excel** 中生成多 Sheet 文件（现在包含阶段信息）。

**权限问题解决**：如果接口返回权限错误，页面会给出具体指引，重点检查开放平台 → 你的应用 → 权限设置。

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

## 项目结构（节选）

```
teambition-app/
├── app.py                 # 主应用（Streamlit UI + API）
├── config_sidebar.py      # 换票、JWT 等
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pytest.ini
├── deploy.sh              # 若存在，部署脚本
└── README.md
```

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

## 文档与反馈

- Teambition 开放平台：<https://open.teambition.com/docs>  
- 问题反馈：在本仓库提交 Issue  

## 许可证

MIT License
