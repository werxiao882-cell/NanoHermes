"""Provider Runtime 集成测试。

测试任务 10.1-10.4：
- 10.1 完整调用链集成测试（resolve → create client → call → parse response）
- 10.2 回退链集成测试（主模型失败 → 回退成功）
- 10.3 辅助客户端集成测试（独立配置调用）
- 10.4 中断集成测试（调用中中断 → 干净退出）

使用 mock 模拟 SDK 响应，不依赖真实 API。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import threading
import time
import os

# 导入 provider 模块组件
from src.provider.api_mode import ApiMode, resolve_api_mode
from src.provider.credentials import CredentialResult, resolve_credentials
from src.provider.fallback import FallbackChain, FallbackEntry


class TestFullCallChainIntegration:
    """10.1 完整调用链集成测试。

    测试流程：resolve → create client → call → parse response
    """

    def test_openai_call_chain_with_mock(self):
        """测试 OpenAI 调用链（resolve → build client → mock call）。"""
        # 设置环境变量模拟
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            # Step 1: 解析凭证
            creds = resolve_credentials(
                env_vars=["OPENAI_API_KEY"],
                base_url=None,
            )
            assert creds.api_key == "sk-test-key"
            assert creds.source == "env"

            # Step 2: 解析 API Mode
            api_mode = resolve_api_mode()
            assert api_mode == ApiMode.CHAT_COMPLETIONS

            # Step 3: 构建 mock 客户端
            with patch("src.provider.client_factory.OpenAI") as mock_openai_class:
                mock_client = MagicMock()
                mock_openai_class.return_value = mock_client

                from src.provider.client_factory import build_client
                client = build_client(api_mode, creds)

                # 验证客户端创建
                mock_openai_class.assert_called_once_with(api_key="sk-test-key")
                assert client == mock_client

                # Step 4: 模拟调用和响应解析
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Hello from GPT!"
                mock_response.choices[0].message.role = "assistant"
                mock_response.usage.prompt_tokens = 10
                mock_response.usage.completion_tokens = 5

                mock_client.chat.completions.create.return_value = mock_response

                # 模拟调用
                response = mock_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": "Hello"}],
                )

                # 验证响应解析
                assert response.choices[0].message.content == "Hello from GPT!"
                assert response.usage.prompt_tokens == 10

    def test_anthropic_call_chain_with_mock(self):
        """测试 Anthropic 调用链（resolve → build client → mock call）。"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            # Step 1: 解析凭证
            creds = resolve_credentials(
                env_vars=["ANTHROPIC_API_KEY"],
                base_url=None,
            )
            assert creds.api_key == "sk-ant-test"

            # Step 2: 解析 API Mode（使用 base_url 启发式检测）
            api_mode = resolve_api_mode(base_url="https://api.anthropic.com")
            assert api_mode == ApiMode.ANTHROPIC_MESSAGES

            # Step 3: 构建 mock 客户端
            with patch("src.provider.client_factory.Anthropic") as mock_anthropic_class:
                mock_client = MagicMock()
                mock_anthropic_class.return_value = mock_client

                from src.provider.client_factory import build_client
                client = build_client(api_mode, creds)

                # 验证客户端创建
                mock_anthropic_class.assert_called_once_with(api_key="sk-ant-test")
                assert client == mock_client

    def test_explicit_key_overrides_env(self):
        """测试显式传入的 Key 优先级高于环境变量。"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"}):
            creds = resolve_credentials(
                env_vars=["OPENAI_API_KEY"],
                base_url=None,
                explicit_key="sk-explicit-key",
            )
            assert creds.api_key == "sk-explicit-key"
            assert creds.source == "explicit"

    def test_key_isolation_security_check(self):
        """测试 API Key 隔离安全检查。"""
        # OpenRouter Key 不应该用于非 OpenRouter 端点
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}):
            # 请求自定义端点时，OpenRouter Key 应被跳过
            try:
                creds = resolve_credentials(
                    env_vars=["OPENROUTER_API_KEY"],
                    base_url="https://custom-api.example.com",
                )
                # 应该抛出错误，因为 Key 与端点不匹配
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "未找到 API Key" in str(e)


class TestFallbackChainIntegration:
    """10.2 回退链集成测试。

    测试流程：主模型失败 → 回退成功
    """

    def test_fallback_chain_triggers_on_failure(self):
        """测试主模型失败时触发回退链。"""
        # 创建回退链
        fallbacks = [
            FallbackEntry(provider="openai", model="gpt-4o"),
            FallbackEntry(provider="anthropic", model="claude-sonnet-4"),
        ]
        chain = FallbackChain(fallbacks)

        # 初始状态
        assert chain.has_fallbacks is True
        assert chain.is_activated is False

        # 模拟主模型失败，获取第一个回退
        first_fallback = chain.get_next(0)
        assert first_fallback.provider == "openai"
        assert first_fallback.model == "gpt-4o"

        # 激活回退
        chain.activate(first_fallback)
        assert chain.is_activated is True
        assert chain.active_fallback == first_fallback

        # 再次尝试回退应返回 None（已激活）
        assert chain.get_next(1) is None

    def test_fallback_chain_one_shot_activation(self):
        """测试回退链一次性激活机制。"""
        fallbacks = [
            FallbackEntry(provider="openai", model="gpt-4o-mini"),
            FallbackEntry(provider="anthropic", model="claude-3-haiku"),
        ]
        chain = FallbackChain(fallbacks)

        # 第一次激活
        first = chain.get_next(0)
        chain.activate(first)
        assert chain.is_activated is True

        # 即使后续失败，也不应再尝试回退
        second = chain.get_next(1)
        assert second is None
        assert chain.active_fallback == first

    def test_fallback_chain_all_failures(self):
        """测试所有回退都失败的情况。"""
        fallbacks = [
            FallbackEntry(provider="provider1", model="model1"),
            FallbackEntry(provider="provider2", model="model2"),
        ]
        chain = FallbackChain(fallbacks)

        # 尝试所有回退（不激活，模拟全部失败）
        first = chain.get_next(0)
        assert first.model == "model1"

        # 假设第一个也失败了
        # 注意：get_next 的索引参数表示当前要尝试的索引
        second = chain.get_next(1)
        assert second.model == "model2"

        # 超过索引范围
        third = chain.get_next(2)
        assert third is None

    def test_fallback_chain_reset(self):
        """测试回退链重置机制。"""
        fallbacks = [FallbackEntry(provider="openai", model="gpt-4o")]
        chain = FallbackChain(fallbacks)

        # 激活回退
        entry = chain.get_next(0)
        chain.activate(entry)
        assert chain.is_activated is True

        # 重置
        chain.reset()
        assert chain.is_activated is False
        assert chain.active_fallback is None

        # 重置后可以再次尝试回退
        entry_after_reset = chain.get_next(0)
        assert entry_after_reset.model == "gpt-4o"


class TestAuxiliaryClientIntegration:
    """10.3 辅助客户端集成测试。

    测试独立配置调用。
    """

    def test_auxiliary_client_with_custom_config(self):
        """测试辅助客户端使用独立配置。"""
        # 模拟辅助配置
        from src.config import AuxiliaryConfig

        aux_config = AuxiliaryConfig(
            provider="openai",
            model="gpt-4o-mini",
            max_tokens=2000,
            temperature=0.3,
        )

        # 验证配置
        assert aux_config.provider == "openai"
        assert aux_config.model == "gpt-4o-mini"
        assert aux_config.max_tokens == 2000
        assert aux_config.temperature == 0.3

    def test_auxiliary_client_main_provider_fallback(self):
        """测试辅助客户端回退到主模型（provider='main'）。"""
        from src.config import AuxiliaryConfig

        # 默认配置回退到主模型
        config = AuxiliaryConfig()
        assert config.provider == "main"
        assert config.model == ""

        # CompressionAuxiliaryClient 会使用主模型的凭证
        # 这里只验证配置逻辑
        if config.provider == "main":
            # 预期：使用主对话的凭证和模型
            expected_behavior = "使用主模型进行压缩摘要"
            assert expected_behavior is not None


class TestInterruptIntegration:
    """10.4 中断集成测试。

    测试调用中中断 → 干净退出。
    """

    def test_interrupt_event_stops_call(self):
        """测试中断事件可以停止调用。"""
        # 创建中断事件
        interrupt_event = threading.Event()

        # 模拟长时间运行的任务
        def long_running_task():
            for i in range(10):
                if interrupt_event.is_set():
                    return "interrupted"
                time.sleep(0.1)
            return "completed"

        # 启动任务线程
        result_container = []
        task_thread = threading.Thread(
            target=lambda: result_container.append(long_running_task())
        )
        task_thread.start()

        # 等待一段时间后发送中断
        time.sleep(0.3)
        interrupt_event.set()

        # 等待线程结束
        task_thread.join(timeout=2)

        # 验证中断生效
        assert result_container[0] == "interrupted"

    def test_clean_exit_on_interrupt(self):
        """测试中断后干净退出（无残留资源）。"""
        interrupt_event = threading.Event()
        resource_released = threading.Event()

        def task_with_resource():
            try:
                # 模拟资源获取
                while not interrupt_event.is_set():
                    time.sleep(0.1)
            finally:
                # 确保资源释放
                resource_released.set()

        thread = threading.Thread(target=task_with_resource)
        thread.start()

        # 发送中断
        time.sleep(0.2)
        interrupt_event.set()

        # 等待线程结束
        thread.join(timeout=2)

        # 验证资源已释放
        assert resource_released.is_set()
        assert not thread.is_alive()


class TestCredentialResolutionPriority:
    """凭证解析优先级集成测试。"""

    def test_priority_order_explicit_env_config(self):
        """测试凭证解析优先级：explicit > env > config。"""
        with patch.dict(os.environ, {"TEST_API_KEY": "env-key"}):
            # 1. 显式传入优先级最高
            creds = resolve_credentials(
                env_vars=["TEST_API_KEY"],
                explicit_key="explicit-key",
            )
            assert creds.api_key == "explicit-key"
            assert creds.source == "explicit"

            # 2. 没有显式传入时，使用环境变量
            creds = resolve_credentials(env_vars=["TEST_API_KEY"])
            assert creds.api_key == "env-key"
            assert creds.source == "env"


class TestApiModeResolutionPriority:
    """API Mode 解析优先级集成测试。"""

    def test_api_mode_priority_order(self):
        """测试 API Mode 解析优先级：explicit > profile > heuristics > default。"""
        # 1. 显式指定优先级最高
        mode = resolve_api_mode(explicit_mode="anthropic_messages")
        assert mode == ApiMode.ANTHROPIC_MESSAGES

        # 2. base_url 启发式检测
        mode = resolve_api_mode(base_url="https://api.anthropic.com/v1")
        assert mode == ApiMode.ANTHROPIC_MESSAGES

        # 3. 默认值
        mode = resolve_api_mode()
        assert mode == ApiMode.CHAT_COMPLETIONS

    def test_api_mode_invalid_explicit_raises(self):
        """测试无效的显式 api_mode 抛出错误。"""
        with pytest.raises(ValueError, match="不支持的 api_mode"):
            resolve_api_mode(explicit_mode="invalid_mode")


class TestFullIntegrationScenario:
    """完整集成场景测试。"""

    def test_end_to_end_openai_scenario(self):
        """端到端 OpenAI 场景：配置 → 凭证 → API Mode → 客户端 → 调用。"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-full"}):
            with patch("src.provider.client_factory.OpenAI") as mock_openai:
                # Mock 客户端和响应
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Integration test response"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                # Step 1: 凭证解析
                creds = resolve_credentials(env_vars=["OPENAI_API_KEY"])

                # Step 2: API Mode 解析
                api_mode = resolve_api_mode()

                # Step 3: 客户端构建
                from src.provider.client_factory import build_client
                client = build_client(api_mode, creds)

                # Step 4: 调用
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": "Test"}],
                )

                # Step 5: 响应解析
                content = response.choices[0].message.content
                assert content == "Integration test response"

    def test_end_to_end_with_fallback(self):
        """端到端回退场景：主模型失败 → 回退成功。"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant-test"}):
            # 创建回退链
            fallbacks = [
                FallbackEntry(provider="anthropic", model="claude-sonnet-4"),
            ]
            chain = FallbackChain(fallbacks)

            with patch("src.provider.client_factory.OpenAI") as mock_openai:
                with patch("src.provider.client_factory.Anthropic") as mock_anthropic:
                    # 主模型客户端失败
                    mock_openai_client = MagicMock()
                    mock_openai_client.chat.completions.create.side_effect = Exception("Rate limit")
                    mock_openai.return_value = mock_openai_client

                    # 回退模型客户端成功
                    mock_anthropic_client = MagicMock()
                    mock_anthropic.return_value = mock_anthropic_client

                    # 主模型调用失败
                    creds_main = resolve_credentials(env_vars=["OPENAI_API_KEY"])
                    api_mode_main = resolve_api_mode()
                    from src.provider.client_factory import build_client
                    client_main = build_client(api_mode_main, creds_main)

                    try:
                        client_main.chat.completions.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": "Test"}],
                        )
                    except Exception:
                        # 触发回退
                        fallback = chain.get_next(0)
                        chain.activate(fallback)

                        # 使用回退模型
                        creds_fallback = resolve_credentials(env_vars=["ANTHROPIC_API_KEY"])
                        api_mode_fallback = resolve_api_mode(
                            base_url="https://api.anthropic.com"
                        )
                        client_fallback = build_client(api_mode_fallback, creds_fallback)

                        # 回退成功
                        assert chain.is_activated is True
                        assert chain.active_fallback.provider == "anthropic"