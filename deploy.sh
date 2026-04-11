#!/bin/bash
# Teambition App 部署脚本

set -e

echo "🚀 开始部署 Teambition App..."

# 配置变量
DOCKER_USERNAME=${DOCKER_USERNAME:-"your-docker-username"}
IMAGE_NAME="${DOCKER_USERNAME}/teambition-app"
CONTAINER_NAME="teambition-api-tool"
APP_PORT=${APP_PORT:-8501}
DATA_DIR=${DATA_DIR:-"/opt/teambition-app/data"}

# 创建数据目录
echo "📁 创建数据目录..."
sudo mkdir -p $DATA_DIR
sudo chown $USER:$USER $DATA_DIR

# 停止并删除旧容器
echo "🛑 停止旧容器..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# 清理未使用的镜像
echo "🧹 清理未使用的镜像..."
docker image prune -f

# 拉取最新镜像
echo "📥 拉取最新镜像..."
docker pull $IMAGE_NAME:latest

# 启动新容器
echo "🏃 启动新容器..."
docker run -d \
  --name $CONTAINER_NAME \
  -p $APP_PORT:8501 \
  -v $DATA_DIR:/app/data \
  --restart unless-stopped \
  --health-cmd "curl -f http://localhost:8501/_stcore/health || exit 1" \
  --health-interval 30s \
  --health-timeout 10s \
  --health-retries 3 \
  $IMAGE_NAME:latest

# 等待应用启动
echo "⏳ 等待应用启动..."
sleep 15

# 检查应用健康状态
echo "🔍 检查应用健康状态..."
if curl -f -s http://localhost:$APP_PORT/_stcore/health > /dev/null; then
    echo "✅ 应用部署成功!"
    echo "🌐 应用访问地址: http://localhost:$APP_PORT"
else
    echo "❌ 应用部署失败，检查容器日志..."
    docker logs $CONTAINER_NAME
    exit 1
fi

echo "🎉 部署完成!"