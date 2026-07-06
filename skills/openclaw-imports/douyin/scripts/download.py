#!/usr/bin/env python3
"""
Download Douyin videos.

Usage:
    python download.py <url> [--output <dir>] [--info-only]

Examples:
    python download.py https://v.douyin.com/xxx
    python download.py https://www.douyin.com/video/123456 --output ./videos
    python download.py https://v.douyin.com/xxx --info-only
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_PROFILE = "douyin"


async def parse_video(url: str, profile: str = DEFAULT_PROFILE, timeout: int = 30) -> Dict[str, Any]:
    """Parse video info from Douyin URL using CDP network monitoring."""
    from nodriver_kit import cdp, connect_browser, browser_start, browser_stop

    browser = None
    api_responses: List[Dict] = []
    own_browser = False
    started_port = None  # Track port if we started browser

    try:
        # Try to connect to existing browser first
        try:
            browser = await connect_browser(port=9222)
            logger.info("Connected to existing browser on port 9222")
        except Exception:
            # Start new browser using nodriver-kit (handles session restore, etc.)
            logger.info(f"Starting browser with profile: {profile}")
            result = browser_start(profile=profile)
            if "error" in result:
                raise RuntimeError(result["error"])
            started_port = result["port"]
            browser = await connect_browser(port=started_port)
            own_browser = True

        tab = browser.main_tab
        await tab.send(cdp.network.enable())

        request_map: Dict[str, str] = {}

        def on_request(event: cdp.network.RequestWillBeSent):
            req_url = event.request.url
            if "aweme/v1/web/aweme/detail" in req_url:
                request_map[event.request_id.to_json()] = req_url

        async def on_response(event: cdp.network.ResponseReceived):
            req_id = event.request_id.to_json()
            if req_id in request_map:
                try:
                    body_result = await tab.send(cdp.network.get_response_body(event.request_id))
                    api_responses.append(json.loads(body_result[0]))
                except Exception:
                    pass

        tab.add_handler(cdp.network.RequestWillBeSent, on_request)
        tab.add_handler(cdp.network.ResponseReceived, on_response)

        logger.info(f"Navigating to: {url}")
        await tab.get(url)

        for _ in range(timeout):
            await asyncio.sleep(1)
            if api_responses:
                await asyncio.sleep(2)
                break

        current_url = tab.url
        logger.info(f"Page URL: {current_url}")

        # Extract video ID
        video_id = _extract_video_id(current_url) or _extract_video_id(url)

        # Parse API response
        video_url = None
        title = ""
        author_name = ""
        cover_url = ""
        duration = 0
        statistics = {"likes": 0, "comments": 0, "shares": 0, "plays": 0}

        for resp in api_responses:
            data = _parse_aweme_response(resp)
            if data:
                video_url = data.get("video_url")
                title = data.get("title", "")
                author_name = data.get("author", "")
                cover_url = data.get("cover", "")
                duration = data.get("duration", 0)
                statistics = data.get("statistics", statistics)
                video_id = video_id or data.get("id", "")
                break

        if not video_url:
            # Fallback: extract from HTML
            page_source = await tab.get_content()
            match = re.search(r'(https://www\.douyin\.com/aweme/v1/play/\?[^"\s]+)', page_source)
            if match:
                video_url = match.group(1).replace(r'\u0026', '&').replace('\\u0026', '&')

        if not video_url:
            raise ValueError(f"Could not find video URL (URL: {current_url})")

        if not title:
            title = await tab.evaluate("document.title")
            title = title.replace(" - 抖音", "").strip() if title else ""

        return {
            "id": video_id,
            "title": title,
            "author": {"name": author_name, "id": "", "avatar": ""},
            "cover": cover_url,
            "video_url": video_url,
            "duration": duration,
            "statistics": statistics,
        }

    finally:
        if own_browser and started_port:
            try:
                browser_stop(port=started_port)
            except:
                pass


def _extract_video_id(url: str) -> str:
    """Extract video ID from Douyin URL."""
    match = re.search(r'/video/(\d+)', url)
    if match:
        return match.group(1)
    match = re.search(r'(?:modal_id|vid)=(\d+)', url)
    if match:
        return match.group(1)
    return ""


def _parse_aweme_response(data: Dict) -> Optional[Dict]:
    """Extract video info from API response."""
    try:
        aweme = data.get("aweme_detail") or (data.get("aweme_list") or [None])[0]
        if not aweme:
            return None

        video = aweme.get("video", {})

        # Try different URL sources
        video_url = None
        for key in ["play_addr", "download_addr"]:
            url_list = video.get(key, {}).get("url_list", [])
            if url_list:
                video_url = url_list[0]
                break

        if not video_url:
            bit_rate = video.get("bit_rate", [])
            if bit_rate:
                url_list = bit_rate[0].get("play_addr", {}).get("url_list", [])
                if url_list:
                    video_url = url_list[0]

        if not video_url:
            return None

        stats = aweme.get("statistics", {})
        cover = video.get("cover", {})

        return {
            "id": aweme.get("aweme_id", ""),
            "title": aweme.get("desc", ""),
            "author": aweme.get("author", {}).get("nickname", ""),
            "cover": cover.get("url_list", [""])[0] if cover.get("url_list") else "",
            "video_url": video_url,
            "duration": video.get("duration", 0),
            "statistics": {
                "likes": stats.get("digg_count", 0),
                "comments": stats.get("comment_count", 0),
                "shares": stats.get("share_count", 0),
                "plays": stats.get("play_count", 0),
            },
        }
    except Exception:
        return None


def download_file(url: str, output_path: Path) -> Path:
    """Download file from URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.douyin.com/',
    }
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Download Douyin videos")
    parser.add_argument("url", help="Douyin video URL (short or full)")
    parser.add_argument("--output", "-o", help="Output directory", default=None)
    parser.add_argument("--info-only", "-i", action="store_true", help="Only show video info")
    parser.add_argument("--profile", "-p", default=DEFAULT_PROFILE, help="Browser profile")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Parse
    print(f"Parsing: {args.url}")
    try:
        info = asyncio.run(parse_video(args.url, profile=args.profile))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Display
    print(f"\n{'='*50}")
    print(f"ID:       {info['id']}")
    title = info.get('title', 'N/A')
    print(f"Title:    {title[:60]}..." if len(title) > 60 else f"Title:    {title}")
    print(f"Author:   {info['author']['name']}")
    print(f"Duration: {info['duration']/1000:.1f}s")
    print(f"Likes:    {info['statistics']['likes']:,}")
    print(f"{'='*50}")

    if args.info_only:
        print(f"\nVideo URL: {info['video_url']}")
        return

    # Download
    output_dir = Path(args.output) if args.output else Path(__file__).parent.parent / "data" / "videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{info['id'] or 'video'}.mp4"

    print(f"\nDownloading...")
    try:
        download_file(info['video_url'], output_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"Saved: {output_path} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
