# Teambition API Tool  测试202604111228-1237

基于 Streamlit 的 Teambition API 图形化工具，支持数据导出到 Excel。

## ✨ 功能特性

- 🏢 **获取企业信息** - 查看企业名称、ID、创建时间等
- 📁 **获取项目列表** - 查看所有项目及其详情
- 📋 **获取任务列表** - 查看每个项目的任务
- 📊 **导出 Excel** - 一键导出所有数据到 Excel 文件
- 🔄 **自动更新** - 支持 Token 自动刷新（后续版本）
- 🐳 **Docker 支持** - 支持 Docker 部署和运行

## � CI/CD 自动化

本项目使用 GitHub Actions 实现自动化 CI/CD：

### 📋 自动化流程

- **PR 检查**: 每次提交 PR 时自动运行测试和代码质量检查
- **主分支部署**: 推送到 `main` 分支时自动构建 Docker 镜像并部署到服务器

### 🔐 GitHub Secrets 配置

在 GitHub 仓库的 Settings > Secrets and variables > Actions 中配置以下密钥：

#### Docker Hub 配置
- `DOCKER_USERNAME`: Docker Hub 用户名
- `DOCKER_PASSWORD`: Docker Hub 密码或访问令牌

#### 服务器部署配置
- `SERVER_HOST`: 服务器 IP 地址或域名
- `SERVER_USERNAME`: 服务器 SSH 用户名
- `SERVER_SSH_KEY`: 服务器 SSH 私钥（用于无密码登录）
- `SERVER_PORT`: SSH 端口（默认为 22）

### 📝 配置步骤

1. **准备服务器**
   ```bash
   # 确保服务器已安装 Docker
   curl -fsSL https://get.docker.com | sh

   # 创建应用数据目录
   sudo mkdir -p /opt/teambition-app/data
   sudo chown $USER:$USER /opt/teambition-app/data
   ```

2. **配置 SSH 密钥**
   ```bash
   # 在本地生成 SSH 密钥对
   ssh-keygen -t rsa -b 4096 -C "github-actions@your-domain.com"

   # 将公钥添加到服务器的 authorized_keys
   ssh-copy-id user@your-server

   # 将私钥内容复制到 GitHub Secrets 的 SERVER_SSH_KEY
   cat ~/.ssh/id_rsa
   ```

3. **配置 GitHub Secrets**
   - 访问仓库 Settings > Secrets and variables > Actions
   - 添加上述所有必需的 secrets

4. **推送代码**
   ```bash
   git add .
   git commit -m "Add CI/CD configuration"
   git push origin main
   ```

### 🔍 工作流文件

- `.github/workflows/ci-cd.yml`: 主要的 CI/CD 工作流
- `tests.py`: 单元测试文件
- `requirements-dev.txt`: 开发依赖
- `pytest.ini`: 测试配置
- `deploy.sh`: 服务器部署脚本

### 📊 测试覆盖率

项目使用 pytest 和 coverage 进行测试，测试覆盖率要求 ≥ 80%。

运行测试：
```bash
pip install -r requirements-dev.txt
pytest
```

### 方式一：本地运行（推荐开发使用）

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 启动应用

```bash
streamlit run app.py
```

#### 3. 访问应用

打开浏览器访问：http://localhost:8501

---

### 方式二：Docker 运行（推荐生产使用）

#### 1. 构建镜像

```bash
docker build -t teambition-app .
```

#### 2. 运行容器

```bash
docker run -p 8501:8501 teambition-app
```

#### 或使用 Docker Compose

```bash
docker-compose up -d
```

#### 3. 访问应用

打开浏览器访问：http://localhost:8501

---

## 📖 使用说明

### 1. 获取 Token

