"""TUI 输入系统单元测试。"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from prompt_toolkit.document import Document

from src.cli.completers import CommandCompleter, FilePathCompleter, ContextAwareCompleter
from src.cli.history import TUIHistory


class TestCommandCompleter:
    """命令补全器测试。"""
    
    def test_command_completion(self):
        """测试命令补全。"""
        completer = CommandCompleter()
        doc = Document(text="/he", cursor_position=3)
        completions = list(completer.get_completions(doc, None))
        
        assert len(completions) > 0
        assert any(c.text == "/help" for c in completions)
    
    def test_no_completion_without_slash(self):
        """测试无 / 时不补全。"""
        completer = CommandCompleter()
        doc = Document(text="hello", cursor_position=5)
        completions = list(completer.get_completions(doc, None))
        
        assert len(completions) == 0
    
    def test_multiple_command_matches(self):
        """测试多个命令匹配。"""
        completer = CommandCompleter()
        doc = Document(text="/", cursor_position=1)
        completions = list(completer.get_completions(doc, None))
        
        assert len(completions) >= 6  # 所有命令


class TestFilePathCompleter:
    """文件路径补全器测试。"""
    
    def test_file_path_completion(self, tmp_path):
        """测试文件路径补全。"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.touch()
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()
        
        completer = FilePathCompleter()
        
        # 模拟输入路径
        doc = Document(text=f"{tmp_path}/test", cursor_position=len(f"{tmp_path}/test"))
        completions = list(completer.get_completions(doc, None))
        
        # 应该找到 test.txt 和 testdir
        assert len(completions) >= 1
        assert any("test" in c.text for c in completions)
    
    def test_no_completion_for_non_path(self):
        """测试非路径不补全。"""
        completer = FilePathCompleter()
        doc = Document(text="hello world", cursor_position=11)
        completions = list(completer.get_completions(doc, None))
        
        # 没有路径特征，不补全
        assert len(completions) == 0


class TestContextAwareCompleter:
    """上下文感知补全器测试。"""
    
    def test_delegates_to_command_completer(self):
        """测试委托给命令补全器。"""
        completer = ContextAwareCompleter()
        doc = Document(text="/he", cursor_position=3)
        completions = list(completer.get_completions(doc, None))
        
        assert len(completions) > 0
        assert any(c.text == "/help" for c in completions)
    
    def test_delegates_to_file_completer(self, tmp_path):
        """测试委托给文件补全器。"""
        # Use a unique name to avoid matching sibling pytest temp dirs
        unique_name = "nanohermes_testfile_xyz"
        test_file = tmp_path / f"{unique_name}.txt"
        test_file.touch()
        
        completer = ContextAwareCompleter()
        doc = Document(text=f"{tmp_path}/{unique_name}", cursor_position=len(f"{tmp_path}/{unique_name}"))
        completions = list(completer.get_completions(doc, None))
        
        assert len(completions) >= 1
        assert any(unique_name in c.text for c in completions)


class TestTUIHistory:
    """TUI 历史测试。"""
    
    def test_append_and_load(self, tmp_path):
        """测试添加和加载。"""
        with patch("src.cli.history.HISTORY_DIR", tmp_path), \
             patch("src.cli.history.HISTORY_FILE", tmp_path / "history.json"):
            
            history = TUIHistory()
            history.append_string("hello")
            history.append_string("world")
            
            # load_history_strings 返回同步列表
            loaded = history.load_history_strings()
            
            assert "world" in loaded
            assert "hello" in loaded
    
    def test_no_duplicate_consecutive(self, tmp_path):
        """测试不添加连续重复项。"""
        with patch("src.cli.history.HISTORY_DIR", tmp_path), \
             patch("src.cli.history.HISTORY_FILE", tmp_path / "history.json"):
            
            history = TUIHistory()
            history.append_string("hello")
            history.append_string("hello")
            history.append_string("hello")
            
            assert len(history._store) == 1
    
    def test_no_empty_strings(self, tmp_path):
        """测试不添加空字符串。"""
        with patch("src.cli.history.HISTORY_DIR", tmp_path), \
             patch("src.cli.history.HISTORY_FILE", tmp_path / "history.json"):
            
            history = TUIHistory()
            history.append_string("")
            history.append_string("   ")
            
            assert len(history._store) == 0
    
    def test_max_items_limit(self, tmp_path):
        """测试最大条目限制。"""
        with patch("src.cli.history.HISTORY_DIR", tmp_path), \
             patch("src.cli.history.HISTORY_FILE", tmp_path / "history.json"):
            
            history = TUIHistory(max_items=5)
            for i in range(10):
                history.append_string(f"item{i}")
            
            assert len(history._store) == 5
            # 应该保留最后 5 个
            assert history._store[-1] == "item9"
