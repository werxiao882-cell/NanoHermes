"""上下文隔离机制。

使用 <memory-context> 标签包裹注入的记忆上下文，提供：
- sanitize_context: 一次性清洗函数，移除完整标签块和系统注释
- StreamingContextScrubber: 流式清洗器，处理可能被分割跨 chunk 的标签

设计原理：
    当 AI Agent 从记忆系统检索到历史上下文时，这些上下文需要被注入到提示词中。
    但检索到的记忆上下文本身可能包含之前注入的 <memory-context> 标签（因为
    历史对话中可能已经包含过记忆注入）。如果不清洗这些嵌套标签，会导致：
    1. 提示词膨胀：重复的记忆上下文不断累积
    2. 语义混乱：AI 可能误将旧的记忆上下文当作当前上下文
    3. 标签嵌套：多层 <memory-context> 嵌套可能破坏提示词结构

    因此需要在每次注入新记忆前，清洗掉文本中已有的记忆上下文标签及其内容。
"""

import re

# ============================================================================
# 一次性清洗
# ============================================================================

# 匹配完整的 <memory-context>...</memory-context> 块
# 使用 [\s\S]*? 而非 . 是因为 . 不匹配换行符，而记忆上下文可能包含多行
# 使用非贪婪匹配 *? 确保匹配最近的关闭标签，避免跨块匹配
INTERNAL_CONTEXT_RE = re.compile(
    r'<\s*memory-context\s*>[\s\S]*?<\/\s*memory-context\s*>',
    re.IGNORECASE
)

# 匹配系统注释 [System note: ...]
# 这是注入记忆上下文时添加的说明性注释，格式为：
# [System note: The following is recalled memory context, ...]
# 使用 re.DOTALL 使 . 匹配换行符，因为注释可能跨多行
INTERNAL_NOTE_RE = re.compile(
    r'\[System note:\s*The following is recalled memory context,.*?\]\s*',
    re.IGNORECASE | re.DOTALL
)

# 匹配孤立的标签（只有开标签或闭标签，没有配对）
# 这种情况可能发生在：
# 1. 流式输出被截断，标签不完整
# 2. 用户手动输入了类似标签的文本
# 3. 之前的清洗操作不完整
# \/?\s* 匹配可选的 / 和可选的空白，兼容 <memory-context> 和 </memory-context>
FENCE_TAG_RE = re.compile(
    r'<\/?\s*memory-context\s*>',
    re.IGNORECASE
)


def sanitize_context(text: str) -> str:
    """清洗文本，移除所有 <memory-context> 标签块、系统注释和孤立标签。

    为什么需要三步清洗：
        1. 先移除完整的标签块：处理正常配对的 <memory-context>...</memory-context>
        2. 再移除系统注释：这些注释是伴随记忆上下文注入的元信息
        3. 最后移除孤立标签：处理前两步可能留下的不成对标签

        顺序很重要：如果先移除孤立标签，会破坏完整标签块的结构，
        导致 INTERNAL_CONTEXT_RE 无法正确匹配。

    Args:
        text: 原始文本，可能包含嵌套的记忆上下文标签。

    Returns:
        清洗后的文本，不包含任何记忆上下文相关内容。
    """
    # 第一步：移除完整的 <memory-context>...</memory-context> 块
    # 这会移除标签及其包裹的所有内容（即实际注入的记忆）
    text = INTERNAL_CONTEXT_RE.sub('', text)
    # 第二步：移除伴随记忆注入的系统注释
    text = INTERNAL_NOTE_RE.sub('', text)
    # 第三步：清理可能残留的孤立标签（开标签或闭标签）
    text = FENCE_TAG_RE.sub('', text)
    return text


# ============================================================================
# 流式清洗器
# ============================================================================

