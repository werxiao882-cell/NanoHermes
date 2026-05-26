"""测试: OpenAI 客户端错误分类。"""

import pytest

from openai import APIError, APIConnectionError

from src.provider.openai_client import (
    ErrorCategory,
    ClassifiedError,
    classify_error,
    TokenUsage,
    extract_usage,
)


class TestClassifyError:
    """测试 classify_error 函数。"""

    def test_auth_error_401(self):
        """测试 401 认证错误分类。"""
        error = _make_api_error(401, "Unauthorized")
        result = classify_error(error)
        assert result.category == ErrorCategory.AUTH
        assert result.retryable is False

    def test_auth_error_403(self):
        """测试 403 授权错误分类。"""
        error = _make_api_error(403, "Forbidden")
        result = classify_error(error)
        assert result.category == ErrorCategory.AUTH
        assert result.retryable is False

    def test_billing_error_402(self):
        """测试 402 计费错误分类。"""
        error = _make_api_error(402, "Payment required")
        result = classify_error(error)
        assert result.category == ErrorCategory.BILLING
        assert result.retryable is False

    def test_rate_limit_429(self):
        """测试 429 速率限制分类。"""
        error = _make_api_error(429, "Too many requests")
        result = classify_error(error)
        assert result.category == ErrorCategory.RATE_LIMIT
        assert result.retryable is True

    def test_server_error_500(self):
        """测试 500 服务器错误分类。"""
        error = _make_api_error(500, "Internal server error")
        result = classify_error(error)
        assert result.category == ErrorCategory.SERVER_ERROR
        assert result.retryable is True

    def test_server_error_502(self):
        """测试 502 网关错误分类。"""
        error = _make_api_error(502, "Bad gateway")
        result = classify_error(error)
        assert result.category == ErrorCategory.SERVER_ERROR
        assert result.retryable is True

    def test_context_overflow(self):
        """测试上下文溢出分类。"""
        error = _make_api_error(400, "This model's maximum context length is 8192 tokens")
        result = classify_error(error)
        assert result.category == ErrorCategory.CONTEXT_OVERFLOW
        assert result.retryable is False

    def test_network_error(self):
        """测试网络连接错误分类。"""
        error = _make_connection_error("Connection refused")
        result = classify_error(error)
        assert result.category == ErrorCategory.NETWORK_ERROR
        assert result.retryable is True

    def test_unknown_error(self):
        """测试未知错误分类。"""
        error = ValueError("some random error")
        result = classify_error(error)
        assert result.category == ErrorCategory.UNKNOWN
        assert result.retryable is False


class TestExtractUsage:
    """测试 extract_usage 函数。"""

    def test_extract_usage_from_response(self):
        """测试从响应中提取 token 使用量。"""
        usage = _mock_usage(input_tokens=100, output_tokens=50)
        result = extract_usage(usage)
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.total_tokens == 150

    def test_extract_usage_none(self):
        """测试 usage 为 None 时返回默认值。"""
        result = extract_usage(None)
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.total_tokens == 0


def _make_api_error(status_code: int, message: str) -> APIError:
    """创建 APIError 实例（兼容新版 SDK）。"""
    error = APIError(
        message=message,
        body={"status_code": status_code},
        request=_make_mock_request(),
    )
    # 手动设置 status_code 属性（某些 SDK 版本需要）
    error.status_code = status_code
    return error


def _make_connection_error(message: str) -> APIConnectionError:
    """创建 APIConnectionError 实例（兼容新版 SDK）。"""
    return APIConnectionError(
        message=message,
        request=_make_mock_request(),
    )


def _make_mock_request():
    """模拟 HTTP 请求对象。"""
    class MockRequest:
        def __init__(self):
            self.method = "POST"
            self.url = "https://api.example.com/v1/chat/completions"
    return MockRequest()


def _mock_usage(input_tokens: int, output_tokens: int):
    """模拟 usage 对象。"""
    class MockDetails:
        def __init__(self):
            self.cached_tokens = 0

    class MockUsage:
        def __init__(self):
            self.prompt_tokens = input_tokens
            self.completion_tokens = output_tokens
            self.prompt_tokens_details = MockDetails()

    return MockUsage()
