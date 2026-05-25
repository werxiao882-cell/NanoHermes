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
        error = APIError(message="Unauthorized", body={}, response=_mock_response(401))
        result = classify_error(error)
        assert result.category == ErrorCategory.AUTH
        assert result.retryable is False

    def test_auth_error_403(self):
        """测试 403 授权错误分类。"""
        error = APIError(message="Forbidden", body={}, response=_mock_response(403))
        result = classify_error(error)
        assert result.category == ErrorCategory.AUTH
        assert result.retryable is False

    def test_billing_error_402(self):
        """测试 402 计费错误分类。"""
        error = APIError(message="Payment required", body={}, response=_mock_response(402))
        result = classify_error(error)
        assert result.category == ErrorCategory.BILLING
        assert result.retryable is False

    def test_rate_limit_429(self):
        """测试 429 速率限制分类。"""
        error = APIError(message="Too many requests", body={}, response=_mock_response(429))
        result = classify_error(error)
        assert result.category == ErrorCategory.RATE_LIMIT
        assert result.retryable is True

    def test_server_error_500(self):
        """测试 500 服务器错误分类。"""
        error = APIError(message="Internal server error", body={}, response=_mock_response(500))
        result = classify_error(error)
        assert result.category == ErrorCategory.SERVER_ERROR
        assert result.retryable is True

    def test_server_error_502(self):
        """测试 502 网关错误分类。"""
        error = APIError(message="Bad gateway", body={}, response=_mock_response(502))
        result = classify_error(error)
        assert result.category == ErrorCategory.SERVER_ERROR
        assert result.retryable is True

    def test_context_overflow(self):
        """测试上下文溢出分类。"""
        error = APIError(
            message="This model's maximum context length is 8192 tokens",
            body={},
            response=_mock_response(400),
        )
        result = classify_error(error)
        assert result.category == ErrorCategory.CONTEXT_OVERFLOW
        assert result.retryable is False

    def test_network_error(self):
        """测试网络连接错误分类。"""
        error = APIConnectionError(message="Connection refused")
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


def _mock_response(status_code: int):
    """模拟 HTTP 响应对象。"""
    class MockResponse:
        def __init__(self, code):
            self.status_code = code
    return MockResponse(status_code)


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
