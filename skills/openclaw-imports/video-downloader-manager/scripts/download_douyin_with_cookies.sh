#!/bin/bash

# 抖音下载脚本（支持cookies认证）
# 用法: ./download_douyin_with_cookies.sh <url> [cookies_file]

URL="$1"
COOKIES_FILE="${2:-./cookies.txt}"

if [ -z "$URL" ]; then
    echo "用法: $0 <douyin_url> [cookies_file]"
    echo "示例: $0 https://v.douyin.com/xxx ./cookies.txt"
    exit 1
fi

# 确保输出目录存在
mkdir -p ~/Videos/douyin

# 检查cookies文件是否存在
if [ ! -f "$COOKIES_FILE" ]; then
    echo "警告: cookies文件 '$COOKIES_FILE' 不存在"
    echo "请先在浏览器中登录抖音，然后导出cookies到该文件"
    echo "或者提供正确的cookies文件路径"
    exit 1
fi

# 使用yt-dlp下载
yt-dlp --cookies "$COOKIES_FILE" -o "~/Videos/douyin/%(title)s.%(ext)s" "$URL"

if [ $? -eq 0 ]; then
    echo "✅ 抖音视频下载成功！"
    echo "📁 保存位置: ~/Videos/douyin/"
else
    echo "❌ 下载失败，请检查cookies是否有效或网络连接"
fi