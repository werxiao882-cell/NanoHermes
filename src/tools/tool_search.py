"""工具搜索引擎 + search_tools 内置工具。

提供 BM25 + Regex 双引擎工具搜索，支持模型按需发现延迟加载的工具。
search_tools 工具始终可见（defer_loading=False），是 Tool Search 机制的入口点。

设计理由：
- 纯 Python 实现 BM25，无外部依赖（项目依赖保持轻量）
- BM25 适合自然语言查询（"send a message to a user"）
- Regex 适合精确模式匹配（"get_.*_data"）
- Auto 模式自动检测查询类型，降低模型选择负担
- search_tools 直接从 ToolRegistry 读取延迟加载的工具，无需全局单例注入
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

# 正则特征字符：用于检测查询是否像正则表达式
# 检测 .* + ? ^ $ { } ( ) | [ ] \ 等正则元字符
_REGEX_INDICATORS = re.compile(r"[.*+?^${}()|[\]\\]")


class ToolSearch:
    """工具搜索引擎。

    支持两种搜索策略：
    1. BM25: 自然语言描述 → BM25 评分排序
    2. Regex: Python 正则表达式 → 匹配工具名/描述/参数

    设计理由：
    - BM25 是信息检索标准算法，适合工具描述这种短文本
    - Regex 适合工具命名规范、描述清晰的场景
    - Auto 模式自动选择最佳策略，减少模型负担

    Attributes:
        _tools: 延迟加载的工具列表（schema dict）。
        _index: BM25 倒排索引，term → {doc_id: frequency}。
        _doc_lengths: 每个文档的词数列表。
        _avg_doc_length: 平均文档长度。
        _num_docs: 文档总数。
    """

    def __init__(self, tools: list[dict[str, Any]] | None = None):
        """初始化工具搜索引擎。

        Args:
            tools: 延迟加载的工具 schema 列表。
                   每个 schema 必须包含 name, description, parameters。
        """
        self._tools = tools or []
        self._index: dict[str, dict[int, int]] = {}
        self._doc_lengths: list[int] = []
        self._avg_doc_length: float = 0.0
        self._num_docs: int = 0

        if self._tools:
            self._build_index()

    def _build_index(self) -> None:
        """构建 BM25 倒排索引。

        索引构建流程：
        1. 对每个工具，提取可搜索文本（工具名、描述、参数名、参数描述）
        2. 分词：按空格、下划线、连字符、标点分割
        3. 构建倒排索引：term → {doc_id: frequency}
        4. 计算平均文档长度
        """
        self._index.clear()
        self._doc_lengths = []
        self._num_docs = len(self._tools)

        for doc_id, tool in enumerate(self._tools):
            tokens = self._tokenize_tool(tool)
            self._doc_lengths.append(len(tokens))

            for token in tokens:
                if token not in self._index:
                    self._index[token] = {}
                if doc_id not in self._index[token]:
                    self._index[token][doc_id] = 0
                self._index[token][doc_id] += 1

        # 计算平均文档长度（避免除以零）
        if self._num_docs > 0:
            self._avg_doc_length = sum(self._doc_lengths) / self._num_docs

    def _tokenize_tool(self, tool: dict[str, Any]) -> list[str]:
        """将工具元数据分词为词元列表。

        分词策略：
        - 工具名：按下划线和连字符分割（如 "read_file" → ["read", "file"]）
        - 描述：按空格和标点分割
        - 参数名：按下划线分割
        - 参数描述：按空格分割
        - 所有词元转为小写

        Args:
            tool: 工具 schema 字典。

        Returns:
            词元列表（小写）。
        """
        tokens = []

        # 工具名分词
        name = tool.get("name", "")
        tokens.extend(re.split(r"[_\-\s]+", name.lower()))

        # 描述分词
        description = tool.get("description", "")
        tokens.extend(re.split(r"[\s\.,;:!?()]+", description.lower()))

        # 参数名和描述分词
        params = tool.get("parameters", {})
        properties = params.get("properties", {})
        for param_name, param_def in properties.items():
            # 参数名分词
            tokens.extend(re.split(r"[_\-\s]+", param_name.lower()))
            # 参数描述分词
            if isinstance(param_def, dict):
                param_desc = param_def.get("description", "")
                tokens.extend(re.split(r"[\s\.,;:!?()]+", param_desc.lower()))

        # 过滤空字符串和单字符词元（保留有意义的词）
        return [t for t in tokens if len(t) > 1]

    def _idf(self, term: str) -> float:
        """计算逆文档频率（IDF）。

        公式：IDF(qi) = log(1 + (N - df + 0.5) / (df + 0.5))
        - N: 文档总数
        - df: 包含该词的文档数

        使用 log(1 + ...) 而非 log(...) 确保 IDF 始终 >= 0。
        标准 BM25 的 log((N-df+0.5)/(df+0.5)) 在 df > N/2 时为负，
        加 1 后避免负分，同时保持稀有词的高权重。

        Args:
            term: 查询词。

        Returns:
            IDF 值。如果词不在索引中，返回 0。
        """
        if term not in self._index:
            return 0.0
        df = len(self._index[term])
        return math.log(1 + (self._num_docs - df + 0.5) / (df + 0.5))

    def _bm25_score(self, doc_id: int, query_tokens: list[str], k1: float = 1.5, b: float = 0.75) -> float:
        """计算文档的 BM25 评分。

        公式：score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D|/avgdl))

        Args:
            doc_id: 文档 ID。
            query_tokens: 查询词列表。
            k1: 词频饱和参数（默认 1.5）。
            b: 文档长度归一化参数（默认 0.75）。

        Returns:
            BM25 评分。
        """
        score = 0.0
        doc_len = self._doc_lengths[doc_id]

        for token in query_tokens:
            if token not in self._index:
                continue
            tf = self._index[token].get(doc_id, 0)
            if tf == 0:
                continue

            idf = self._idf(token)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / self._avg_doc_length)
            score += idf * numerator / denominator

        return score

    def _search_bm25(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """BM25 自然语言搜索。

        Args:
            query: 自然语言查询字符串。
            top_k: 返回结果数量上限。

        Returns:
            按 BM25 评分降序排列的工具 schema 列表。
        """
        query_tokens = re.split(r"[\s\.,;:!?()]+", query.lower())
        query_tokens = [t for t in query_tokens if len(t) > 1]

        if not query_tokens:
            return []

        scores = []
        for doc_id in range(self._num_docs):
            score = self._bm25_score(doc_id, query_tokens)
            if score > 0:
                scores.append((score, doc_id))

        # 按评分降序排序
        scores.sort(key=lambda x: x[0], reverse=True)

        return [self._tools[doc_id] for _, doc_id in scores[:top_k]]

    def _search_regex(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Regex 模式匹配搜索。

        匹配目标：
        - 工具名
        - 工具描述
        - 参数名
        - 参数描述

        Args:
            query: Python 正则表达式字符串。
            top_k: 返回结果数量上限。

        Returns:
            匹配的工具 schema 列表。
        """
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            return []

        results = []
        for tool in self._tools:
            if self._regex_match_tool(pattern, tool):
                results.append(tool)
                if len(results) >= top_k:
                    break

        return results

    def _regex_match_tool(self, pattern: re.Pattern, tool: dict[str, Any]) -> bool:
        """检查正则是否匹配工具的任意字段。

        Args:
            pattern: 编译后的正则表达式。
            tool: 工具 schema 字典。

        Returns:
            True 如果匹配成功。
        """
        # 匹配工具名
        if pattern.search(tool.get("name", "")):
            return True

        # 匹配工具描述
        if pattern.search(tool.get("description", "")):
            return True

        # 匹配参数名和描述
        params = tool.get("parameters", {})
        properties = params.get("properties", {})
        for param_name, param_def in properties.items():
            if pattern.search(param_name):
                return True
            if isinstance(param_def, dict):
                if pattern.search(param_def.get("description", "")):
                    return True

        return False

    def _is_regex(self, query: str) -> bool:
        """检测查询是否像正则表达式。

        检测特征：包含 .* + ? ^ $ 等正则元字符。

        Args:
            query: 查询字符串。

        Returns:
            True 如果查询包含正则特征字符。
        """
        return bool(_REGEX_INDICATORS.search(query))

    @staticmethod
    def _parse_select_query(query: str) -> list[str]:
        """解析 select: 语法，提取工具名列表。

        设计理由：
        - select: 前缀表示精确加载指定工具，而非模糊搜索
        - 逗号分隔支持批量加载
        - 最多 10 个工具，防止上下文溢出

        Args:
            query: 以 "select:" 开头的查询字符串。

        Returns:
            工具名列表（已去空白，最多 10 个）。
        """
        SELECT_PREFIX = "select:"
        if not query.startswith(SELECT_PREFIX):
            return []

        raw = query[len(SELECT_PREFIX):]
        if not raw.strip():
            return []

        names = [name.strip() for name in raw.split(",") if name.strip()]
        return names[:10]

    def _search_select(self, names: list[str]) -> list[dict[str, Any]]:
        """按名称精确加载工具 schema。

        设计理由：
        - 按查询中指定的顺序返回
        - 不存在的工具名静默忽略
        - O(n) 遍历构建 name→tool 映射，然后 O(m) 按名称查找

        Args:
            names: 工具名列表。

        Returns:
            匹配的工具 schema 列表（按指定顺序）。
        """
        tool_map = {t.get("name", ""): t for t in self._tools}
        results = []
        for name in names:
            if name in tool_map:
                results.append(tool_map[name])
        return results

    def search(
        self,
        query: str,
        mode: str = "auto",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """搜索工具。

        搜索策略：
        - "select:": 精确加载指定工具（优先检测）
        - "auto": 自动检测查询类型，包含正则特征字符时使用 Regex，否则 BM25
        - "bm25": 强制使用 BM25 自然语言搜索
        - "regex": 强制使用 Regex 模式匹配

        Args:
            query: 查询字符串（自然语言、正则表达式或 select: 语法）。
            mode: 搜索模式，"auto" | "bm25" | "regex"。
            top_k: 返回结果数量上限。

        Returns:
            匹配的工具 schema 列表（最多 top_k 个）。
        """
        if not self._tools:
            return []

        # 优先检测 select: 语法（精确加载，不走搜索引擎）
        if query.startswith("select:"):
            select_names = self._parse_select_query(query)
            return self._search_select(select_names)

        if mode == "regex" or (mode == "auto" and self._is_regex(query)):
            return self._search_regex(query, top_k)

        return self._search_bm25(query, top_k)

    @property
    def tool_count(self) -> int:
        """索引中的工具数量。"""
        return self._num_docs


# ============================================================================
# search_tools 内置工具
# ============================================================================

def search_tools(query: str = "", mode: str = "auto", task_id=None, **kwargs) -> str:
    """搜索可用的工具。

    模型通过此工具按需发现延迟加载的工具。
    始终可见（defer_loading=False），是 Tool Search 机制的入口点。

    设计理由：
    - 直接从 ToolRegistry 读取延迟加载的工具，无需全局单例注入
    - 每次调用时构建 ToolSearch 实例（延迟工具数量少，构建开销可忽略）
    - 低耦合：不依赖 main.py 的初始化顺序

    Args:
        query: 查询字符串。自然语言（"send email"）或正则（"get_.*_data"）。
        mode: 搜索模式，"auto"（默认）| "bm25" | "regex"。
        task_id: 任务 ID（忽略，保持接口一致）。
        **kwargs: 其他参数（忽略）。

    Returns:
        JSON 格式的工具 schema 列表（最多 5 个）。
    """
    if not query:
        return json.dumps([], ensure_ascii=False)

    # 直接从注册表读取延迟加载的工具，构建搜索引擎
    from src.tools.registry import get_deferred_tools

    deferred_tools = get_deferred_tools()
    if not deferred_tools:
        return json.dumps([], ensure_ascii=False)

    deferred_schemas = [entry.schema for entry in deferred_tools]
    searcher = ToolSearch(deferred_schemas)

    try:
        results = searcher.search(query, mode=mode, top_k=5)
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        logger.error(f"search_tools 执行失败: {e}")
        return json.dumps({"error": str(e)})


def check_search_tools_requirements() -> bool:
    """search_tools 始终可用。"""
    return True


# 注册 search_tools 工具（始终可见，不延迟加载）
def _register_search_tools() -> None:
    """注册 search_tools 内置工具。"""
    from src.tools.registry import register_tool

    register_tool(
        name="search_tools",
        toolset="search",
        schema={
            "name": "search_tools",
            "description": (
                "Search for tools that are not currently loaded. Use this when you need a capability "
                "that none of the visible tools provide, or when you suspect a tool exists for a specific task.\n\n"
                "Use natural language queries like 'send a message to a user' or 'create a pull request'. "
                "You can also use regex patterns like 'get_.*_data' for precise matching.\n\n"
                "Use 'select:<name>[,<name>...]' to explicitly load specific tools by name "
                "(e.g., 'select:execute_code,process'). Maximum 10 tools per query.\n\n"
                "Returns up to 5 matching tool schemas. After discovering tools, you can call them directly in the next turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query: natural language (e.g., 'send email'), "
                            "regex pattern (e.g., 'get_.*_data'), "
                            "or select syntax (e.g., 'select:execute_code,process')."
                        ),
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "bm25", "regex"],
                        "description": "Search mode. 'auto' (default) detects query type automatically. 'bm25' for natural language. 'regex' for pattern matching.",
                        "default": "auto",
                    },
                },
                "required": ["query"],
            },
        },
        handler=search_tools,
        check_fn=check_search_tools_requirements,
        description="搜索可用的工具",
        defer_loading=False,
    )


_register_search_tools()
