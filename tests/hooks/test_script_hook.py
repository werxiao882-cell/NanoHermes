"""ScriptHook 单元测试。"""

import json
import subprocess
from unittest.mock import patch, MagicMock

from src.hooks.script_hook import ScriptHook


class TestScriptHook:
    """测试 ScriptHook 包装类。"""

    def test_script_releases_on_empty_output(self):
        """测试脚本空输出视为放行。"""
        hook = ScriptHook("dummy.sh")
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            hook({}, next_fn)

        assert next_called is True

    def test_script_releases_on_block_false(self):
        """测试脚本输出 block=false 放行。"""
        hook = ScriptHook("dummy.sh")
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"block": False}),
                stderr="",
            )
            hook({}, next_fn)

        assert next_called is True

    def test_script_blocks_on_block_true(self):
        """测试脚本输出 block=true 阻断。"""
        hook = ScriptHook("dummy.sh")
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"block": True, "message": "拒绝"}),
                stderr="",
            )
            hook({}, next_fn)

        assert next_called is False

    def test_script_releases_on_nonzero_exit(self):
        """测试脚本非零退出码放行（故障隔离）。"""
        hook = ScriptHook("dummy.sh")
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            hook({}, next_fn)

        assert next_called is True

    def test_script_releases_on_invalid_json(self):
        """测试脚本非法 JSON 输出放行（故障隔离）。"""
        hook = ScriptHook("dummy.sh")
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
            hook({}, next_fn)

        assert next_called is True

    def test_script_releases_on_timeout(self):
        """测试脚本超时放行（故障隔离）。"""
        hook = ScriptHook("dummy.sh", timeout=1)
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("dummy.sh", 1)):
            hook({}, next_fn)

        assert next_called is True

    def test_script_releases_on_file_not_found(self):
        """测试脚本不存在放行（故障隔离）。"""
        hook = ScriptHook("/nonexistent/script.sh")
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run", side_effect=FileNotFoundError):
            hook({}, next_fn)

        assert next_called is True

    def test_script_passes_data_as_stdin(self):
        """测试脚本通过 stdin 接收 JSON 数据。"""
        hook = ScriptHook("dummy.sh")
        next_called = False

        def next_fn():
            nonlocal next_called
            next_called = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
            test_data = {"tool_name": "terminal", "tool_args": '{"command": "ls"}'}
            hook(test_data, next_fn)

            # 验证 stdin 传入了 JSON
            call_args = mock_run.call_args
            assert call_args.kwargs["input"] == json.dumps(test_data, ensure_ascii=False)

        assert next_called is True
