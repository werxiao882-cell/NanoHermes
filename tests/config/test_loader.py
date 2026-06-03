"""配置加载和优先级测试。

测试 src/config/loader.py 中的配置加载、合并和优先级逻辑。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest


class TestLoadJsonFile:
    """load_json_file 函数测试。"""

    def test_load_valid_json(self):
        """测试加载有效 JSON 文件。"""
        from src.config.loader import load_json_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json.dumps({"key": "value"}))
            f.flush()
            result = load_json_file(Path(f.name))
            assert result == {"key": "value"}
        os.unlink(f.name)

    def test_file_not_exists(self):
        """测试文件不存在。"""
        from src.config.loader import load_json_file
        result = load_json_file(Path("/nonexistent/file.json"))
        assert result is None

    def test_invalid_json(self):
        """测试无效 JSON。"""
        from src.config.loader import load_json_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            f.flush()
            result = load_json_file(Path(f.name))
            assert result is None
        os.unlink(f.name)

    def test_non_dict_root(self):
        """测试根节点不是对象。"""
        from src.config.loader import load_json_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json.dumps(["list", "not", "dict"]))
            f.flush()
            result = load_json_file(Path(f.name))
            assert result is None
        os.unlink(f.name)


class TestDeepMerge:
    """deep_merge 函数测试。"""

    def test_simple_merge(self):
        """测试简单合并。"""
        from src.config.loader import deep_merge
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """测试嵌套合并。"""
        from src.config.loader import deep_merge
        base = {"model": {"provider": "openai", "name": "gpt-4"}}
        override = {"model": {"name": "gpt-4o"}}
        result = deep_merge(base, override)
        assert result == {"model": {"provider": "openai", "name": "gpt-4o"}}

    def test_list_override(self):
        """测试列表完全覆盖（不递归合并）。"""
        from src.config.loader import deep_merge
        base = {"servers": [{"name": "a"}, {"name": "b"}]}
        override = {"servers": [{"name": "c"}]}
        result = deep_merge(base, override)
        assert result == {"servers": [{"name": "c"}]}

    def test_empty_override(self):
        """测试空覆盖。"""
        from src.config.loader import deep_merge
        base = {"a": 1, "b": 2}
        override = {}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}


class TestResolveEnvCredentials:
    """resolve_env_credentials 函数测试。"""

    def test_resolve_env_value(self):
        """测试解析 _env 后缀字段。"""
        from src.config.loader import resolve_env_credentials
        with mock.patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = resolve_env_credentials({"url_env": "TEST_VAR"})
            assert result == {"url_env": "test_value"}

    def test_api_key_env_preserved(self):
        """测试 api_key_env 保留环境变量名。"""
        from src.config.loader import resolve_env_credentials
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            result = resolve_env_credentials({"api_key_env": "OPENAI_API_KEY"})
            # api_key_env 保留变量名，不替换为实际值
            assert result == {"api_key_env": "OPENAI_API_KEY"}

    def test_nested_resolve(self):
        """测试嵌套解析。"""
        from src.config.loader import resolve_env_credentials
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            result = resolve_env_credentials({
                "providers": {
                    "openai": {"api_key_env": "OPENAI_API_KEY"},
                },
                "url_env": "OPENAI_API_KEY",
            })
            assert result["providers"]["openai"]["api_key_env"] == "OPENAI_API_KEY"
            assert result["url_env"] == "sk-test"


class TestLoadEnvDefaults:
    """load_env_defaults 函数测试。"""

    def test_model_name_from_env(self):
        """测试从环境变量读取模型名称。"""
        from src.config.loader import load_env_defaults
        with mock.patch.dict(os.environ, {"MODEL_NAME": "gpt-4o"}, clear=True):
            result = load_env_defaults()
            assert result["model"]["name"] == "gpt-4o"

    def test_openai_provider_from_env(self):
        """测试从环境变量读取 OpenAI 提供商配置。"""
        from src.config.loader import load_env_defaults
        with mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://custom.api/v1",
        }, clear=True):
            result = load_env_defaults()
            assert "openai" in result["providers"]
            assert result["providers"]["openai"]["api_key_env"] == "OPENAI_API_KEY"
            assert result["providers"]["openai"]["base_url"] == "https://custom.api/v1"

    def test_dashscope_provider_from_env(self):
        """测试从环境变量读取 DashScope 提供商配置。"""
        from src.config.loader import load_env_defaults
        with mock.patch.dict(os.environ, {
            "DASHSCOPE_API_KEY": "ds-test",
        }, clear=True):
            result = load_env_defaults()
            assert "dashscope" in result["providers"]
            assert result["providers"]["dashscope"]["api_key_env"] == "DASHSCOPE_API_KEY"


class TestLoadConfigPriority:
    """load_config 优先级测试。"""

    def test_explicit_params_override(self):
        """测试显式参数覆盖。"""
        from src.config.loader import load_config
        with mock.patch.dict(os.environ, {
            "DASHSCOPE_API_KEY": "ds-test",
            "MODEL_NAME": "qwen-plus",
        }, clear=True):
            # 显式参数应覆盖环境变量
            config = load_config(model="gpt-4o", provider="openai")
            assert config.model.name == "gpt-4o"
            assert config.model.provider == "openai"

    def test_project_config_override_global(self):
        """测试项目配置覆盖全局配置。"""
        from src.config.loader import load_config, PROJECT_CONFIG, GLOBAL_CONFIG
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建全局配置
            global_config = Path(tmpdir) / "global.json"
            global_config.write_text(json.dumps({
                "model": {"provider": "dashscope", "name": "qwen-plus"},
            }))
            # 创建项目配置
            project_config = Path(tmpdir) / "project.json"
            project_config.write_text(json.dumps({
                "model": {"provider": "openai", "name": "gpt-4o"},
            }))
            with mock.patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test"}, clear=True):
                with mock.patch.object(Path, "home", return_value=Path(tmpdir)):
                    config = load_config(config_file=str(project_config))
                    # 项目配置应覆盖全局
                    assert config.model.name == "gpt-4o"


class TestGetApiKey:
    """get_api_key 函数测试。"""

    def test_from_provider_config(self):
        """测试从提供商配置获取。"""
        from src.config.loader import get_api_key
        from src.config.models import Config, ProviderConfig
        with mock.patch.dict(os.environ, {"TEST_KEY": "test-value"}):
            config = Config(
                model={"provider": "test"},
                providers={
                    "test": ProviderConfig(api_key_env="TEST_KEY"),
                },
            )
            key = get_api_key(config)
            assert key == "test-value"

    def test_from_common_env_vars(self):
        """测试从常见环境变量回退。"""
        from src.config.loader import get_api_key
        from src.config.models import Config
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            config = Config(model={"provider": "unknown"})
            key = get_api_key(config)
            assert key == "sk-test"


class TestGetBaseUrl:
    """get_base_url 函数测试。"""

    def test_from_provider_config(self):
        """测试从提供商配置获取。"""
        from src.config.loader import get_base_url
        from src.config.models import Config, ProviderConfig
        config = Config(
            model={"provider": "custom"},
            providers={
                "custom": ProviderConfig(base_url="https://custom.url/v1"),
            },
        )
        url = get_base_url(config)
        assert url == "https://custom.url/v1"

    def test_from_provider_registry(self):
        """测试从 provider 注册表获取默认值。"""
        from src.config.loader import get_base_url
        from src.config.models import Config
        # 导入 builtins 以注册提供商
        import src.provider.builtins
        config = Config(model={"provider": "openai"})
        url = get_base_url(config)
        # 应从注册表获取 OpenAI 默认 URL
        assert url == "https://api.openai.com/v1"