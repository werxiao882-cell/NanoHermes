"""工具 DFX 组件单元测试。

测试覆盖:
- retry_classifier.py: 错误分类器
- result_budget.py: 结果预算
- execution_tracker.py: 执行追踪器
- concurrency_limiter.py: 并发限流器
"""

import pytest
import time
import threading


# ─── ToolErrorClassifier 测试 ─────────────────────────────────


class TestToolErrorClassifier:
    """错误分类器测试。"""

    def test_connection_error_reconnect(self):
        """连接错误应分类为可重试 + reconnect。"""
        from src.tools.dfx.retry_classifier import (
            ToolErrorClassifier, RecoveryAction
        )
        classifier = ToolErrorClassifier()

        for err_msg in [
            "ECONNRESET",
            "EPIPE",
            "Connection refused",
            "Connection reset",
            "Connection timed out",
            "Broken pipe",
            "Network is unreachable",
        ]:
            result = classifier.classify(ConnectionError(err_msg))
            assert result.is_retryable is True
            assert result.action == RecoveryAction.RECONNECT

    def test_rate_limit_backoff(self):
        """限流错误应分类为可重试 + backoff。"""
        from src.tools.dfx.retry_classifier import (
            ToolErrorClassifier, RecoveryAction
        )
        classifier = ToolErrorClassifier()

        for err_msg in [
            "429 Too Many Requests",
            "529 Service Unavailable",
            "rate limit exceeded",
            "too many requests",
            "overloaded",
            "capacity exceeded",
        ]:
            result = classifier.classify(RuntimeError(err_msg))
            assert result.is_retryable is True
            assert result.action == RecoveryAction.BACKOFF

    def test_auth_error_refresh_credentials(self):
        """认证错误应分类为可重试 + refresh_credentials。"""
        from src.tools.dfx.retry_classifier import (
            ToolErrorClassifier, RecoveryAction
        )
        classifier = ToolErrorClassifier()

        for err_msg in [
            "401 Unauthorized",
            "token expired",
            "token invalid",
            "Authentication failed",
            "Invalid API key",
        ]:
            result = classifier.classify(RuntimeError(err_msg))
            assert result.is_retryable is True
            assert result.action == RecoveryAction.REFRESH_CREDENTIALS

    def test_non_retryable_errors(self):
        """工具逻辑错误应分类为不可重试。"""
        from src.tools.dfx.retry_classifier import (
            ToolErrorClassifier, RecoveryAction
        )
        classifier = ToolErrorClassifier()

        for exc_type in [
            ValueError("invalid value"),
            TypeError("wrong type"),
            FileNotFoundError("not found"),
            PermissionError("denied"),
            KeyError("missing key"),
            AttributeError("no attribute"),
        ]:
            result = classifier.classify(exc_type)
            assert result.is_retryable is False
            assert result.action == RecoveryAction.FAIL

    def test_unknown_error_non_retryable(self):
        """未知错误应保守视为不可重试。"""
        from src.tools.dfx.retry_classifier import (
            ToolErrorClassifier, RecoveryAction
        )
        classifier = ToolErrorClassifier()

        result = classifier.classify(RuntimeError("unknown error"))
        assert result.is_retryable is False
        assert result.action == RecoveryAction.FAIL

    def test_exponential_backoff_with_jitter(self):
        """退避延迟应指数增长且包含抖动。"""
        from src.tools.dfx.retry_classifier import ToolErrorClassifier, BASE_DELAY_MS

        classifier = ToolErrorClassifier(base_delay_ms=100, max_delay_ms=10000)

        # 多次采样验证平均增长趋势
        all_delays = []
        for _ in range(10):
            delays = []
            for attempt in range(1, 6):
                delay = classifier._calculate_delay(attempt)
                delays.append(delay)
            all_delays.append(delays)

        # 计算平均延迟
        avg_delays = [sum(d[i] for d in all_delays) / len(all_delays) for i in range(5)]

        # 平均延迟应大致指数增长（至少 1.3 倍）
        for i in range(1, len(avg_delays)):
            assert avg_delays[i] > avg_delays[i - 1] * 1.3

        # 不应超过最大延迟
        for delays in all_delays:
            for delay in delays:
                assert delay <= 10000

    def test_retry_after_extraction(self):
        """应能从错误信息中提取 Retry-After 值。"""
        from src.tools.dfx.retry_classifier import ToolErrorClassifier
        import re
        classifier = ToolErrorClassifier()

        pattern = re.compile(r"Retry-After:\s*(\d+)", re.IGNORECASE)
        match = pattern.search("429 Retry-After: 30")
        assert match is not None

        retry_after = classifier._extract_retry_after(None, match)
        assert retry_after == 30000  # 30 秒 = 30000 毫秒

    def test_retry_after_from_headers(self):
        """应能从 HTTP 头中提取 Retry-After。"""
        from src.tools.dfx.retry_classifier import ToolErrorClassifier
        classifier = ToolErrorClassifier()

        headers = {"Retry-After": "60"}
        retry_after = classifier._extract_retry_after(headers, None)
        assert retry_after == 60000  # 60 秒 = 60000 毫秒

    def test_should_retry_whitelist(self):
        """白名单外的工具不应重试。"""
        from src.tools.dfx.retry_classifier import ToolErrorClassifier
        classifier = ToolErrorClassifier()

        # ValueError 不可重试
        assert not classifier.should_retry(
            ValueError("bad"), 1, "read_file", {"read_file"}
        )

        # 工具不在白名单中
        assert not classifier.should_retry(
            ConnectionError("Connection reset"), 1, "terminal", {"read_file"}
        )

        # 工具在白名单中且错误可重试
        assert classifier.should_retry(
            ConnectionError("Connection reset"), 1, "read_file", {"read_file"}
        )

    def test_max_retries_exceeded(self):
        """超过最大重试次数不应再重试。"""
        from src.tools.dfx.retry_classifier import ToolErrorClassifier
        classifier = ToolErrorClassifier(max_retries=3)

        assert classifier.should_retry(
            ConnectionError("Connection reset"), 3, "read_file", {"read_file"}
        )
        assert not classifier.should_retry(
            ConnectionError("Connection reset"), 4, "read_file", {"read_file"}
        )


