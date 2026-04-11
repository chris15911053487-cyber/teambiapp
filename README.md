# Teambition API Tool

基于 Streamlit 的 Teambition API 图形化工具，支持数据导出到 Excel。

## ✨ 功能特性

- 🏢 **获取企业信息** - 查看企业名称、ID、创建时间等
- 📁 **获取项目列表** - 查看所有项目及其详情
- 📋 **获取任务列表** - 查看每个项目的任务
- 📊 **导出 Excel** - 一键导出所有数据到 Excel 文件
- 🔄 **自动更新** - 支持 Token 自动刷新（后续版本）
- 🐳 **Docker 支持** - 支持 Docker 部署和运行

## 🚀 快速开始

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
