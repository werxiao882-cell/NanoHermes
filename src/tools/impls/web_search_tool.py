"""网络搜索工具：使用 DuckDuckGo 搜索引擎获取实时信息。

设计理由：
- 使用 duckduckgo-search 库，无需 API Key，隐私友好
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

try:
    from duckduckgo_search import DDGS
    _DDGS_AVAILABLE = True
except ImportError:
    DDGS = None
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
            "error": "duckduckgo-search 未安装，请运行: pip install duckduckgo-search"
        }, ensure_ascii=False)

    if not query or not query.strip():
        return json.dumps({"error": "搜索关键词不能为空"}, ensure_ascii=False)

    max_results = max(1, min(max_results, 20))

    try:
        with DDGS() as ddgs:
            if backend == "news":
                results = list(ddgs.news(
                    keywords=query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=max_results,
                ))
                formatted = _format_news_results(results)
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
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "搜索互联网获取实时信息。适用于查询最新新闻、技术文档、"
            "API 参考、当前事件等需要实时数据的场景。"
            "返回结构化的搜索结果，包含标题、链接和摘要。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数（默认 5，最大 20）",
                    "default": 5,
                },
                "region": {
                    "type": "string",
                    "description": "搜索区域（默认 wt-wt 全球，可选 zh-cn、en-us 等）",
                    "default": "wt-wt",
                },
                "safesearch": {
                    "type": "string",
                    "enum": ["on", "moderate", "off"],
                    "description": "安全搜索级别（默认 moderate）",
                    "default": "moderate",
                },
                "timelimit": {
                    "type": "string",
                    "enum": ["d", "w", "m", "y"],
                    "description": "时间限制：d=过去一天, w=过去一周, m=过去一月, y=过去一年",
                },
                "backend": {
                    "type": "string",
                    "enum": ["text", "news"],
                    "description": "搜索类型：text=网页搜索（默认）, news=新闻搜索",
                    "default": "text",
                },
            },
            "required": ["query"],
        },
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
