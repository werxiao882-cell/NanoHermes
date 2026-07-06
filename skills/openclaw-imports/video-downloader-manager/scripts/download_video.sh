#!/bin/bash

# 视频下载管理脚本
# 用法: ./download_video.sh <platform> <url>

set -e

PLATFORM="$1"
URL="$2"

if [ -z "$PLATFORM" ] || [ -z "$URL" ]; then
    echo "用法: $0 <platform> <url>"
    echo "支持的平台: youtube, bilibili, douyin"
    echo "示例: $0 bilibili https://www.bilibili.com/video/BV1xxxxx"
    exit 1
fi

# 创建目录结构
mkdir -p ~/Videos/{youtube,bilibili,douyin,other}

case "$PLATFORM" in
    "youtube")
        # 检查YouTube下载器是否可用
        if [ -f "~/.agents/skills/youtube-downloader/scripts/download_video.py" ]; then
            python3 ~/.agents/skills/youtube-downloader/scripts/download_video.py "$URL" -o ~/Videos/youtube
        else
            # 回退到yt-dlp
            yt-dlp -o "~/Videos/youtube/%(title)s.%(ext)s" "$URL"
        fi
        echo "YouTube视频已下载到 ~/Videos/youtube/"
        ;;
    "bilibili")
        # 使用Bilibili下载器
        TEMP_DIR=$(mktemp -d)
        node ~/.agents/skills/bilibili-downloader/download.cjs "$URL" "$TEMP_DIR"
        
        # 获取BV号
        BV_ID=$(echo "$URL" | grep -o 'BV[0-9A-Za-z]*')
        if [ -z "$BV_ID" ]; then
            echo "无法从URL提取BV号"
            exit 1
        fi
        
        # 获取视频信息用于重命名
        VIDEO_INFO=$(curl -s "https://api.bilibili.com/x/web-interface/view?bvid=$BV_ID" 2>/dev/null)
        if [ $? -eq 0 ] && echo "$VIDEO_INFO" | grep -q '"title"'; then
            TITLE=$(echo "$VIDEO_INFO" | jq -r '.data.title' 2>/dev/null | sed 's/[\\/:*?"<>|]//g' | cut -c1-200)
            if [ -n "$TITLE" ] && [ "$TITLE" != "null" ]; then
                mv "$TEMP_DIR/${BV_ID}_video.mp4" "$TEMP_DIR/temp_video.mp4"
                mv "$TEMP_DIR/${BV_ID}_audio.mp4" "$TEMP_DIR/temp_audio.mp4"
                ffmpeg -i "$TEMP_DIR/temp_video.mp4" -i "$TEMP_DIR/temp_audio.mp4" -c copy "~/Videos/bilibili/${TITLE}.mp4"
                rm -rf "$TEMP_DIR"
                echo "Bilibili视频已下载并重命名为: ${TITLE}.mp4"
            else
                # 回退到默认命名
                ffmpeg -i "$TEMP_DIR/${BV_ID}_video.mp4" -i "$TEMP_DIR/${BV_ID}_audio.mp4" -c copy "~/Videos/bilibili/${BV_ID}.mp4"
                rm -rf "$TEMP_DIR"
                echo "Bilibili视频已下载到 ~/Videos/bilibili/${BV_ID}.mp4"
            fi
        else
            # 回退到默认命名和合并
            ffmpeg -i "$TEMP_DIR/${BV_ID}_video.mp4" -i "$TEMP_DIR/${BV_ID}_audio.mp4" -c copy "~/Videos/bilibili/${BV_ID}.mp4"
            rm -rf "$TEMP_DIR"
            echo "Bilibili视频已下载到 ~/Videos/bilibili/${BV_ID}.mp4"
        fi
        ;;
    "douyin")
        # 检查抖音下载器是否可用
        if [ -f "~/.agents/skills/douyin/scripts/download.py" ]; then
            python3 ~/.agents/skills/douyin/scripts/download.py "$URL" --output ~/Videos/douyin
        else
            # 回退到yt-dlp（需要cookies）
            if [ -f "./cookies.txt" ]; then
                yt-dlp --cookies ./cookies.txt -o "~/Videos/douyin/%(title)s.%(ext)s" "$URL"
            else
                yt-dlp -o "~/Videos/douyin/%(title)s.%(ext)s" "$URL"
            fi
        fi
        echo "抖音视频已下载到 ~/Videos/douyin/"
        ;;
    *)
        echo "不支持的平台: $PLATFORM"
        echo "支持的平台: youtube, bilibili, douyin"
        exit 1
        ;;
esac