"""压缩验证器单元测试。

覆盖场景：
- 关键词提取（中英文、停用词过滤）
- 信息保留度验证
- 摘要长度验证
- 关键信息完整性验证
- 边界条件
"""

import pytest

from src.compression.validator import (
    CompressionValidator,
    ValidationResult,
    STOP_WORDS,
    FILE_CHANGE_KEYWORDS,
    TOOL_CALL_KEYWORDS,
)


class TestCompressionValidatorInit:
    """测试压缩验证器初始化。"""

    def test_default_parameters(self):
        """默认参数。"""
        validator = CompressionValidator()
        assert validator._min_retention_rate == 0.6
        assert validator._min_summary_length == 500
        assert validator._max_summary_length == 12000

    def test_custom_parameters(self):
        """自定义参数。"""
        validator = CompressionValidator(
            min_retention_rate=0.7,
            min_summary_length=300,
            max_summary_length=15000,
        )
        assert validator._min_retention_rate == 0.7
        assert validator._min_summary_length == 300
        assert validator._max_summary_length == 15000

    def test_invalid_retention_rate_too_low(self):
        """保留率过低抛出异常。"""
        with pytest.raises(ValueError, match="min_retention_rate must be between"):
            CompressionValidator(min_retention_rate=-0.1)

    def test_invalid_retention_rate_too_high(self):
        """保留率过高抛出异常。"""
        with pytest.raises(ValueError, match="min_retention_rate must be between"):
            CompressionValidator(min_retention_rate=1.5)

    def test_invalid_min_length_negative(self):
        """最小长度为负数抛出异常。"""
        with pytest.raises(ValueError, match="min_summary_length must be non-negative"):
            CompressionValidator(min_summary_length=-100)

    def test_invalid_max_length_less_than_min(self):
        """最大长度小于最小长度抛出异常。"""
        with pytest.raises(ValueError, match="max_summary_length must be >="):
            CompressionValidator(min_summary_length=1000, max_summary_length=500)


class TestKeywordExtraction:
    """测试关键词提取。"""

    def test_extract_english_keywords(self):
        """提取英文关键词。"""
        validator = CompressionValidator()
        text = "The user wants to create a new file"
        keywords = validator.extract_keywords(text)

        assert "user" in keywords
        assert "create" in keywords
        assert "file" in keywords
        assert "new" in keywords

    def test_extract_chinese_keywords(self):
        """提取中文关键词。"""
        validator = CompressionValidator()
        # 中文文本没有空格分隔，会被提取为连续的字符序列
        text = "用户 创建 文件"
        keywords = validator.extract_keywords(text)

        assert "用户" in keywords
        assert "创建" in keywords
        assert "文件" in keywords

    def test_filter_stop_words(self):
        """过滤停用词。"""
        validator = CompressionValidator()
        text = "the a an is are was were"
        keywords = validator.extract_keywords(text)

        # 停用词应该被过滤
        assert len(keywords) == 0

    def test_filter_short_words(self):
        """过滤短词（长度 < 2）。"""
        validator = CompressionValidator()
        text = "I a an the"
        keywords = validator.extract_keywords(text)

        # 长度 < 2 的词应该被过滤
        assert "I" not in keywords
        assert "a" not in keywords

    def test_empty_text(self):
        """空文本返回空集合。"""
        validator = CompressionValidator()
        keywords = validator.extract_keywords("")
        assert keywords == set()

    def test_mixed_language(self):
        """混合语言文本。"""
        validator = CompressionValidator()
        text = "用户 user 创建 create 文件 file"
        keywords = validator.extract_keywords(text)

        assert "用户" in keywords
        assert "user" in keywords
        assert "创建" in keywords
        assert "create" in keywords


class TestRetentionRate:
    """测试信息保留度计算。"""

    def test_high_retention_rate(self):
        """高信息保留率。"""
        validator = CompressionValidator()
        original = [
            {"role": "user", "content": "Create a file named test.py"},
            {"role": "assistant", "content": "I created test.py file"},
        ]
        summary = "Created test.py file as requested"

        rate = validator.calculate_retention_rate(original, summary)
        assert rate > 0.5  # 应该有较高的保留率

    def test_low_retention_rate(self):
        """低信息保留率。"""
        validator = CompressionValidator()
        original = [
            {"role": "user", "content": "Create a file named test.py with specific content"},
            {"role": "assistant", "content": "I created the file with all the required content"},
        ]
        summary = "Something completely different and unrelated"

        rate = validator.calculate_retention_rate(original, summary)
        assert rate < 0.3  # 应该有较低的保留率

    def test_empty_original(self):
        """空原始消息。"""
        validator = CompressionValidator()
        rate = validator.calculate_retention_rate([], "Some summary")
        assert rate == 0.0

    def test_empty_summary(self):
        """空摘要。"""
        validator = CompressionValidator()
        original = [{"role": "user", "content": "Hello world"}]
        rate = validator.calculate_retention_rate(original, "")
        assert rate == 0.0

    def test_both_empty(self):
        """原始消息和摘要都为空。"""
        validator = CompressionValidator()
        rate = validator.calculate_retention_rate([], "")
        assert rate == 1.0


