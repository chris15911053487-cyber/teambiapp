# Teambition 数据工作台

基于 [Streamlit](https://streamlit.io) 的 Teambition Open API 图形化工具，用于拉取企业、项目、任务与工时数据，并导出为 Excel。

## 功能特性

- **企业信息**：查看企业名称、组织 ID、创建时间等
- **项目列表**：支持游标分页（`pageToken` / `nextPageToken`）
- **任务查询**（**重点增强**）：新增独立「任务」菜单
  - 先调用 `/v3/project/{projectId}/stage/search` 获取**阶段/任务列表**（Kanban 列）
  - 再调用 `/v3/project/{projectId}/task/query` 获取完整任务
  - 支持单个项目查询 + 全部项目批量查询
  - 自动关联阶段名称，提升数据可读性
- **工时汇总**：在已有任务数据的基础上，按任务拉取工时聚合
- **导出 Excel**：多 Sheet 导出（企业、项目、各项目任务、工时、阶段信息等）
- **权限友好**：增强错误提示，明确指出需要开启的权限（`tb-core:project.stage:list` 等）
- **Docker**：支持容器化部署

**核心解决**：之前「给了权限仍提示没有权限」的问题，现在有专门页面和详细指引。

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

**重要**：**任务页面** 专门优化了权限问题，如果遇到「没有权限」，请重点检查开放平台应用权限配置。

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

---

## 技术说明

- **项目分页**：Open API v3 的 `/v3/project/query` 使用 **游标分页** (`pageToken`/`nextPageToken`)。
- **任务查询**：新增 `search_project_stages()`（`/v3/project/{projectId}/stage/search`）和 `query_tasks()`（支持 `/v3/project/{projectId}/task/query` 或全局 `/v3/task/query`）。
  - 自动获取阶段信息并映射到任务的 `stageName`。
  - 增强 `_request()` 方法，提供详细的权限错误诊断（code 403、10133、authorization 等）。
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
