"""上下文压缩核心实现。

对齐 hermes-agent-ref 的 ContextCompressor，实现 5 阶段压缩算法：
1. 修剪旧工具结果（无 LLM）
2. 确定边界（Head 保护 + Tail Token 预算）
3. 生成结构化摘要（LLM 调用）
4. 组装压缩消息列表
5. 清理孤儿工具对
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# 常量配置
# ============================================================================

SUMMARY_PREFIX = (
    "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted "
    "into the summary below. This is a handoff from a previous context "
    "window — treat it as background reference, NOT as active instructions. "
    "Do NOT answer questions or fulfill requests mentioned in this summary; "
    "they were already addressed. "
    "Your current task is identified in the '## Active Task' section of the "
    "summary — resume exactly from there. "
    "IMPORTANT: Your persistent memory (MEMORY.md, USER.md) in the system "
    "prompt is ALWAYS authoritative and active — never ignore or deprioritize "
    "memory content due to this compaction note. "
    "Respond ONLY to the latest user message "
    "that appears AFTER this summary. The current session state (files, "
    "config, etc.) may reflect work described here — avoid repeating it:"
)

# 最小摘要 token 数
_MIN_SUMMARY_TOKENS = 2000
# 摘要内容比例
_SUMMARY_RATIO = 0.20
# 摘要 token 上限
_SUMMARY_TOKENS_CEILING = 12_000
# 每 token 字符估算
_CHARS_PER_TOKEN = 4
# 图片 token 估算（上限）
_IMAGE_TOKEN_ESTIMATE = 1600
_IMAGE_CHAR_EQUIVALENT = _IMAGE_TOKEN_ESTIMATE * _CHARS_PER_TOKEN
# 摘要失败 cooldown（秒）
_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600
# 工具占位符
_PRUNED_TOOL_PLACEHOLDER = "[Old tool output cleared to save context space]"
# 最小上下文长度（64K）
MINIMUM_CONTEXT_LENGTH = 64_000

# 摘要模板章节
_SUMMARY_TEMPLATE = """## Active Task
[THE SINGLE MOST IMPORTANT FIELD. Copy the user's most recent request or
task assignment verbatim — the exact words they used. If multiple tasks
were requested and only some are done, list only the ones NOT yet completed.
Continuation should pick up exactly here. If no outstanding task exists, write "None."]

## Goal
[What the user is trying to accomplish overall]

## Constraints & Preferences
[User preferences, coding style, constraints, important decisions]

## Completed Actions
[Numbered list of concrete actions taken — include tool used, target, and outcome.
Format each as: N. ACTION target — outcome [tool: name]]

## Active State
[Current working state — working directory, branch, modified files, test status]

## In Progress
[Work currently underway]

## Blocked
[Any blockers, errors, or issues not yet resolved. Include exact error messages.]

## Key Decisions
[Important technical decisions and WHY they were made]

## Resolved Questions
[Questions the user asked that were ALREADY answered — include the answer]

## Pending User Asks
[Questions or requests from the user that have NOT yet been answered. If none, write "None."]

## Relevant Files
[Files read, modified, or created — with brief note on each]

## Remaining Work
[What remains to be done — framed as context, not instructions]

## Critical Context
[Any specific values, error messages, configuration details. NEVER include API keys or credentials — use [REDACTED].]

