# Spec: 网络搜索工具 (web_search)

## 概述

`web_search` 工具提供实时互联网搜索能力，基于 DuckDuckGo 搜索引擎。

## 接口定义

### 函数签名

```python
def web_search(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    backend: str = "text",
    task_id: str | None = None,
) -> str:
```

### 返回值格式

**成功（text 模式）**:
```json
{
  "status": "success",
  "query": "搜索关键词",
  "backend": "text",
  "count": 3,
  "results": [
    {
      "title": "页面标题",
      "url": "https://...",
      "description": "页面摘要"
    }
  ]
}
```

**成功（news 模式）**:
```json
{
  "status": "success",
  "query": "搜索关键词",
  "backend": "news",
  "count": 2,
  "results": [
    {
      "title": "新闻标题",
      "url": "https://...",
      "description": "新闻摘要",
      "source": "新闻来源",
      "date": "2024-01-01"
    }
  ]
}
```

**失败**:
```json
{
  "error": "错误描述",
  "query": "搜索关键词"
}
```

## 工具注册

| 属性 | 值 |
|------|-----|
| name | `web_search` |
| toolset | `search` |
| defer_loading | `True` |
| check_fn | `check_web_search_available` |

## 依赖

- `duckduckgo-search>=6.0.0`

## 约束

- `max_results` 限制在 [1, 20] 范围内
- `query` 不能为空或纯空白
- 网络异常时返回错误而非抛出异常