class TestSummaryLengthValidation:
    """测试摘要长度验证。"""

    def test_valid_length(self):
        """有效长度。"""
        validator = CompressionValidator(min_summary_length=100, max_summary_length=1000)
        summary = "a" * 500  # 500 字符

        is_valid, warnings = validator.validate_summary_length(summary)
        assert is_valid is True
        assert len(warnings) == 0

    def test_too_short(self):
        """摘要过短。"""
        validator = CompressionValidator(min_summary_length=100, max_summary_length=1000)
        summary = "a" * 50  # 50 字符

        is_valid, warnings = validator.validate_summary_length(summary)
        assert is_valid is False
        assert len(warnings) == 1
        assert "too short" in warnings[0].lower()

    def test_too_long(self):
        """摘要过长。"""
        validator = CompressionValidator(min_summary_length=100, max_summary_length=1000)
        summary = "a" * 1500  # 1500 字符

        is_valid, warnings = validator.validate_summary_length(summary)
        assert is_valid is False
        assert len(warnings) == 1
        assert "too long" in warnings[0].lower()

    def test_at_min_boundary(self):
        """在最小边界。"""
        validator = CompressionValidator(min_summary_length=100, max_summary_length=1000)
        summary = "a" * 100

        is_valid, warnings = validator.validate_summary_length(summary)
        assert is_valid is True

    def test_at_max_boundary(self):
        """在最大边界。"""
        validator = CompressionValidator(min_summary_length=100, max_summary_length=1000)
        summary = "a" * 1000

        is_valid, warnings = validator.validate_summary_length(summary)
        assert is_valid is True


class TestKeyInformationCheck:
    """测试关键信息完整性检查。"""

    def test_has_file_changes(self):
        """包含文件变更信息。"""
        validator = CompressionValidator()
        original = [
            {"role": "user", "content": "Create a file named test.py"},
        ]
        compressed = [
            {"role": "system", "content": "Summary: Created test.py file"},
        ]
        summary = "Created test.py file"

        result = validator.check_key_information(original, compressed, summary)
        assert result["has_file_changes"] is True

    def test_no_file_changes(self):
        """不包含文件变更信息。"""
        validator = CompressionValidator()
        original = [
            {"role": "user", "content": "What is the weather today?"},
        ]
        compressed = [
            {"role": "system", "content": "Summary: User asked about weather"},
        ]
        summary = "User asked about weather"

        result = validator.check_key_information(original, compressed, summary)
        assert result["has_file_changes"] is False

    def test_has_user_intent(self):
        """包含用户意图。"""
        validator = CompressionValidator()
        original = []
        compressed = [
            {"role": "system", "content": "Summary"},
            {"role": "user", "content": "Latest user message"},  # 最后 5 条中有用户消息
        ]
        summary = "Summary"

        result = validator.check_key_information(original, compressed, summary)
        assert result["has_user_intent"] is True

    def test_no_user_intent(self):
        """不包含用户意图。"""
        validator = CompressionValidator()
        original = []
        compressed = [
            {"role": "system", "content": "Summary"},
            {"role": "assistant", "content": "Assistant message 1"},
            {"role": "assistant", "content": "Assistant message 2"},
            {"role": "assistant", "content": "Assistant message 3"},
            {"role": "assistant", "content": "Assistant message 4"},
            {"role": "assistant", "content": "Assistant message 5"},
        ]
        summary = "Summary"

        result = validator.check_key_information(original, compressed, summary)
        assert result["has_user_intent"] is False

    def test_has_tool_calls(self):
        """包含工具调用信息。"""
        validator = CompressionValidator()
        original = [
            {"role": "assistant", "content": "I will use the tool to help you", "tool_calls": []},
        ]
        compressed = [
            {"role": "system", "content": "Summary: Used tool to assist"},
        ]
        summary = "Used tool to assist user"

        result = validator.check_key_information(original, compressed, summary)
        assert result["has_tool_calls"] is True