class StreamingContextScrubber:
    """流式上下文清洗器。

    为什么需要这个类：
        sanitize_context() 函数适用于一次性处理完整文本的场景。
        但在流式输出（streaming）场景中，文本是分段（chunk by chunk）到达的，
        一个 <memory-context> 标签可能被分割在多个 chunk 之间。例如：
            chunk1: "一些文本<mem"
            chunk2: "ory-context>记忆内容</mem"
            chunk3: "ory-context>更多文本"

        如果使用一次性清洗，需要等待所有 chunk 到达后再处理，这会：
        1. 增加延迟：用户需要等待更长时间才能看到输出
        2. 增加内存：需要缓存所有 chunk 直到流结束
        3. 破坏流式体验：无法实现真正的实时输出

        StreamingContextScrubber 通过状态机逐 chunk 处理，可以：
        - 立即输出不在标签内的文本
        - 缓存可能被分割的标签部分
        - 在标签内时丢弃内容，不输出

    状态机设计：
        使用 _in_span 布尔值表示当前是否在 <memory-context> 标签内：
        - False (not_in_span): 正常状态，输出文本直到遇到开标签
        - True (in_span): 过滤状态，丢弃文本直到遇到闭标签

        状态转换：
        not_in_span --[发现 <memory-context>]--> in_span
        in_span     --[发现 </memory-context>]--> not_in_span

    缓冲区策略：
        为了避免将不完整的标签误判为普通文本，需要保留可能是标签前缀的
        字符在缓冲区中，等待下一个 chunk 来确认。例如：
        - 收到 "hello <mem" 时，不能立即输出 "<mem"，因为它可能是
          "<memory-context>" 的开头
        - 保留 "<mem" 在缓冲区，等下一个 chunk 到来后再决定

    安全考量：
        flush() 时如果仍在 span 内（即收到了开标签但没收到闭标签），
        选择丢弃缓冲区内容而不是输出。这是因为：
        1. 泄露部分记忆上下文比丢失部分用户文本更危险
        2. 记忆上下文可能包含敏感的历史对话内容
        3. 不完整的记忆上下文对 AI 也没有参考价值
    """

    # 硬编码标签字符串，用于流式匹配
    # 注意：这里不使用正则表达式，因为流式处理需要精确的字符串匹配
    # 来定位标签边界，正则表达式在部分匹配时难以处理
    OPEN_TAG = '<memory-context>'
    CLOSE_TAG = '</memory-context>'

    def __init__(self):
        # 状态机核心状态：是否在 <memory-context> 标签范围内
        # False = 正常输出模式，True = 过滤丢弃模式
        self._in_span = False
        # 缓冲区：存储可能是标签前缀的字符，等待下一个 chunk 确认
        # 例如：收到 "<mem" 时，暂存于此，等下一个 chunk 判断是否完整标签
        self._buf = ''
        # 块边界标记：用于判断标签是否出现在有效位置（行首或空白后）
        # 初始为 True，表示流开始处是一个有效的块边界
        self._at_block_boundary = True

    def reset(self) -> None:
        """重置清洗器状态。

        使用场景：
        - 开始新的流式输出前
        - 处理完一个完整响应后复用清洗器实例
        - 测试时重置状态
        """
        self._in_span = False
        self._buf = ''
        self._at_block_boundary = True

    def feed(self, text: str) -> str:
        """输入文本块，返回清洗后的可见内容。

        流式处理逻辑：
            1. 将新文本追加到缓冲区（可能有上一次残留的部分标签）
            2. 循环处理缓冲区，根据当前状态查找标签：
               - 在 span 内：查找 </memory-context>，找到后退出 span
               - 在 span 外：查找 <memory-context>，找到后进入 span
            3. 如果标签不完整（跨 chunk），保留可能的部分在缓冲区
            4. 返回已确认的可见文本

        为什么使用 while 循环：
            一个 chunk 可能包含多个标签，例如：
            "文本1<mem>记忆1</mem>文本2<mem>记忆2</mem>文本3"
            需要循环处理直到缓冲区为空或遇到不完整的标签。

        缓冲区保留策略（核心难点）：
            当标签被分割时，需要决定保留多少字符在缓冲区：
            - 如果保留太少：可能将标签前缀误输出给用户
            - 如果保留太多：会降低输出效率，增加延迟

            使用 _max_partial_suffix() 计算缓冲区末尾可能匹配标签前缀的
            最大长度，只保留这部分字符。例如：
            - 缓冲区："hello </mem"
            - CLOSE_TAG = "</memory-context>"
            - "</mem" 是 "</memory-context>" 的前缀，长度 6
            - 保留 6 个字符 "</mem" 在缓冲区

        Args:
            text: 输入文本块，可能包含完整的、部分的或不包含标签。

        Returns:
            清洗后的可见内容（不包含记忆上下文）。
            注意：返回的只是已确认安全的部分，可能少于输入。
        """
        if not text:
            return ''

        # 将新文本追加到缓冲区（合并上一次残留的部分标签前缀）
        buf = self._buf + text
        self._buf = ''  # 清空缓冲区，处理完后重新设置
        out: list = []  # 使用 list 累积输出，最后 join 比字符串拼接更高效

        while buf:
            if self._in_span:
                # ============================================================
                # 状态：在 <memory-context> 标签内（过滤模式）
                # ============================================================
                # 设计决策：在 span 内时，我们不需要输出任何内容，
                # 只需要找到闭标签来退出 span。
                #
                # 为什么不输出 span 内的内容？
                # 因为这些内容是之前注入的记忆上下文，不是当前响应的部分。
                # 如果输出给用户，会造成信息泄露和语义混乱。

                # 查找关闭标签 </memory-context>
                # 使用 .lower() 实现大小写不敏感匹配
                idx = buf.lower().find(self.CLOSE_TAG)
                if idx == -1:
                    # --------------------------------------------------------
                    # 没有找到关闭标签，当前 chunk 可能：
                    # 1. 完全不包含标签（纯记忆内容）
                    # 2. 包含不完整的闭标签前缀（如 "</mem"）
                    #
                    # 策略：保留可能是闭标签前缀的字符在缓冲区
                    # 例如：buf = "记忆内容</mem"，保留 "</mem"（6 字符）
                    # --------------------------------------------------------
                    held = self._max_partial_suffix(buf, self.CLOSE_TAG)
                    self._buf = buf[-held:] if held > 0 else ''
                    # 返回空字符串（span 内的内容全部丢弃）
                    return ''.join(out)

                # --------------------------------------------------------
                # 找到关闭标签！跳过标签及其之前的所有内容
                # 例如：buf = "记忆内容</memory-context>后续文本"
                #       idx = 4（"记忆内容" 的长度）
                #       buf 更新为 "后续文本"，状态变为 not_in_span
                # --------------------------------------------------------
                buf = buf[idx + len(self.CLOSE_TAG):]
                self._in_span = False
                # 继续循环，处理标签后的文本（现在是 not_in_span 状态）

            else:
                # ============================================================
                # 状态：不在 <memory-context> 标签内（正常输出模式）
                # ============================================================
                # 设计决策：在 span 外时，我们输出所有文本，
                # 直到遇到开标签 <memory-context>。
                #
                # 为什么需要 _find_boundary_open_tag() 而不是简单的 find()？
                # 因为我们需要确保标签出现在有效位置（行首或空白后），
                # 避免将用户输入的类似文本误判为标签。
                # 例如：用户说 "我用<mem>作为缩写" 不应该被识别为标签。

                # 在块边界处查找打开标签
                idx = self._find_boundary_open_tag(buf)
                if idx == -1:
                    # --------------------------------------------------------
                    # 没有找到打开标签，当前 chunk 可能：
                    # 1. 完全不包含标签（纯可见文本）
                    # 2. 包含不完整的开标签前缀（如 "<mem"）
                    # 3. 包含完整的开标签但不在块边界（如 "hello<mem"）
                    #
                    # 策略：计算需要保留的字符数，将可能的标签前缀
                    # 保留在缓冲区，其余部分输出
                    # --------------------------------------------------------

                    # 计算需要保留的字符数：
                    # 1. _max_pending_open_suffix: 检查末尾是否是完整的开标签
                    #    但不在块边界（如 "hello<mem" 中的 "<mem"）
                    # 2. _max_partial_suffix: 检查末尾是否是标签的部分前缀
                    held = (
                        self._max_pending_open_suffix(buf)
                        or self._max_partial_suffix(buf, self.OPEN_TAG)
                    )
                    if held > 0:
                        # 有需要保留的字符：输出保留字符之前的部分
                        # 例如：buf = "hello <mem"，held = 5 ("<mem")
                        #       输出 "hello "，保留 "<mem"
                        self._append_visible(out, buf[:-held])
                        self._buf = buf[-held:]
                    else:
                        # 没有需要保留的字符：全部输出
                        self._append_visible(out, buf)
                    return ''.join(out)

                # --------------------------------------------------------
                # 找到打开标签！输出标签前的文本，进入 span 状态
                # 例如：buf = "可见文本<mem>记忆内容"
                #       idx = 4（"可见文本" 的长度）
                #       输出 "可见文本"，buf 更新为 "记忆内容"
                #       状态变为 in_span，后续内容将被丢弃
                # --------------------------------------------------------
                if idx > 0:
                    # 标签前有可见文本，输出
                    self._append_visible(out, buf[:idx])
                # 跳过开标签，进入 span 状态
                buf = buf[idx + len(self.OPEN_TAG):]
                self._in_span = True
                # 继续循环，处理标签后的文本（现在是 in_span 状态）

        return ''.join(out)

    def flush(self) -> str:
        """刷新缓冲区，返回剩余的可见内容。

        调用时机：
            当流式输出结束时调用，处理缓冲区中可能残留的文本。

        安全考量（关键设计决策）：
            如果 flush 时仍在 span 内（_in_span = True），说明：
            - 收到了 <memory-context> 开标签
            - 但没有收到对应的 </memory-context> 闭标签
            - 缓冲区中可能包含部分记忆上下文内容

            此时选择丢弃缓冲区内容，原因：
            1. 安全性优先：泄露部分记忆上下文比丢失用户文本更危险
               记忆上下文可能包含敏感的历史对话、用户信息等
            2. 完整性考虑：不完整的记忆上下文对 AI 没有参考价值
               AI 需要完整的上下文才能正确理解，片段可能造成误导
            3. 错误恢复：如果流被意外截断，丢弃是安全的默认行为

            如果不在 span 内，缓冲区内容就是正常的可见文本，直接返回。

        Returns:
            剩余的可见内容。如果仍在 span 内，返回空字符串（已丢弃）。
        """
        if self._in_span:
            # 仍在 span 内：丢弃缓冲区中的记忆上下文片段
            # 这是安全决策：宁可丢失部分文本，也不泄露记忆内容
            self._buf = ''
            self._in_span = False
            return ''

        # 不在 span 内：缓冲区是正常的可见文本，返回
        tail = self._buf
        self._buf = ''
        return tail

    def _max_partial_suffix(self, buf: str, tag: str) -> int:
        """查找缓冲区末尾可能匹配标签前缀的最大长度。

        这个方法是流式处理的核心，用于解决标签跨 chunk 分割的问题。

        工作原理：
            检查缓冲区末尾的 N 个字符是否是标签的前缀。
            从最大可能长度开始检查，找到第一个匹配的前缀。

            例如：
            - buf = "hello </mem"
            - tag = "</memory-context>"
            - 检查末尾 10 字符（tag 长度 - 1）: "</mem"
            - "</mem" 是 "</memory-context>" 的前缀吗？是！
            - 返回 6，表示需要保留末尾 6 个字符

        为什么从最大长度开始检查：
            因为我们希望保留尽可能多的字符，避免误输出标签前缀。
            例如：buf = "text </mem"，如果只保留 2 字符 "em"，
            会输出 "text </m"，其中 "</m" 可能是标签的一部分。

        为什么最大检查长度是 len(tag) - 1：
            因为如果缓冲区末尾已经是完整的标签，它应该已经被
            feed() 中的 find() 匹配到了，不会进入这个方法。
            所以只需要检查不完整的部分前缀。

        Args:
            buf: 缓冲区内容。
            tag: 要匹配的标签（如 "</memory-context>"）。

        Returns:
            需要保留的字符数（0 表示没有需要保留的前缀）。
        """
        tag_lower = tag.lower()
        buf_lower = buf.lower()
        # 最大检查长度：缓冲区长度和标签长度-1 的较小值
        # 减 1 是因为完整标签应该已经被 find() 匹配
        max_check = min(len(buf_lower), len(tag_lower) - 1)

        # 从最大可能长度开始，递减检查
        for i in range(max_check, 0, -1):
            # 检查缓冲区末尾 i 个字符是否是标签的前缀
            if tag_lower.startswith(buf_lower[-i:]):
                return i
        return 0

    def _find_boundary_open_tag(self, buf: str) -> int:
        """在块边界处查找打开标签。

        为什么需要这个方法而不是简单的 buf.find(OPEN_TAG)？

        问题场景：
            用户可能在正常对话中输入类似标签的文本，例如：
            - "我用<mem>作为备忘录的缩写"
            - "HTML标签<memory-context>在网页中很常见"

            如果简单使用 find()，这些文本会被误判为记忆上下文标签，
            导致后续内容被错误过滤。

        解决方案：
            只识别出现在"块边界"的标签：
            1. 标签前是行首（idx == 0）
            2. 标签前是空白字符（\\n, 空格, 制表符）

            这样确保只有作为独立标记的标签被识别，
            而嵌入在单词中的类似文本被忽略。

        Args:
            buf: 缓冲区内容。

        Returns:
            标签位置索引，未找到返回 -1。
        """
        buf_lower = buf.lower()
        search_start = 0

        while True:
            # 查找下一个开标签
            idx = buf_lower.find(self.OPEN_TAG, search_start)
            if idx == -1:
                return -1

            # 检查标签是否在块边界且后面是有效字符
            if self._is_block_boundary(buf, idx) and self._has_block_opener_suffix(buf, idx):
                return idx
            # 不是有效边界，继续查找下一个
            search_start = idx + 1

    def _is_block_boundary(self, buf: str, idx: int) -> bool:
        """检查标签前是否是块边界（行首或空白后）。

        块边界的定义：
            - 标签在文本开头（idx == 0）
            - 标签前是换行符、空格或制表符

        为什么只检查这三个字符：
            1. 换行符：标签通常在新行开始
            2. 空格：标签前可能有缩进或分隔空格
            3. 制表符：类似空格，用于缩进

            不将其他字符（如标点符号）视为边界，是为了避免误判。
            例如："标签<memory-context>开始" 中的 "<" 前是中文，
            不应被视为块边界。

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

        设计决策：
            打开标签 `<memory-context>` 后可以跟任何字符，因为：
            1. 标签后直接是记忆内容，没有特定的分隔符要求
            2. 记忆内容可以是任何文本（包括换行、特殊字符等）
            3. 与闭标签不同，开标签不需要特定的后续字符来确认

            这个方法保留在这里是为了：
            1. 与 _is_block_boundary 形成对称的 API
            2. 未来如果需要添加后缀检查（如要求标签后是换行），
               可以方便地修改这个方法

        Args:
            buf: 缓冲区内容。
            idx: 标签起始位置。

        Returns:
            True（始终返回 True，因为开标签后可以跟任何字符）。
        """
        after_idx = idx + len(self.OPEN_TAG)
        if after_idx >= len(buf):
            # 标签在缓冲区末尾，后面没有字符，等待下一个 chunk
            return True
        # 标签后可以跟任何字符（内容直接开始）
        return True

    def _max_pending_open_suffix(self, buf: str) -> int:
        """查找缓冲区末尾可能的未完成打开标签长度。

        与 _max_partial_suffix 的区别：
            - _max_partial_suffix: 检查是否是标签的部分前缀（如 "<mem"）
            - _max_pending_open_suffix: 检查是否是完整的开标签，
              但不在块边界（如 "hello<mem>" 中的 "<mem>"）

        为什么需要这个方法：
            场景：buf = "hello<mem>"
            - 末尾是完整的 "<mem>" 吗？不是（应该是 "<memory-context>"）
            - 但如果 buf = "hello<mem"，末尾 "<mem" 是部分前缀

            更关键的场景：buf = "hello<mem"（不完整）
            - _max_partial_suffix 会返回 4（"<mem" 是前缀）
            - 但如果 buf = "hello<mem>" 且下一个 chunk 是 "ory-context>..."
            - 需要确保 "hello<mem" 不被输出

            这个方法专门处理：缓冲区末尾是完整开标签，但不在块边界的情况。
            此时标签不应被识别，但标签本身需要保留在缓冲区。

        Args:
            buf: 缓冲区内容。

        Returns:
            需要保留的字符数（0 表示没有需要保留的完整标签）。
        """
        # 检查缓冲区末尾是否是完整的开标签
        if not buf.lower().endswith(self.OPEN_TAG):
            return 0
        # 计算标签起始位置
        idx = len(buf) - len(self.OPEN_TAG)
        # 检查标签是否在块边界
        if not self._is_block_boundary(buf, idx):
            # 不在块边界，这个标签不应被识别
            # 但需要保留在缓冲区，等待更多上下文
            return 0
        # 在块边界，返回标签长度（整个标签需要保留）
        return len(self.OPEN_TAG)

    def _append_visible(self, out: list, text: str) -> None:
        """将可见文本追加到输出列表。

        为什么使用 list 而不是字符串拼接：
            在 Python 中，字符串是不可变的，每次拼接都会创建新字符串。
            对于频繁的追加操作，使用 list.append() + ''.join() 更高效。
            时间复杂度：O(n) vs O(n²)

        Args:
            out: 输出列表，累积所有可见文本片段。
            text: 要追加的可见文本。
        """
        if text:
            out.append(text)
