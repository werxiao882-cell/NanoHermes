#!/bin/bash

# 视频下载管理器安装脚本

echo "正在安装视频下载管理器..."

# 创建目录结构
mkdir -p ~/Videos/{youtube,bilibili,douyin,other}

# 复制脚本到用户PATH或工作目录
SCRIPT_DIR="/home/perjoker/.openclaw/workspace/skills/video-downloader-manager/scripts"
TARGET_SCRIPT="/home/perjoker/.openclaw/workspace/download_video.sh"

cp "$SCRIPT_DIR/download_video.sh" "$TARGET_SCRIPT"
chmod +x "$TARGET_SCRIPT"

echo "安装完成！"
echo "使用方法: ./download_video.sh <platform> <url>"
echo "支持的平台: youtube, bilibili, douyin"
echo "视频将自动保存到 ~/Videos/ 对应子目录中"