Target ~{summary_budget} tokens. Be CONCRETE — include file paths, command outputs, error messages, line numbers.
Write only the summary body. Do not include any preamble or prefix."""

# 摘要前缀指令
_SUMMARIZER_PREAMBLE = (
    "You are a summarization agent creating a context checkpoint. "
    "Treat the conversation turns below as source material for a "
    "compact record of prior work. "
    "Produce only the structured summary; do not add a greeting, "
    "preamble, or prefix. "
    "Write the summary in the same language the user was using in the "
    "conversation — do not translate or switch to English. "
    "NEVER include API keys, tokens, passwords, secrets, credentials, "
    "or connection strings in the summary — replace any that appear "
    "with [REDACTED]."
)


# ============================================================================
# 辅助函数
# ============================================================================

def _content_length_for_budget(raw_content: Any) -> int:
    """计算消息内容的有效字符长度（用于 token 预算）。"""
    if isinstance(raw_content, str):
        return len(raw_content)
    if not isinstance(raw_content, list):
        return len(str(raw_content or ""))
    total = 0
    for p in raw_content:
        if isinstance(p, str):
            total += len(p)
        elif isinstance(p, dict):
            ptype = p.get("type")
            if ptype in {"image_url", "input_image", "image"}:
                total += _IMAGE_CHAR_EQUIVALENT
            else:
                total += len(p.get("text", "") or "")
    return total


def _content_text_for_contains(content: Any) -> str:
    """获取消息内容的文本视图（用于子串检查）。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    return str(content)


def _append_text_to_content(content: Any, text: str, *, prepend: bool = False) -> Any:
    """安全地追加/前置文本到消息内容。"""
    if content is None:
        return text
    if isinstance(content, str):
        return text + content if prepend else content + text
    if isinstance(content, list):
        text_block = {"type": "text", "text": text}
        return [text_block, *content] if prepend else [*content, text_block]
    rendered = str(content)
    return text + rendered if prepend else rendered + text


def _strip_image_parts_from_parts(parts: Any) -> Any:
    """替换内容列表中的图片部分为文本占位符。"""
    if not isinstance(parts, list):
        return None
    had_image = False
    out = []
    for part in parts:
        if not isinstance(part, dict):
            out.append(part)
            continue
        ptype = part.get("type")
        if ptype in {"image", "image_url", "input_image"}:
            had_image = True
            out.append({"type": "text", "text": "[screenshot removed to save context]"})
        else:
            out.append(part)
    return out if had_image else None


