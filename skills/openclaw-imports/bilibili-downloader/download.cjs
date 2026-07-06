#!/usr/bin/env node
/**
 * B站视频下载工具 - Node.js版本
 * 支持通过命令行参数传入视频URL和保存目录
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path'); // Import path module for joining paths

// --- Argument Parsing ---
const args = process.argv.slice(2); // Get arguments after node and script path
if (args.length < 2) {
    console.error('Usage: node download_bilibili_video.cjs <video_url> <save_directory>');
    console.error('Example: node download_bilibili_video.cjs https://www.bilibili.com/video/BV1abcde ./downloads');
    process.exit(1);
}
const VIDEO_URL_ARG = args[0];
const SAVE_DIR = args[1];
// --- End Argument Parsing ---

// Ensure save directory exists
if (!fs.existsSync(SAVE_DIR)){
    fs.mkdirSync(SAVE_DIR, { recursive: true });
    console.log(`Created save directory: ${SAVE_DIR}`);
}

/**
 * 从URL中提取BV号
 */
function extractBVID(url) {
    // If it's already a BV number, return it
    if (url.startsWith('BV')) {
        return url;
    }
    // Extract BV number from the full URL
    const match = url.match(/BV[a-zA-Z0-9]+/);
    return match ? match[0] : null;
}

/**
 * 发送HTTP/HTTPS请求
 */
function fetch(url) {
    return new Promise((resolve, reject) => {
        const protocol = url.startsWith('https') ? https : http;
        const options = {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com/',
                'Origin': 'https://www.bilibili.com',
            }
        };

        protocol.get(url, options, (res) => {
            let data = '';

            res.on('data', (chunk) => {
                data += chunk;
            });

            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    resolve(jsonData);
                } catch (error) {
                    reject(new Error(`JSON解析失败: ${error.message}`));
                }
            });
        }).on('error', (error) => {
            reject(error);
        });
    });
}

/**
 * 获取视频信息
 */
async function getVideoInfo(bvid) {
    const url = `https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`;
    
    try {
        const data = await fetch(url);
        
        if (data.code === -404) {
            throw new Error('视频不存在或已被删除');
        }
        if (data.code === -403) {
            throw new Error('视频访问受限');
        }
        if (data.code !== 0) {
            throw new Error(`API错误: ${data.message || data.code}`);
        }

        return data.data;
    } catch (error) {
        if (error.message.includes('视频')) {
            throw error;
        }
        throw new Error('获取视频信息失败: 网络错误');
    }
}

/**
 * 获取视频播放URL
 */
async function getVideoPlayurl(bvid, cid) {
    const url = `https://api.bilibili.com/x/player/playurl?bvid=${bvid}&cid=${cid}&qn=80&fnval=16&fnver=0&fourk=1`;
    
    try {
        const data = await fetch(url);
        
        if (data.code === -404) {
            throw new Error('播放信息不存在');
        }
        if (data.code !== 0) {
            throw new Error(`获取播放链接失败: ${data.message || data.code}`);
        }

        return data.data;
    } catch (error) {
        if (error.message.includes('播放')) {
            throw error;
        }
        throw new Error('获取播放信息失败: 网络错误');
    }
}

/**
 * 下载文件（带重试机制）
 */
function downloadFile(url, filename, retries = 3) {
    return new Promise((resolve, reject) => {
        const attemptDownload = (attempt) => {
            const protocol = url.startsWith('https') ? https : http;
            const options = {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.bilibili.com/',
                }
            };

            const fullPath = path.join(SAVE_DIR, filename);
            console.log(`开始下载: ${fullPath} (尝试 ${attempt}/${retries})`);

            protocol.get(url, options, (res) => {
                if (res.statusCode !== 200) {
                    reject(new Error(`HTTP ${res.statusCode}`));
                    return;
                }

                const totalSize = parseInt(res.headers['content-length'] || '0', 10);
                let downloaded = 0;

                const fileStream = fs.createWriteStream(fullPath);

                res.on('data', (chunk) => {
                    downloaded += chunk.length;
                    fileStream.write(chunk);

                    const progress = totalSize > 0 ? ((downloaded / totalSize) * 100).toFixed(1) : 0;
                    process.stdout.write(`\r下载进度: ${progress}%`);
                });

                res.on('end', () => {
                    fileStream.end();
                    console.log(`\n✅ 下载完成: ${fullPath}`);
                    resolve();
                });

                res.on('error', (error) => {
                    fileStream.end();
                    if (attempt < retries) {
                        console.log(`\n下载失败，重试中...`);
                        setTimeout(() => attemptDownload(attempt + 1), 1000 * attempt);
                    } else {
                        reject(error);
                    }
                });
            }).on('error', (error) => {
                if (attempt < retries) {
                    console.log(`\n网络错误，重试中...`);
                    setTimeout(() => attemptDownload(attempt + 1), 1000 * attempt);
                } else {
                    reject(error);
                }
            });
        };

        attemptDownload(1);
    });
}

/**
 * 主函数
 */
async function main() {
    try {
        // Use the URL from command-line arguments
        const bvid = extractBVID(VIDEO_URL_ARG);
        if (!bvid) {
            throw new Error('无效的BV号或URL格式');
        }

        console.log(`视频BV号: ${bvid}`);

        console.log(`正在获取视频信息...`);
        const videoInfo = await getVideoInfo(bvid);
        const cid = videoInfo.cid;
        console.log(`视频: ${videoInfo.title}`);

        console.log(`正在获取播放链接...`);
        const playData = await getVideoPlayurl(bvid, cid);

        const dashData = playData.dash || {};
        const videos = dashData.video || [];

        if (videos.length === 0) {
            throw new Error('没有可用的视频流');
        }

        // 选择最高质量的视频
        const video = videos.reduce((max, v) => (v.bandwidth > max.bandwidth ? v : max), videos[0]);
        const videoUrl = video.baseUrl;

        console.log(`质量: ${video.width}x${video.height}`);

        // 获取音频
        const audios = dashData.audio || [];
        let audioUrl = null;

        if (audios.length > 0) {
            const audio = audios.reduce((max, a) => (a.bandwidth > max.bandwidth ? a : max), audios[0]);
            audioUrl = audio.baseUrl;
        }

        // 并发下载视频和音频
        const videoFilename = `${bvid}_video.mp4`;
        const audioFilename = `${bvid}_audio.mp4`;

        const downloads = [downloadFile(videoUrl, videoFilename)];
        if (audioUrl) {
            downloads.push(downloadFile(audioUrl, audioFilename));
        }
        
        await Promise.all(downloads);
        console.log('\n🎉 下载完成!');
        
    } catch (error) {
        console.error('❌ ' + error.message);
        process.exit(1);
    }
}

main();