class TestValidation:
    """测试综合验证。"""

    def test_validation_pass(self):
        """验证通过。"""
        validator = CompressionValidator(
            min_retention_rate=0.3,
            min_summary_length=10,
            max_summary_length=1000,
        )
        original = [
            {"role": "user", "content": "Create a file named test.py"},
        ]
        compressed = [
            {"role": "system", "content": "Summary: Created test.py"},
            {"role": "user", "content": "Thanks"},
        ]
        summary = "Created test.py file as requested by user"

        result = validator.validate(original, compressed, summary)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.retention_rate > 0.3
        assert result.summary_length >= 10
        assert len(result.warnings) == 0

    def test_validation_fail_low_retention(self):
        """验证失败：信息保留率低。"""
        validator = CompressionValidator(
            min_retention_rate=0.8,  # 高阈值
            min_summary_length=10,
            max_summary_length=1000,
        )
        original = [
            {"role": "user", "content": "Create a file named test.py with specific content"},
        ]
        compressed = [
            {"role": "system", "content": "Summary"},
        ]
        summary = "Something completely different"

        result = validator.validate(original, compressed, summary)

        assert result.is_valid is False
        assert result.retention_rate < 0.8
        assert len(result.warnings) > 0
        assert any("retention" in w.lower() for w in result.warnings)

    def test_validation_fail_short_summary(self):
        """验证失败：摘要过短。"""
        validator = CompressionValidator(
            min_retention_rate=0.1,
            min_summary_length=100,  # 高阈值
            max_summary_length=1000,
        )
        original = [{"role": "user", "content": "Hello"}]
        compressed = [{"role": "system", "content": "Hi"}]
        summary = "Short"

        result = validator.validate(original, compressed, summary)

        assert result.is_valid is False
        assert result.summary_length < 100
        assert any("short" in w.lower() for w in result.warnings)

    def test_validation_fail_long_summary(self):
        """验证失败：摘要过长。"""
        validator = CompressionValidator(
            min_retention_rate=0.1,
            min_summary_length=10,
            max_summary_length=100,  # 低阈值
        )
        original = [{"role": "user", "content": "Hello"}]
        compressed = [{"role": "system", "content": "Hi"}]
        summary = "a" * 200  # 200 字符

        result = validator.validate(original, compressed, summary)

        assert result.is_valid is False
        assert result.summary_length > 100
        assert any("long" in w.lower() for w in result.warnings)

    def test_validation_result_structure(self):
        """验证结果结构。"""
        validator = CompressionValidator()
        original = [{"role": "user", "content": "Hello"}]
        compressed = [{"role": "system", "content": "Hi"}]
        summary = "Hello world summary"

        result = validator.validate(original, compressed, summary)

        # 验证所有字段存在
        assert hasattr(result, "is_valid")
        assert hasattr(result, "retention_rate")
        assert hasattr(result, "summary_length")
        assert hasattr(result, "has_file_changes")
        assert hasattr(result, "has_user_intent")
        assert hasattr(result, "has_tool_calls")
        assert hasattr(result, "warnings")

        # 验证类型
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.retention_rate, float)
        assert isinstance(result.summary_length, int)
        assert isinstance(result.has_file_changes, bool)
        assert isinstance(result.has_user_intent, bool)
        assert isinstance(result.has_tool_calls, bool)
        assert isinstance(result.warnings, list)


class TestValidationEdgeCases:
    """测试验证器边界条件。"""

    def test_empty_messages(self):
        """空消息列表。"""
        validator = CompressionValidator()
        result = validator.validate([], [], "")

        assert isinstance(result, ValidationResult)
        assert result.retention_rate == 1.0  # 空对空
        assert result.summary_length == 0

    def test_non_string_content(self):
        """非字符串内容。"""
        validator = CompressionValidator()
        original = [
            {"role": "user", "content": 123},  # 非字符串
        ]
        compressed = [{"role": "system", "content": "Summary"}]
        summary = "Summary text"

        result = validator.validate(original, compressed, summary)
        assert isinstance(result, ValidationResult)

    def test_missing_content_field(self):
        """缺少 content 字段。"""
        validator = CompressionValidator()
        original = [
            {"role": "user"},  # 缺少 content
        ]
        compressed = [{"role": "system", "content": "Summary"}]
        summary = "Summary text"

        result = validator.validate(original, compressed, summary)
        assert isinstance(result, ValidationResult)
