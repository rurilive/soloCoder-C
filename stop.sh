#!/bin/bash

# 文档管理平台停止脚本

echo "=================================="
echo "  停止文档管理平台服务"
echo "=================================="

# 从PID文件读取PID
if [ -f "app.pid" ]; then
    PID=$(cat app.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "正在停止服务 (PID: $PID)..."
        kill $PID 2>/dev/null || true
        
        # 等待进程结束
        for i in 1 2 3 4 5; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # 如果进程还在运行，强制停止
        if ps -p $PID > /dev/null 2>&1; then
            echo "强制停止服务..."
            kill -9 $PID 2>/dev/null || true
        fi
        
        # 清理PID文件
        rm -f app.pid
        echo "服务已停止"
    else
        echo "PID文件存在，但进程已不存在"
        rm -f app.pid
    fi
else
    # 尝试通过端口查找进程
    PORT=3333
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        PID=$(lsof -ti:$PORT)
        echo "通过端口 $PORT 找到进程 (PID: $PID)..."
        kill $PID 2>/dev/null || true
        
        # 等待进程结束
        for i in 1 2 3 4 5; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        if ps -p $PID > /dev/null 2>&1; then
            echo "强制停止服务..."
            kill -9 $PID 2>/dev/null || true
        fi
        
        echo "服务已停止"
    else
        echo "未找到正在运行的服务"
    fi
fi

echo "=================================="
