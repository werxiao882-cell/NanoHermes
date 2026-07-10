"""循环提示系统测试。"""

import tempfile
from pathlib import Path

from src.loop.prompt import MAINTENANCE_PROMPT, get_maintenance_prompt


class TestMaintenancePrompt:
    """测试维护提示加载。"""

    def test_builtin_prompt_not_empty(self):
        """内置提示不应为空。"""
        assert MAINTENANCE_PROMPT
        assert len(MAINTENANCE_PROMPT) > 100

    def test_builtin_prompt_contains_key_sections(self):
        """内置提示应包含关键段落。"""
        assert "维护模式" in MAINTENANCE_PROMPT
        assert "未完成的工作" in MAINTENANCE_PROMPT
        assert "CI 状态" in MAINTENANCE_PROMPT
        assert "清理任务" in MAINTENANCE_PROMPT
        assert "next_interval" in MAINTENANCE_PROMPT

    def test_no_loop_md_uses_builtin(self, tmp_path):
        """没有 loop.md 时应使用内置提示。"""
        prompt = get_maintenance_prompt(tmp_path)
        assert prompt == MAINTENANCE_PROMPT

    def test_project_loop_md_takes_precedence(self, tmp_path):
        """项目级 loop.md 应优先于用户级。"""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        loop_md = claude_dir / "loop.md"
        loop_md.write_text("项目级自定义提示", encoding="utf-8")

        prompt = get_maintenance_prompt(tmp_path)
        assert prompt == "项目级自定义提示"

    def test_user_loop_md_fallback(self, tmp_path):
        """没有项目级时应回退到用户级。"""
        nanohermes_dir = Path.home() / ".nanohermes"
        nanohermes_dir.mkdir(parents=True, exist_ok=True)
        user_loop_md = nanohermes_dir / "loop.md"

        original_exists = None
        if user_loop_md.exists():
            original_exists = user_loop_md.read_text(encoding="utf-8")

        try:
            user_loop_md.write_text("用户级自定义提示", encoding="utf-8")
            prompt = get_maintenance_prompt(tmp_path)
            assert prompt == "用户级自定义提示"
        finally:
            if original_exists is not None:
                user_loop_md.write_text(original_exists, encoding="utf-8")
            elif user_loop_md.exists():
                user_loop_md.unlink()

    def test_loop_md_truncation(self, tmp_path):
        """超过 25,000 字节的 loop.md 应被截断。"""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        loop_md = claude_dir / "loop.md"

        large_content = "x" * 30_000
        loop_md.write_text(large_content, encoding="utf-8")

        prompt = get_maintenance_prompt(tmp_path)
        assert len(prompt) <= 25_000

    def test_nonexistent_loop_md(self, tmp_path):
        """不存在的 loop.md 文件不应引发异常。"""
        prompt = get_maintenance_prompt(tmp_path)
        assert prompt == MAINTENANCE_PROMPT
