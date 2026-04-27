#!/bin/bash

# 文档管理平台启动脚本

set -e

echo "=================================="
echo "  文档管理平台"
echo "=================================="

# 检查是否已存在虚拟环境
if [ ! -d ".venv" ]; then
    echo "正在创建虚拟环境..."
    uv venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
echo "正在安装依赖..."
uv sync

# 检查端口是否被占用
PORT=3333
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "端口 $PORT 已被占用，正在尝试停止现有服务..."
    PID=$(lsof -ti:$PORT)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        sleep 1
    fi
fi

# 启动服务
echo "正在启动服务 (端口: $PORT)..."
echo "服务地址: http://0.0.0.0:$PORT"
echo "按 Ctrl+C 停止服务"
echo "=================================="

# 后台启动并记录PID
nohup uvicorn app.main:app --host 0.0.0.0 --port $PORT > app.log 2>&1 &
PID=$!

# 等待服务启动
sleep 2

# 检查服务是否启动成功
if ps -p $PID > /dev/null 2>&1; then
    echo $PID > app.pid
    echo "服务已启动成功!"
    echo "PID: $PID"
    echo "日志文件: app.log"
    echo "访问地址: http://localhost:$PORT"
    echo ""
    echo "停止服务请运行: ./stop.sh"
else
    echo "服务启动失败，请查看日志文件: app.log"
    exit 1
fi
