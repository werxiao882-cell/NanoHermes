"""上下文隔离机制。

使用 <memory-context> 标签包裹注入的记忆上下文，提供：
- sanitize_context: 一次性清洗函数，移除完整标签块和系统注释
- StreamingContextScrubber: 流式清洗器，处理可能被分割跨 chunk 的标签
"""

import re

# ============================================================================
# 一次性清洗
# ============================================================================

# 匹配完整的 <memory-context>...</memory-context> 块
INTERNAL_CONTEXT_RE = re.compile(
    r'<\s*memory-context\s*>[\s\S]*?<\/\s*memory-context\s*>',
    re.IGNORECASE
)

# 匹配系统注释 [System note: ...]
INTERNAL_NOTE_RE = re.compile(
    r'\[System note:\s*The following is recalled memory context,.*?\]\s*',
    re.IGNORECASE | re.DOTALL
)

# 匹配孤立的标签
FENCE_TAG_RE = re.compile(
    r'<\/?\s*memory-context\s*>',
    re.IGNORECASE
)


def sanitize_context(text: str) -> str:
    """清洗文本，移除所有 <memory-context> 标签块、系统注释和孤立标签。

    Args:
        text: 原始文本。

    Returns:
        清洗后的文本。
    """
    text = INTERNAL_CONTEXT_RE.sub('', text)
    text = INTERNAL_NOTE_RE.sub('', text)
    text = FENCE_TAG_RE.sub('', text)
    return text


# ============================================================================
# 流式清洗器
# ============================================================================

class StreamingContextScrubber:
    """流式上下文清洗器。

    使用状态机处理可能被分割跨 chunk 的 <memory-context> 标签。
    关键决策：
    - 在 span 内时，丢弃所有内容直到找到关闭标签
    - 在 span 外时，输出所有内容直到找到打开标签
    - 保留可能的部分标签在缓冲区，等待下一个 chunk 确认
    - flush 时，如果仍在 span 内，丢弃剩余内容（比泄露部分记忆上下文更安全）
    """

    OPEN_TAG = '<memory-context>'
    CLOSE_TAG = '</memory-context>'

    def __init__(self):
        self._in_span = False
        self._buf = ''
        self._at_block_boundary = True

    def reset(self) -> None:
        """重置清洗器状态。"""
        self._in_span = False
        self._buf = ''
        self._at_block_boundary = True

    def feed(self, text: str) -> str:
        """输入文本块，返回清洗后的可见内容。

        Args:
            text: 输入文本块。

        Returns:
            清洗后的可见内容（不包含记忆上下文）。
        """
        if not text:
            return ''

        buf = self._buf + text
        self._buf = ''
        out: list = []

        while buf:
            if self._in_span:
                # 在 span 内，查找关闭标签
                idx = buf.lower().find(self.CLOSE_TAG)
                if idx == -1:
                    # 没有关闭标签，保留可能的部分标签
                    held = self._max_partial_suffix(buf, self.CLOSE_TAG)
                    self._buf = buf[-held:] if held > 0 else ''
                    return ''.join(out)
                # 找到关闭标签，跳过 span 内容和标签
                buf = buf[idx + len(self.CLOSE_TAG):]
                self._in_span = False
            else:
                # 在 span 外，查找打开标签
                idx = self._find_boundary_open_tag(buf)
                if idx == -1:
                    # 没有打开标签，保留可能的部分标签
                    held = (
                        self._max_pending_open_suffix(buf)
                        or self._max_partial_suffix(buf, self.OPEN_TAG)
                    )
                    if held > 0:
                        self._append_visible(out, buf[:-held])
                        self._buf = buf[-held:]
                    else:
                        self._append_visible(out, buf)
                    return ''.join(out)
                # 输出标签前的文本，进入 span
                if idx > 0:
                    self._append_visible(out, buf[:idx])
                buf = buf[idx + len(self.OPEN_TAG):]
                self._in_span = True

        return ''.join(out)

    def flush(self) -> str:
        """刷新缓冲区，返回剩余的可见内容。

        Returns:
            剩余的可见内容。如果仍在 span 内，返回空字符串（丢弃）。
        """
        if self._in_span:
            # 仍在 span 内，丢弃剩余内容（更安全）
            self._buf = ''
            self._in_span = False
            return ''
        tail = self._buf
        self._buf = ''
        return tail

    def _max_partial_suffix(self, buf: str, tag: str) -> int:
        """查找缓冲区末尾可能匹配标签前缀的最大长度。

        Args:
            buf: 缓冲区内容。
            tag: 要匹配的标签。

        Returns:
            需要保留的字符数。
        """
        tag_lower = tag.lower()
        buf_lower = buf.lower()
        max_check = min(len(buf_lower), len(tag_lower) - 1)

        for i in range(max_check, 0, -1):
            if tag_lower.startswith(buf_lower[-i:]):
                return i
        return 0

    def _find_boundary_open_tag(self, buf: str) -> int:
        """在块边界处查找打开标签。

        标签必须出现在行首或空白字符后才被识别。

        Args:
            buf: 缓冲区内容。

        Returns:
            标签位置索引，未找到返回 -1。
        """
        buf_lower = buf.lower()
        search_start = 0

        while True:
            idx = buf_lower.find(self.OPEN_TAG, search_start)
            if idx == -1:
                return -1

            if self._is_block_boundary(buf, idx) and self._has_block_opener_suffix(buf, idx):
                return idx
            search_start = idx + 1

    def _is_block_boundary(self, buf: str, idx: int) -> bool:
        """检查标签前是否是块边界（行首或空白后）。

        Args:
            buf: 缓冲区内容。
            idx: 标签起始位置。

        Returns:
            True 如果是块边界。
        """
        if idx == 0:
            return True
        prev_char = buf[idx - 1]
        return prev_char in ('\n', ' ', '\t')

    def _has_block_opener_suffix(self, buf: str, idx: int) -> bool:
        """检查标签后是否是有效字符。

        打开标签 `<memory-context>` 后可以跟任何字符（包括内容直接开始）。

        Args:
            buf: 缓冲区内容。
            idx: 标签起始位置。

        Returns:
            True 如果标签后可以跟内容。
        """
        after_idx = idx + len(self.OPEN_TAG)
        if after_idx >= len(buf):
            return True
        # 标签后可以跟任何字符（内容直接开始）
        return True

    def _max_pending_open_suffix(self, buf: str) -> int:
        """查找缓冲区末尾可能的未完成打开标签长度。

        Args:
            buf: 缓冲区内容。

        Returns:
            需要保留的字符数。
        """
        if not buf.lower().endswith(self.OPEN_TAG):
            return 0
        idx = len(buf) - len(self.OPEN_TAG)
        if not self._is_block_boundary(buf, idx):
            return 0
        return len(self.OPEN_TAG)

    def _append_visible(self, out: list, text: str) -> None:
        """将可见文本追加到输出列表。

        Args:
            out: 输出列表。
            text: 可见文本。
        """
        if text:
            out.append(text)
