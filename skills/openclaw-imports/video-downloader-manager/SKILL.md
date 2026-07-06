---
name: video-downloader-manager
description: 统一管理多平台视频下载，支持YouTube、Bilibili、抖音等平台，自动分类保存到对应目录，智能文件命名。
---

# 视频下载管理器 (Video Downloader Manager)

## 功能特性

- **多平台支持**: YouTube、Bilibili、抖音等主流视频平台
- **自动分类**: 不同平台视频自动保存到对应目录
- **智能命名**: 基于视频标题生成有意义的文件名
- **格式处理**: 自动处理音视频分离与合并
- **统一接口**: 简单易用的命令行接口

## 目录结构

```
~/Videos/
├── youtube/     # YouTube视频
├── bilibili/    # Bilibili视频  
├── douyin/      # 抖音视频
└── other/       # 其他平台视频
```

## 安装依赖

确保已安装以下工具：
- ffmpeg (用于音视频处理)
- yt-dlp (用于多平台下载支持)
- Python3 (用于抖音下载器)

## 使用方法

### 基本命令
```bash
# 下载视频到对应平台目录
./download_video.sh <platform> <url>

# 支持的平台: youtube, bilibili, douyin
```

### 示例
```bash
# 下载YouTube视频
./download_video.sh youtube "https://www.youtube.com/watch?v=xxx"

# 下载Bilibili视频  
./download_video.sh bilibili "https://www.bilibili.com/video/BV1xxxxx"

# 下载抖音视频
./download_video.sh douyin "https://v.douyin.com/xxx"
```

## 平台特定说明

### YouTube
- 自动下载最高质量的完整视频
- 文件名基于视频标题自动生成

### Bilibili  
- 下载分离的视频和音频流
- 自动合并为完整视频文件
- 智能重命名为中文标题

### 抖音
- **需要登录认证**：抖音视频需要登录才能下载
- **推荐方法**：使用cookies文件配合yt-dlp
- **操作步骤**：
  1. 在浏览器中登录 [douyin.com](https://www.douyin.com)
  2. 导出cookies保存为 `cookies.txt`
  3. 使用专用脚本下载：`./download_douyin_with_cookies.sh "URL" cookies.txt`
- **备选方案**：如果已安装nodriver_kit依赖，可直接使用skill内置功能

## 高级功能

### 自定义输出目录
修改脚本中的目录路径来自定义保存位置。

### 批量下载
可以编写简单的循环脚本来批量处理多个URL。

### 文件命名规则
- 移除特殊字符和非法文件名字符
- 保留中文、英文、数字和基本标点
- 截断过长的文件名（保持在200字符以内）

## 故障排除

### 抖音下载需要登录
1. 在浏览器中访问 https://www.douyin.com 并登录
2. 按F12打开开发者工具
3. 在Application → Cookies中复制所有cookies
4. 保存为 `cookies.txt` 文件
5. 使用yt-dlp配合cookies下载

### Bilibili音视频合并失败
确保系统已安装ffmpeg：
```bash
sudo apt install ffmpeg
```

### YouTube下载失败
检查网络连接和视频是否可用，某些视频可能有区域限制。

## 安全注意事项

- 视频下载请遵守各平台的使用条款
- 仅用于个人学习和备份用途
- 不要用于商业分发或侵权行为
- 注意版权保护，尊重创作者权益