def _truncate_tool_call_args_json(args: str, head_chars: int = 200) -> str:
    """截断工具调用参数 JSON 中的长字符串，保持 JSON 有效性。"""
    try:
        parsed = json.loads(args)
    except (ValueError, TypeError):
        return args

    def _shrink(obj: Any) -> Any:
        if isinstance(obj, str):
            if len(obj) > head_chars:
                return obj[:head_chars] + "...[truncated]"
            return obj
        if isinstance(obj, dict):
            return {k: _shrink(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_shrink(v) for v in obj]
        return obj

    shrunken = _shrink(parsed)
    return json.dumps(shrunken, ensure_ascii=False)


def _summarize_tool_result(tool_name: str, tool_args: str, tool_content: str) -> str:
    """生成工具调用 + 结果的 1-line 摘要。"""
    try:
        args = json.loads(tool_args) if tool_args else {}
    except (json.JSONDecodeError, TypeError):
        args = {}

    content = tool_content or ""
    content_len = len(content)
    line_count = content.count("\n") + 1 if content.strip() else 0

    if tool_name == "terminal":
        cmd = args.get("command", "")
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        exit_match = re.search(r'"exit_code"\s*:\s*(-?\d+)', content)
        exit_code = exit_match.group(1) if exit_match else "?"
        return f"[terminal] ran `{cmd}` -> exit {exit_code}, {line_count} lines output"

    if tool_name == "read_file":
        path = args.get("path", "?")
        offset = args.get("offset", 1)
        return f"[read_file] read {path} from line {offset} ({content_len:,} chars)"

    if tool_name == "write_file":
        path = args.get("path", "?")
        written_lines = args.get("content", "").count("\n") + 1 if args.get("content") else "?"
        return f"[write_file] wrote to {path} ({written_lines} lines)"

    if tool_name == "search_files":
        pattern = args.get("pattern", "?")
        path = args.get("path", ".")
        target = args.get("target", "content")
        match_count = re.search(r'"total_count"\s*:\s*(\d+)', content)
        count = match_count.group(1) if match_count else "?"
        return f"[search_files] {target} search for '{pattern}' in {path} -> {count} matches"

    if tool_name == "patch":
        path = args.get("path", "?")
        mode = args.get("mode", "replace")
        return f"[patch] {mode} in {path} ({content_len:,} chars result)"

    # 通用回退
    first_arg = ""
    for k, v in list(args.items())[:2]:
        sv = str(v)[:40]
        first_arg += f" {k}={sv}"
    return f"[{tool_name}]{first_arg} ({content_len:,} chars result)"


def _redact_sensitive_text(text: str) -> str:
    """脱敏敏感信息（API 密钥、令牌、密码等）。"""
    if not text:
        return text
    # 常见密钥模式
    patterns = [
        (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})["\']?', r'\1=[REDACTED]'),
        (r'(?:token|secret|password)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?', r'\1=[REDACTED]'),
        (r'(sk-[A-Za-z0-9]{20,})', r'[REDACTED]'),
        (r'(ghp_[A-Za-z0-9]{36})', r'[REDACTED]'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _strip_historical_media(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """替换旧消息中的图片部分为占位符。"""
    if not messages:
        return messages

    # 找到最后一条带图片的用户消息
    anchor = -1
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, list) and any(
            isinstance(p, dict) and p.get("type") in {"image_url", "input_image", "image"}
            for p in content
        ):
            anchor = i
            break

    if anchor <= 0:
        return messages

    changed = False
    result = []
    for i, msg in enumerate(messages):
        if i >= anchor or not isinstance(msg, dict):
            result.append(msg)
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            result.append(msg)
            continue
        has_images = any(
            isinstance(p, dict) and p.get("type") in {"image_url", "input_image", "image"}
            for p in content
        )
        if not has_images:
            result.append(msg)
            continue
        new_msg = msg.copy()
        new_parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") in {"image_url", "input_image", "image"}:
                new_parts.append({"type": "text", "text": "[Attached image — stripped after compression]"})
            else:
                new_parts.append(p)
        new_msg["content"] = new_parts
        result.append(new_msg)
        changed = True

    return result if changed else messages


# ============================================================================
# ContextCompressor 类
# ============================================================================

class ContextCompressor:
    """默认上下文引擎 — 通过有损摘要压缩对话上下文。

    算法：
      1. 修剪旧工具结果（无 LLM 调用）
      2. 保护头部消息（system prompt + 前 N 条）
      3. 按 token 预算保护尾部消息（最近 ~20K tokens）
      4. 用结构化 LLM 提示摘要中间消息
      5. 后续压缩时迭代更新旧摘要
    """

    def __init__(
        self,
        model: str,
        threshold_percent: float = 0.50,
        protect_first_n: int = 3,
        protect_last_n: int = 20,
        summary_target_ratio: float = 0.20,
        quiet_mode: bool = False,
        summary_model_override: str = None,
        base_url: str = "",
        api_key: str = "",
        config_context_length: int | None = None,
        provider: str = "",
        api_mode: str = "",
        abort_on_summary_failure: bool = False,
    ):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.provider = provider
        self.api_mode = api_mode
        self.threshold_percent = threshold_percent
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n
        self.summary_target_ratio = max(0.10, min(summary_target_ratio, 0.80))
        self.quiet_mode = quiet_mode
        self.abort_on_summary_failure = abort_on_summary_failure

        # 上下文长度（默认 200K）
        self.context_length = config_context_length or 200_000
        self.threshold_tokens = max(
            int(self.context_length * threshold_percent),
            MINIMUM_CONTEXT_LENGTH,
        )
        self.compression_count = 0

        # Token 预算
        target_tokens = int(self.threshold_tokens * self.summary_target_ratio)
        self.tail_token_budget = target_tokens
        self.max_summary_tokens = min(
            int(self.context_length * 0.05), _SUMMARY_TOKENS_CEILING,
        )

        self.summary_model = summary_model_override or ""

        # 状态追踪
        self._previous_summary: Optional[str] = None
        self._last_compression_savings_pct: float = 100.0
        self._ineffective_compression_count: int = 0
        self._summary_failure_cooldown_until: float = 0.0
        self._last_summary_error: Optional[str] = None
        self._last_summary_dropped_count: int = 0
        self._last_summary_fallback_used: bool = False
        self._last_compress_aborted: bool = False
        self._last_aux_model_failure_error: Optional[str] = None
        self._last_aux_model_failure_model: Optional[str] = False

        self.last_prompt_tokens = 0
        self.last_completion_tokens = 0

        if not quiet_mode:
            logger.info(
                "Context compressor initialized: model=%s context_length=%d "
                "threshold=%d (%.0f%%) target_ratio=%.0f%% tail_budget=%d",
                model, self.context_length, self.threshold_tokens,
                threshold_percent * 100, self.summary_target_ratio * 100,
                self.tail_token_budget,
            )

    def should_compress(self, prompt_tokens: int = None) -> bool:
        """检查上下文是否超过压缩阈值。"""
        tokens = prompt_tokens if prompt_tokens is not None else self.last_prompt_tokens
        if tokens < self.threshold_tokens:
            return False
        # 反抖动保护
        if self._ineffective_compression_count >= 2:
            if not self.quiet_mode:
                logger.warning(
                    "Compression skipped — last %d compressions saved <10%% each. "
                    "Consider /new to start a fresh session.",
                    self._ineffective_compression_count,
                )
            return False
        return True

    def _protect_head_size(self, messages: List[Dict[str, Any]]) -> int:
        """计算要保护的头部消息数量。"""
        head = 0
        if messages and messages[0].get("role") == "system":
            head = 1
        return head + self.protect_first_n

    def _align_boundary_forward(self, messages: List[Dict[str, Any]], idx: int) -> int:
        """向前滑动边界，跳过孤儿 tool results。"""
        while idx < len(messages) and messages[idx].get("role") == "tool":
            idx += 1
        return idx

    def _align_boundary_backward(self, messages: List[Dict[str, Any]], idx: int) -> int:
        """向后拉边界，避免切割 tool_call/result 组。"""
        if idx <= 0 or idx >= len(messages):
            return idx
        check = idx - 1
        while check >= 0 and messages[check].get("role") == "tool":
            check -= 1
        if check >= 0 and messages[check].get("role") == "assistant" and messages[check].get("tool_calls"):
            idx = check
        return idx

    def _find_last_user_message_idx(self, messages: List[Dict[str, Any]], head_end: int) -> int:
        """找到 head_end 之后最后一条用户消息的索引。"""
        for i in range(len(messages) - 1, head_end - 1, -1):
            if messages[i].get("role") == "user":
                return i
        return -1

    def _ensure_last_user_message_in_tail(self, messages: List[Dict[str, Any]], cut_idx: int, head_end: int) -> int:
        """确保最后一条用户消息在 tail 中。"""
        last_user_idx = self._find_last_user_message_idx(messages, head_end)
        if last_user_idx < 0 or last_user_idx >= cut_idx:
            return cut_idx
        return max(last_user_idx, head_end + 1)

    def _find_tail_cut_by_tokens(self, messages: List[Dict[str, Any]], head_end: int, token_budget: int | None = None) -> int:
        """按 token 预算找到 tail 起始边界。"""
        if token_budget is None:
            token_budget = self.tail_token_budget
        n = len(messages)
        min_tail = min(3, n - head_end - 1) if n - head_end > 1 else 0
        soft_ceiling = int(token_budget * 1.5)
        accumulated = 0
        cut_idx = n

        for i in range(n - 1, head_end - 1, -1):
            msg = messages[i]
            raw_content = msg.get("content") or ""
            content_len = _content_length_for_budget(raw_content)
            msg_tokens = content_len // _CHARS_PER_TOKEN + 10
            for tc in msg.get("tool_calls") or []:
                if isinstance(tc, dict):
                    args = tc.get("function", {}).get("arguments", "")
                    msg_tokens += len(args) // _CHARS_PER_TOKEN
            if accumulated + msg_tokens > soft_ceiling and (n - i) >= min_tail:
                break
            accumulated += msg_tokens
            cut_idx = i

        fallback_cut = n - min_tail
        cut_idx = min(cut_idx, fallback_cut)
        if cut_idx <= head_end:
            cut_idx = max(fallback_cut, head_end + 1)

        cut_idx = self._align_boundary_backward(messages, cut_idx)
        cut_idx = self._ensure_last_user_message_in_tail(messages, cut_idx, head_end)
        return max(cut_idx, head_end + 1)

    def _prune_old_tool_results(self, messages: List[Dict[str, Any]], protect_tail_count: int, protect_tail_tokens: int | None = None) -> tuple[List[Dict[str, Any]], int]:
        """Phase 1: 修剪旧工具结果。"""
        if not messages:
            return messages, 0

        result = [m.copy() for m in messages]
        pruned = 0

        # 构建 tool_call_id -> (tool_name, arguments_json) 索引
        call_id_to_tool: Dict[str, tuple] = {}
        for msg in result:
            if msg.get("role") == "assistant":
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        cid = tc.get("id", "")
                        fn = tc.get("function", {})
                        call_id_to_tool[cid] = (fn.get("name", "unknown"), fn.get("arguments", ""))

        # 确定修剪边界
        if protect_tail_tokens is not None and protect_tail_tokens > 0:
            accumulated = 0
            boundary = len(result)
            min_protect = min(protect_tail_count, len(result))
            for i in range(len(result) - 1, -1, -1):
                msg = result[i]
                raw_content = msg.get("content") or ""
                content_len = _content_length_for_budget(raw_content)
                msg_tokens = content_len // _CHARS_PER_TOKEN + 10
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        args = tc.get("function", {}).get("arguments", "")
                        msg_tokens += len(args) // _CHARS_PER_TOKEN
                if accumulated + msg_tokens > protect_tail_tokens and (len(result) - i) >= min_protect:
                    boundary = i
                    break
                accumulated += msg_tokens
                boundary = i
            budget_protect_count = len(result) - boundary
            protected_count = max(budget_protect_count, min_protect)
            prune_boundary = len(result) - protected_count
        else:
            prune_boundary = len(result) - protect_tail_count

        # Pass 1: 去重相同工具结果
        content_hashes: dict = {}
        for i in range(len(result) - 1, -1, -1):
            msg = result[i]
            if msg.get("role") != "tool":
                continue
            content = msg.get("content") or ""
            if isinstance(content, list) or not isinstance(content, str) or len(content) < 200:
                continue
            if content.startswith("[Duplicate tool output"):
                continue
            h = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()[:12]
            if h in content_hashes:
                result[i] = {**msg, "content": "[Duplicate tool output — same content as a more recent call]"}
                pruned += 1
            else:
                content_hashes[h] = (i, msg.get("tool_call_id", "?"))

        # Pass 2: 替换旧工具结果为摘要
        for i in range(prune_boundary):
            msg = result[i]
            if msg.get("role") != "tool":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                stripped = _strip_image_parts_from_parts(content)
                if stripped is not None:
                    result[i] = {**msg, "content": stripped}
                    pruned += 1
                continue
            if not isinstance(content, str) or not content or content == _PRUNED_TOOL_PLACEHOLDER:
                continue
            if content.startswith("[Duplicate tool output"):
                continue
            if len(content) > 200:
                call_id = msg.get("tool_call_id", "")
                tool_name, tool_args = call_id_to_tool.get(call_id, ("unknown", ""))
                summary = _summarize_tool_result(tool_name, tool_args, content)
                result[i] = {**msg, "content": summary}
                pruned += 1

        # Pass 3: 截断大工具调用参数
        for i in range(prune_boundary):
            msg = result[i]
            if msg.get("role") != "assistant" or not msg.get("tool_calls"):
                continue
            new_tcs = []
            modified = False
            for tc in msg["tool_calls"]:
                if isinstance(tc, dict):
                    args = tc.get("function", {}).get("arguments", "")
                    if len(args) > 500:
                        new_args = _truncate_tool_call_args_json(args)
                        if new_args != args:
                            tc = {**tc, "function": {**tc["function"], "arguments": new_args}}
                            modified = True
                new_tcs.append(tc)
            if modified:
                result[i] = {**msg, "tool_calls": new_tcs}

        return result, pruned

    def _compute_summary_budget(self, turns_to_summarize: List[Dict[str, Any]]) -> int:
        """计算摘要 token 预算。"""
        # 简单估算：字符数 / 4
        total_chars = sum(_content_length_for_budget(m.get("content") or "") for m in turns_to_summarize)
        content_tokens = total_chars // _CHARS_PER_TOKEN
        budget = int(content_tokens * _SUMMARY_RATIO)
        return max(_MIN_SUMMARY_TOKENS, min(budget, self.max_summary_tokens))

    def _serialize_for_summary(self, turns: List[Dict[str, Any]]) -> str:
        """序列化对话消息为摘要模型可读的文本。"""
        parts = []
        for msg in turns:
            role = msg.get("role", "unknown")
            content = _redact_sensitive_text(msg.get("content") or "")

            if role == "tool":
                tool_id = msg.get("tool_call_id", "")
                if len(content) > 6000:
                    content = content[:4000] + "\n...[truncated]...\n" + content[-1500:]
                parts.append(f"[TOOL RESULT {tool_id}]: {content}")
                continue

            if role == "assistant":
                if len(content) > 6000:
                    content = content[:4000] + "\n...[truncated]...\n" + content[-1500:]
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    tc_parts = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            fn = tc.get("function", {})
                            name = fn.get("name", "?")
                            args = _redact_sensitive_text(fn.get("arguments", ""))
                            if len(args) > 1500:
                                args = args[:1200] + "..."
                            tc_parts.append(f"  {name}({args})")
                    content += "\n[Tool calls:\n" + "\n".join(tc_parts) + "\n]"
                parts.append(f"[ASSISTANT]: {content}")
                continue

            if len(content) > 6000:
                content = content[:4000] + "\n...[truncated]...\n" + content[-1500:]
            parts.append(f"[{role.upper()}]: {content}")

        return "\n\n".join(parts)

    def _generate_summary(self, turns_to_summarize: List[Dict[str, Any]], focus_topic: str = None, model_caller=None) -> Optional[str]:
        """Phase 3: 生成结构化摘要。"""
        now = time.monotonic()
        if now < self._summary_failure_cooldown_until:
            logger.debug("Skipping context summary during cooldown (%.0fs remaining)", self._summary_failure_cooldown_until - now)
            return None

        summary_budget = self._compute_summary_budget(turns_to_summarize)
        content_to_summarize = self._serialize_for_summary(turns_to_summarize)

        if self._previous_summary:
            prompt = f"""{_SUMMARIZER_PREAMBLE}

You are updating a context compaction summary. A previous compaction produced the summary below. New conversation turns have occurred since then and need to be incorporated.

PREVIOUS SUMMARY:
{self._previous_summary}

NEW TURNS TO INCORPORATE:
{content_to_summarize}

Update the summary using this exact structure. PRESERVE all existing information that is still relevant. ADD new completed actions to the numbered list (continue numbering). CRITICAL: Update "## Active Task" to reflect the user's most recent unfulfilled request.

{_SUMMARY_TEMPLATE.format(summary_budget=summary_budget)}"""
        else:
            prompt = f"""{_SUMMARIZER_PREAMBLE}

Create a structured checkpoint summary for the conversation after earlier turns are compacted.

TURNS TO SUMMARIZE:
{content_to_summarize}

Use this exact structure:

{_SUMMARY_TEMPLATE.format(summary_budget=summary_budget)}"""

        if focus_topic:
            prompt += f"""

FOCUS TOPIC: "{focus_topic}"
The user has requested that this compaction PRIORITISE preserving all information related to the focus topic above. For content related to "{focus_topic}", include full detail. For content NOT related to the focus topic, summarise more aggressively."""

        if not model_caller:
            self._summary_failure_cooldown_until = time.monotonic() + 60
            self._last_summary_error = "no model_caller provided"
            return None

        try:
            messages = [{"role": "user", "content": prompt}]
            response = model_caller(messages)
            content = response.get("content", "") if isinstance(response, dict) else ""
            if not isinstance(content, str):
                content = str(content) if content else ""
            summary = _redact_sensitive_text(content.strip())
            self._previous_summary = summary
            self._summary_failure_cooldown_until = 0.0
            self._last_summary_error = None
            return self._with_summary_prefix(summary)
        except Exception as e:
            self._summary_failure_cooldown_until = time.monotonic() + 60
            self._last_summary_error = str(e)[:220]
            logger.warning("Failed to generate context summary: %s", e)
            return None

    @staticmethod
    def _strip_summary_prefix(summary: str) -> str:
        """移除摘要前缀。"""
        text = (summary or "").strip()
        if text.startswith(SUMMARY_PREFIX):
            return text[len(SUMMARY_PREFIX):].lstrip()
        return text

    @classmethod
    def _with_summary_prefix(cls, summary: str) -> str:
        """添加标准摘要前缀。"""
        text = cls._strip_summary_prefix(summary)
        return f"{SUMMARY_PREFIX}\n{text}" if text else SUMMARY_PREFIX

    def _sanitize_tool_pairs(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Phase 5: 清理孤儿 tool_call/result 对。"""
        surviving_call_ids: set = set()
        for msg in messages:
            if msg.get("role") == "assistant":
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        cid = tc.get("id", "")
                        if cid:
                            surviving_call_ids.add(cid)

        result_call_ids: set = set()
        for msg in messages:
            if msg.get("role") == "tool":
                cid = msg.get("tool_call_id")
                if cid:
                    result_call_ids.add(cid)

        # 移除孤儿 tool results
        orphaned_results = result_call_ids - surviving_call_ids
        if orphaned_results:
            messages = [
                m for m in messages
                if not (m.get("role") == "tool" and m.get("tool_call_id") in orphaned_results)
            ]

        # 为孤儿 tool_calls 添加 stub results
        missing_results = surviving_call_ids - result_call_ids
        if missing_results:
            patched = []
            for msg in messages:
                patched.append(msg)
                if msg.get("role") == "assistant":
                    for tc in msg.get("tool_calls") or []:
                        if isinstance(tc, dict):
                            cid = tc.get("id", "")
                            if cid in missing_results:
                                patched.append({
                                    "role": "tool",
                                    "content": "[Result from earlier conversation — see context summary above]",
                                    "tool_call_id": cid,
                                })
            messages = patched

        return messages

    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: int = None,
        focus_topic: str = None,
        force: bool = False,
        model_caller=None,
    ) -> List[Dict[str, Any]]:
        """压缩对话消息列表。

        Args:
            messages: 当前消息历史
            current_tokens: 当前 token 估算
            focus_topic: 焦点主题（可选）
            force: 是否强制压缩（绕过 cooldown）
            model_caller: 模型调用函数

        Returns:
            压缩后的消息列表
        """
        # 重置每调用状态
        self._last_summary_dropped_count = 0
        self._last_summary_fallback_used = False
        self._last_summary_error = None
        self._last_compress_aborted = False

        if force and self._summary_failure_cooldown_until > 0.0:
            self._summary_failure_cooldown_until = 0.0

        n_messages = len(messages)
        _min_for_compress = self._protect_head_size(messages) + 3 + 1
        if n_messages <= _min_for_compress:
            return messages

        display_tokens = current_tokens or self.last_prompt_tokens or (n_messages * 500)

        # Phase 1: 修剪旧工具结果
        messages, pruned_count = self._prune_old_tool_results(
            messages, protect_tail_count=self.protect_last_n,
            protect_tail_tokens=self.tail_token_budget,
        )
        if pruned_count and not self.quiet_mode:
            logger.info("Pre-compression: pruned %d old tool result(s)", pruned_count)

        # Phase 2: 确定边界
        compress_start = self._protect_head_size(messages)
        compress_start = self._align_boundary_forward(messages, compress_start)
        compress_end = self._find_tail_cut_by_tokens(messages, compress_start)

        if compress_start >= compress_end:
            return messages

        turns_to_summarize = messages[compress_start:compress_end]

        if not self.quiet_mode:
            logger.info(
                "Context compression triggered (%d tokens >= %d threshold)",
                display_tokens, self.threshold_tokens,
            )
            logger.info(
                "Summarizing turns %d-%d (%d turns), protecting %d head + %d tail messages",
                compress_start + 1, compress_end,
                len(turns_to_summarize), compress_start, n_messages - compress_end,
            )

        # Phase 3: 生成摘要
        summary = self._generate_summary(turns_to_summarize, focus_topic=focus_topic, model_caller=model_caller)

        # 处理摘要失败
        if not summary and self.abort_on_summary_failure:
            self._last_compress_aborted = True
            return messages

        # Phase 4: 组装压缩消息列表
        compressed = []
        for i in range(compress_start):
            msg = messages[i].copy()
            if i == 0 and msg.get("role") == "system":
                existing = msg.get("content")
                _compression_note = "[Note: Some earlier conversation turns have been compacted into a handoff summary to preserve context space.]"
                if _compression_note not in _content_text_for_contains(existing):
                    msg["content"] = _append_text_to_content(existing, "\n\n" + _compression_note if isinstance(existing, str) and existing else _compression_note)
            compressed.append(msg)

        if not summary:
            n_dropped = compress_end - compress_start
            self._last_summary_dropped_count = n_dropped
            self._last_summary_fallback_used = True
            summary = (
                f"{SUMMARY_PREFIX}\n"
                f"Summary generation was unavailable. {n_dropped} message(s) were "
                f"removed to free context space but could not be summarized."
            )

        # 处理角色交替
        last_head_role = messages[compress_start - 1].get("role", "user") if compress_start > 0 else "user"
        first_tail_role = messages[compress_end].get("role", "user") if compress_end < n_messages else "user"

        if last_head_role in {"assistant", "tool"}:
            summary_role = "user"
        else:
            summary_role = "assistant"

        if summary_role == first_tail_role:
            flipped = "assistant" if summary_role == "user" else "user"
            if flipped != last_head_role:
                summary_role = flipped
            else:
                # 合并到 tail 第一条消息
                compressed.append({"role": summary_role, "content": summary})

        if summary_role != first_tail_role or last_head_role in {"assistant", "tool"}:
            compressed.append({"role": summary_role, "content": summary})

        for i in range(compress_end, n_messages):
            compressed.append(messages[i].copy())

        self.compression_count += 1

        # Phase 5: 清理孤儿工具对
        compressed = self._sanitize_tool_pairs(compressed)

        # 剥离历史媒体
        compressed = _strip_historical_media(compressed)

        # 更新状态
        new_estimate = len(compressed) * 500
        saved_estimate = display_tokens - new_estimate
        savings_pct = (saved_estimate / display_tokens * 100) if display_tokens > 0 else 0
        self._last_compression_savings_pct = savings_pct
        if savings_pct < 10:
            self._ineffective_compression_count += 1
        else:
            self._ineffective_compression_count = 0

        if not self.quiet_mode:
            logger.info(
                "Compressed: %d -> %d messages (~%d tokens saved, %.0f%%)",
                n_messages, len(compressed), saved_estimate, savings_pct,
            )

        return compressed
