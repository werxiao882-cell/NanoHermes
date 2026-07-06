#!/usr/bin/env python3

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import sys
import json

def download_douyin_video(url, output_dir="~/Videos/douyin"):
    """
    使用浏览器自动化下载抖音视频
    """
    # 创建输出目录
    output_dir = os.path.expanduser(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # 配置Chrome选项
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    print(f"正在启动浏览器...")
    driver = uc.Chrome(options=options)
    
    try:
        print(f"正在访问抖音视频: {url}")
        driver.get(url)
        
        # 等待页面加载
        time.sleep(5)
        
        # 尝试获取视频标题
        try:
            title_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
            )
            video_title = title_element.text.strip()
            print(f"视频标题: {video_title}")
        except:
            video_title = "douyin_video"
            print("无法获取视频标题，使用默认名称")
        
        # 尝试找到视频元素并获取src
        try:
            video_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            video_url = video_element.get_attribute("src")
            
            if video_url:
                print(f"找到视频URL: {video_url}")
                
                # 下载视频
                import requests
                response = requests.get(video_url, stream=True)
                if response.status_code == 200:
                    safe_title = "".join(c for c in video_title if c.isalnum() or c in " _-").rstrip()
                    filename = f"{safe_title}.mp4"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"✅ 视频下载成功!")
                    print(f"📁 保存位置: {filepath}")
                    return True
                else:
                    print(f"❌ 视频下载失败，状态码: {response.status_code}")
            else:
                print("❌ 未找到视频URL")
                
        except Exception as e:
            print(f"❌ 获取视频元素失败: {e}")
            
        # 如果直接方法失败，尝试其他方法
        print("尝试备用下载方法...")
        page_source = driver.page_source
        
        # 在页面源码中查找视频URL
        import re
        video_urls = re.findall(r'https://[^"\']+\.mp4[^"\']*', page_source)
        if video_urls:
            print(f"在页面源码中找到 {len(video_urls)} 个视频URL")
            # 下载第一个找到的视频
            video_url = video_urls[0]
            print(f"尝试下载: {video_url}")
            
            response = requests.get(video_url, stream=True)
            if response.status_code == 200:
                safe_title = "".join(c for c in video_title if c.isalnum() or c in " _-").rstrip()
                filename = f"{safe_title}_backup.mp4"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✅ 备用方法下载成功!")
                print(f"📁 保存位置: {filepath}")
                return True
        
        return False
        
    finally:
        driver.quit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python download_douyin_automated.py <douyin_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    success = download_douyin_video(url)
    
    if not success:
        print("❌ 所有下载方法都失败了")
        sys.exit(1)