1. 访问 [Teambition 开放平台](https://open.teambition.com/docs/apis/6321c6ce912d20d3b5a488f4)
2. 点击 **调试** 按钮
3. 复制 **Authorization** 中的 Token（去掉 `Bearer ` 前缀）

![获取 Token 步骤](https://example.com/token-guide.png)

### 2. 配置应用

在左侧边栏输入：
- **Access Token**: 从上一步获取的 Token
- **企业 ID**: 你的 Teambition 企业 ID

### 3. 获取数据

点击按钮获取数据：
- 🏢 **获取企业信息** - 仅获取企业基本信息
- 📁 **获取项目列表** - 获取项目列表
- 🚀 **获取全部数据** - 获取企业、项目和所有任务

### 4. 导出 Excel

1. 点击 **"生成 Excel 文件"** 按钮
2. 等待生成完成
3. 点击 **"下载 Excel 文件"** 按钮下载

---

## 🐳 Docker 部署详解

### 为什么使用 Docker？

| 优势 | 说明 |
|------|------|
| 🚀 一键部署 | 无需配置 Python 环境，一条命令启动 |
| 🔄 环境隔离 | 避免与其他项目依赖冲突 |
| 📦 便于分发 | 打包后可在任何机器运行 |
| 🛡️ 生产就绪 | 内置健康检查和自动重启 |

### Docker 常用命令

```bash
# 构建镜像
docker build -t teambition-app .

# 运行容器
docker run -d -p 8501:8501 --name teambition-app teambition-app

# 查看日志
docker logs -f teambition-app

# 停止容器
docker stop teambition-app

# 删除容器
docker rm teambition-app

# 更新镜像（代码更新后）
docker build -t teambition-app .
docker stop teambition-app
docker rm teambition-app
docker run -d -p 8501:8501 --name teambition-app teambition-app
```

### Docker Compose 部署（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新服务（代码更新后）
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 🔄 代码更新迭代

### 更新流程

#### 本地开发模式

```bash
# 1. 修改代码（app.py 等文件）
# 2. 测试运行
streamlit run app.py
# 3. 提交代码
git add .
git commit -m "更新说明"
```

#### Docker 部署模式

```bash
# 1. 修改代码
# 2. 重新构建镜像
docker-compose down
docker-compose build
docker-compose up -d
```

### 版本管理建议

```bash
# 使用 Git 管理代码
git init
git add .
git commit -m "初始版本"

# 添加新功能后
git add .
git commit -m "添加 XX 功能"

# 查看历史
git log
```

---

## 📁 项目结构

```
teambition-app/
├── app.py              # 主应用代码
├── requirements.txt    # Python 依赖
├── Dockerfile         # Docker 镜像配置
├── docker-compose.yml # Docker Compose 配置
├── .env.example       # 环境变量示例
└── README.md          # 使用说明
```

---

## ⚙️ 高级配置

### 环境变量

创建 `.env` 文件：

```env
TEAMBITION_TOKEN=your_token
TEAMBITION_TENANT_ID=your_tenant_id
```

### 自定义端口

修改 `docker-compose.yml`：

```yaml
ports:
  - "8080:8501"  # 将 8080 映射到容器的 8501
```

访问：http://localhost:8080

---

## 🐛 常见问题

### Q: Token 过期怎么办？
A: Token 有效期约 30 分钟，过期后需要重新从开放平台获取。

### Q: 如何持久化数据？
A: 已配置 Docker volumes，数据会自动保存到 `./data` 目录。

### Q: 如何查看日志？
A: 
```bash
# Docker 模式
docker logs -f teambition-app

# Docker Compose 模式
docker-compose logs -f
```

### Q: 如何备份数据？
A: Excel 文件会自动下载到浏览器默认下载目录，建议定期备份。

---

## 🔒 安全提示

1. **不要硬编码 Token** - 使用环境变量或侧边栏输入
2. **定期更换 Token** - Token 有效期短，安全性较高
3. **注意网络安全** - 生产环境建议配置 HTTPS
4. **限制访问权限** - 使用防火墙限制访问 IP

---

## 📞 技术支持

- 文档：https://open.teambition.com/docs
- 问题反馈：请在项目中提交 Issue

---

## 📄 许可证

MIT License
