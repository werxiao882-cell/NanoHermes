"""网络搜索工具：使用 DuckDuckGo 搜索引擎获取实时信息。

设计理由：
- 优先使用 ddgs 库（duckduckgo_search 的继任者），API 更稳定
- 回退到旧版 duckduckgo_search 以保持向后兼容
- 支持 text（网页）和 news（新闻）两种搜索模式
- 结果格式化为结构化 JSON，便于 LLM 理解和引用
- 可用性检查确保网络不可用时快速失败
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.core.registry import register_tool

logger = logging.getLogger(__name__)

# 优先使用新版 ddgs，避免旧版 duckduckgo_search 的 RuntimeWarning
# 旧版库会打印 "renamed to ddgs" 警告，且在国内网络下经常返回 0 结果
try:
    from ddgs import DDGS
    _USE_NEW_API = True
    _DDGS_AVAILABLE = True
except ImportError:
    import warnings
    warnings.filterwarnings("ignore", message=".*renamed to ddgs.*")
    try:
        from duckduckgo_search import DDGS
        _USE_NEW_API = False
        _DDGS_AVAILABLE = True
    except ImportError:
        DDGS = None
        _USE_NEW_API = False
        _DDGS_AVAILABLE = False


def check_web_search_available() -> bool:
    """检查网络搜索是否可用。"""
    return _DDGS_AVAILABLE


def web_search(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    backend: str = "text",
    task_id: str | None = None,
    **kwargs,
) -> str:
    """执行网络搜索。

    Args:
        query: 搜索关键词。
        max_results: 最大返回结果数（默认 5）。
        region: 搜索区域（默认 "wt-wt" 表示全球，可选 zh-cn、en-us 等）。
        safesearch: 安全级别（on/moderate/off，默认 moderate）。
        timelimit: 时间限制（d/w/m/y 分别表示日/周/月/年）。
        backend: 搜索后端（text/news，默认 text）。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含搜索结果列表。
    """
    if not _DDGS_AVAILABLE:
        return json.dumps({
            "error": "ddgs 未安装，请运行: pip install ddgs"
        }, ensure_ascii=False)

    if not query or not query.strip():
        return json.dumps({"error": "搜索关键词不能为空"}, ensure_ascii=False)

    # 类型转换：LLM 可能将整数参数作为字符串传递
    try:
        max_results = int(max_results)
    except (ValueError, TypeError):
        max_results = 5

    max_results = max(1, min(max_results, 20))

    try:
        with DDGS() as ddgs:
            if backend == "news":
                # ddgs 新版用 query，旧版用 keywords
                if _USE_NEW_API:
                    results = list(ddgs.news(
                        query=query,
                        region=region,
                        safesearch=safesearch,
                        timelimit=timelimit,
                        max_results=max_results,
                    ))
                else:
                    results = list(ddgs.news(
                        keywords=query,
                        region=region,
                        safesearch=safesearch,
                        timelimit=timelimit,
                        max_results=max_results,
                    ))
                formatted = _format_news_results(results)
            else:
                if _USE_NEW_API:
                    results = list(ddgs.text(
                        query=query,
                        region=region,
                        safesearch=safesearch,
                        timelimit=timelimit,
                        max_results=max_results,
                    ))
                else:
                    results = list(ddgs.text(
                        keywords=query,
                        region=region,
                        safesearch=safesearch,
                        timelimit=timelimit,
                        max_results=max_results,
                    ))
                formatted = _format_text_results(results)

        return json.dumps({
            "status": "success",
            "query": query,
            "backend": backend,
            "count": len(formatted),
            "results": formatted,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"网络搜索失败: {e}", exc_info=True)
        return json.dumps({
            "error": f"搜索失败: {type(e).__name__}: {e}",
            "query": query,
        }, ensure_ascii=False)


def _format_text_results(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """格式化文本搜索结果。"""
    formatted = []
    for r in results:
        formatted.append({
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "description": r.get("body", ""),
        })
    return formatted


def _format_news_results(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """格式化新闻搜索结果。"""
    formatted = []
    for r in results:
        formatted.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "description": r.get("body", ""),
            "source": r.get("source", ""),
            "date": r.get("date", ""),
        })
    return formatted


SCHEMA = {
    "name": "web_search",
    "description": (
        "Search the internet for real-time information. Use for querying latest news, "
        "technical documentation, API references, current events, or any data that requires "
        "up-to-date information. Returns structured search results with titles, URLs, and snippets.\n\n"
        "Two backends:\n"
        "- text (default): General web search\n"
        "- news: News-specific search with date and source information"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keywords",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5, max: 20)",
                "default": 5,
            },
            "region": {
                "type": "string",
                "description": "Search region (default: 'wt-wt' for worldwide, options: 'zh-cn', 'en-us', etc.)",
                "default": "wt-wt",
            },
            "safesearch": {
                "type": "string",
                "enum": ["on", "moderate", "off"],
                "description": "Safe search level (default: moderate)",
                "default": "moderate",
            },
            "timelimit": {
                "type": "string",
                "enum": ["d", "w", "m", "y"],
                "description": "Time filter: d=past day, w=past week, m=past month, y=past year",
            },
            "backend": {
                "type": "string",
                "enum": ["text", "news"],
                "description": "Search type: 'text' for web search (default), 'news' for news search",
                "default": "text",
            },
        },
        "required": ["query"],
    },
}


def _register_web_search_tool():
    """注册网络搜索工具。"""
    register_tool(
        name="web_search",
        toolset="search",
        schema=SCHEMA,
        handler=web_search,
        check_fn=check_web_search_available,
        description="搜索互联网获取实时信息",
        defer_loading=True,
    )


_register_web_search_tool()