# ─── Result Budget 测试 ──────────────────────────────────────


class TestResultBudget:
    """结果预算测试。"""

    def test_small_result_no_truncation(self):
        """小结果不应截断。"""
        from src.tools.dfx.result_budget import (
            apply_tool_result_budget, DEFAULT_RESULT_BUDGET_TOKENS
        )
        result = "hello world"
        truncated = apply_tool_result_budget(result, budget=8000)
        assert truncated == result

    def test_large_result_truncated(self):
        """大结果应头尾保留截断。"""
        from src.tools.dfx.result_budget import apply_tool_result_budget
        result = "A" * 20000
        truncated = apply_tool_result_budget(result, budget=1000)

        assert "[output truncated" in truncated
        assert "tokens" in truncated
        assert "bytes omitted" in truncated
        assert len(truncated) < len(result)

    def test_truncated_preserves_head_and_tail(self):
        """截断应保留头部和尾部。"""
        from src.tools.dfx.result_budget import apply_tool_result_budget
        result = "HEAD" + "X" * 20000 + "TAIL"
        truncated = apply_tool_result_budget(result, budget=1000)

        assert truncated.startswith("HEAD")
        assert truncated.endswith("TAIL")

    def test_terminal_budget_default(self):
        """terminal 工具应使用更严格的预算。"""
        from src.tools.dfx.result_budget import get_result_budget
        assert get_result_budget("terminal") == 4000
        assert get_result_budget("read_file") == 8000

    def test_custom_budget_override(self):
        """自定义预算应覆盖默认值。"""
        from src.tools.dfx.result_budget import get_result_budget
        assert get_result_budget("terminal", tool_budget=2000) == 2000

    def test_env_variable_budget(self):
        """环境变量应覆盖默认预算。"""
        import os
        from src.tools.dfx.result_budget import get_result_budget

        os.environ["NANOHERMES_TOOL_RESULT_BUDGET"] = "5000"
        try:
            assert get_result_budget("read_file") == 5000
        finally:
            del os.environ["NANOHERMES_TOOL_RESULT_BUDGET"]

    def test_error_result_not_truncated(self):
        """JSON 错误结果不应截断。"""
        from src.tools.dfx.result_budget import apply_budget_to_dispatch_result
        import json
        error_result = json.dumps({"error": "something went wrong"})
        result = apply_budget_to_dispatch_result(error_result, "terminal")
        assert result == error_result

    def test_estimate_tokens(self):
        """Token 估算应大致准确。"""
        from src.tools.dfx.result_budget import estimate_tokens
        text = "hello world"
        tokens = estimate_tokens(text)
        assert tokens > 0
        # 英文文本: 字符数 * 0.75 ≈ token 数
        assert tokens == pytest.approx(len(text) * 0.75, abs=2)


# ─── Execution Tracker 测试 ──────────────────────────────────


class TestExecutionTracker:
    """执行追踪器测试。"""

    def setup_method(self):
        """每个测试前重置追踪器。"""
        from src.tools.dfx.execution_tracker import ToolExecutionTracker
        tracker = ToolExecutionTracker()
        tracker.reset()

    def test_mark_start(self):
        """标记开始应成功。"""
        from src.tools.dfx.execution_tracker import ToolExecutionTracker
        tracker = ToolExecutionTracker()
        assert tracker.mark_start("call_1", "read_file") is True
        assert tracker.is_in_progress("call_1") is True

    def test_prevent_reentry(self):
        """防重入应拒绝重复执行。"""
        from src.tools.dfx.execution_tracker import ToolExecutionTracker
        tracker = ToolExecutionTracker()
        assert tracker.mark_start("call_1", "read_file") is True
        assert tracker.mark_start("call_1", "read_file") is False

    def test_mark_complete(self):
        """标记完成应更新状态。"""
        from src.tools.dfx.execution_tracker import (
            ToolExecutionTracker, ToolExecutionStatus
        )
        tracker = ToolExecutionTracker()
        tracker.mark_start("call_1", "read_file")
        state = tracker.mark_complete("call_1", result_length=500)
        assert state is not None
        assert state.status == ToolExecutionStatus.COMPLETED
        assert state.result_length == 500
        assert state.duration_ms is not None
        assert not tracker.is_in_progress("call_1")

    def test_mark_failed(self):
        """标记失败应记录错误。"""
        from src.tools.dfx.execution_tracker import (
            ToolExecutionTracker, ToolExecutionStatus
        )
        tracker = ToolExecutionTracker()
        tracker.mark_start("call_1", "read_file")
        state = tracker.mark_failed("call_1", error="FileNotFoundError")
        assert state is not None
        assert state.status == ToolExecutionStatus.FAILED
        assert "FileNotFoundError" in state.error

    def test_mark_timeout(self):
        """标记超时应记录超时状态。"""
        from src.tools.dfx.execution_tracker import (
            ToolExecutionTracker, ToolExecutionStatus
        )
        tracker = ToolExecutionTracker()
        tracker.mark_start("call_1", "read_file")
        state = tracker.mark_timeout("call_1")
        assert state is not None
        assert state.status == ToolExecutionStatus.TIMEOUT

    def test_get_active_count(self):
        """活跃计数应正确。"""
        from src.tools.dfx.execution_tracker import ToolExecutionTracker
        tracker = ToolExecutionTracker()
        assert tracker.get_active_count() == 0
        tracker.mark_start("call_1", "read_file")
        tracker.mark_start("call_2", "write_file")
        assert tracker.get_active_count() == 2
        tracker.mark_complete("call_1")
        assert tracker.get_active_count() == 1

    def test_statistics(self):
        """统计信息应正确。"""
        from src.tools.dfx.execution_tracker import ToolExecutionTracker
        tracker = ToolExecutionTracker()
        tracker.mark_start("call_1", "read_file")
        tracker.mark_complete("call_1")
        tracker.mark_start("call_2", "write_file")
        tracker.mark_failed("call_2", "error")

        stats = tracker.get_statistics()
        assert stats["total_completed"] == 1
        assert stats["total_failed"] == 1
        assert stats["active_count"] == 0

    def test_history_limit(self):
        """历史记录应限制大小。"""
        from src.tools.dfx.execution_tracker import ToolExecutionTracker, MAX_HISTORY_SIZE
        tracker = ToolExecutionTracker()
        for i in range(MAX_HISTORY_SIZE + 10):
            tracker.mark_start(f"call_{i}", "read_file")
            tracker.mark_complete(f"call_{i}")

        history = tracker.get_history(limit=1000)
        assert len(history) <= MAX_HISTORY_SIZE

    def test_thread_safety(self):
        """多线程并发操作应安全。"""
        from src.tools.dfx.execution_tracker import ToolExecutionTracker
        tracker = ToolExecutionTracker()

        def worker(n):
            tracker.mark_start(f"call_{n}", "read_file")
            time.sleep(0.01)
            tracker.mark_complete(f"call_{n}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert tracker.get_active_count() == 0
        stats = tracker.get_statistics()
        assert stats["total_completed"] == 10


# ─── Concurrency Limiter 测试 ────────────────────────────────


class TestConcurrencyLimiter:
    """并发限流器测试。"""

    def test_get_max_tool_concurrency_default(self):
        """默认并发数应为 10。"""
        from src.tools.dfx.concurrency_limiter import (
            get_max_tool_concurrency, DEFAULT_MAX_CONCURRENCY
        )
        assert get_max_tool_concurrency() == DEFAULT_MAX_CONCURRENCY

    def test_get_max_tool_concurrency_env(self):
        """环境变量应覆盖默认值。"""
        import os
        from src.tools.dfx.concurrency_limiter import get_max_tool_concurrency

        os.environ["NANOHERMES_MAX_TOOL_CONCURRENCY"] = "5"
        try:
            assert get_max_tool_concurrency() == 5
        finally:
            del os.environ["NANOHERMES_MAX_TOOL_CONCURRENCY"]

    def test_register_tool(self):
        """注册工具应创建信号量。"""
        from src.tools.dfx.concurrency_limiter import (
            ToolConcurrencyLimiter, ToolConcurrencyConfig
        )
        limiter = ToolConcurrencyLimiter(max_concurrency=5)
        limiter.register_tool("read_file", max_concurrent_instances=20, is_concurrency_safe=True)
        assert "read_file" in limiter.tool_configs
        assert limiter.tool_configs["read_file"].max_concurrent_instances == 20

    def test_partition_tool_calls(self):
        """工具调用应正确分组。"""
        from src.tools.dfx.concurrency_limiter import (
            ToolConcurrencyLimiter, ToolConcurrencyConfig
        )
        limiter = ToolConcurrencyLimiter(max_concurrency=5)
        limiter.register_tool("read_file", is_concurrency_safe=True)
        limiter.register_tool("write_file", is_concurrency_safe=False)

        tool_calls = [
            {"name": "read_file"},
            {"name": "read_file"},
            {"name": "write_file"},
            {"name": "read_file"},
        ]
        batches = limiter.partition_tool_calls(tool_calls)

        # 前两个 read_file 应合并为一个并发组
        assert batches[0]["is_concurrency_safe"] is True
        assert len(batches[0]["calls"]) == 2

        # write_file 单独为串行组
        assert batches[1]["is_concurrency_safe"] is False
        assert len(batches[1]["calls"]) == 1

        # 最后一个 read_file 为新并发组
        assert batches[2]["is_concurrency_safe"] is True
        assert len(batches[2]["calls"]) == 1

    def test_status_tracking(self):
        """限流器应正确追踪活跃工具。"""
        from src.tools.dfx.concurrency_limiter import ToolConcurrencyLimiter
        limiter = ToolConcurrencyLimiter(max_concurrency=5)
        limiter.register_tool("read_file", is_concurrency_safe=True)

        assert limiter.active_count == 0
        assert limiter.get_status()["max_concurrency"] == 5
