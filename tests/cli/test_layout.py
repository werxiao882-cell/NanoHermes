"""TUI 布局系统单元测试。"""

import pytest
from unittest.mock import patch, MagicMock

from src.cli.layout import LayoutManager, LayoutConfig, DynamicPanelManager


class TestLayoutManager:
    """布局管理器测试。"""
    
    def test_init_default_config(self):
        """测试默认配置初始化。"""
        manager = LayoutManager()
        
        assert manager.config.min_width == 80
        assert manager.config.min_height == 24
        assert manager.config.show_tool_panel is True
    
    def test_init_custom_config(self):
        """测试自定义配置初始化。"""
        config = LayoutConfig(min_width=100, show_tool_panel=False)
        manager = LayoutManager(config=config)
        
        assert manager.config.min_width == 100
        assert manager.config.show_tool_panel is False
    
    @patch("src.cli.layout.get_terminal_size")
    def test_get_layout_fullscreen(self, mock_size):
        """测试全屏布局。"""
        mock_size.return_value = (120, 40)
        config = LayoutConfig(show_tool_panel=False)
        manager = LayoutManager(config=config)
        
        layout = manager.get_layout()
        
        assert layout["type"] == "fullscreen"
        assert layout["width"] == 120
        assert layout["height"] == 40
    
    @patch("src.cli.layout.get_terminal_size")
    def test_get_layout_vertical_split(self, mock_size):
        """测试垂直分割布局。"""
        mock_size.return_value = (120, 40)
        config = LayoutConfig(show_tool_panel=True, tool_panel_position="right")
        manager = LayoutManager(config=config)
        
        layout = manager.get_layout()
        
        assert layout["type"] == "vertical_split"
        assert "main" in layout
        assert "tool_panel" in layout
    
    @patch("src.cli.layout.get_terminal_size")
    def test_get_layout_horizontal_split(self, mock_size):
        """测试水平分割布局。"""
        mock_size.return_value = (120, 40)
        config = LayoutConfig(show_tool_panel=True, tool_panel_position="bottom")
        manager = LayoutManager(config=config)
        
        layout = manager.get_layout()
        
        assert layout["type"] == "horizontal_split"
    
    @patch("src.cli.layout.get_terminal_size")
    def test_check_min_size_ok(self, mock_size):
        """测试最小尺寸检查（通过）。"""
        mock_size.return_value = (100, 30)
        manager = LayoutManager()
        
        ok, msg = manager.check_min_size()
        
        assert ok is True
        assert msg == ""
    
    @patch("src.cli.layout.get_terminal_size")
    def test_check_min_size_warning(self, mock_size):
        """测试最小尺寸检查（警告）。"""
        mock_size.return_value = (60, 20)
        manager = LayoutManager()
        
        ok, msg = manager.check_min_size()
        
        assert ok is False
        assert "过小" in msg
    
    def test_update_config(self):
        """测试更新配置。"""
        manager = LayoutManager()
        manager.update_config(min_width=100, show_tool_panel=False)
        
        assert manager.config.min_width == 100
        assert manager.config.show_tool_panel is False
    
    def test_register_resize_handler(self):
        """测试注册调整大小处理函数。"""
        manager = LayoutManager()
        handler = MagicMock()
        manager.register_resize_handler(handler)
        
        assert handler in manager._resize_handlers
    
    def test_unregister_resize_handler(self):
        """测试注销调整大小处理函数。"""
        manager = LayoutManager()
        handler = MagicMock()
        manager.register_resize_handler(handler)
        manager.unregister_resize_handler(handler)
        
        assert handler not in manager._resize_handlers


class TestDynamicPanelManager:
    """动态面板管理器测试。"""
    
    @pytest.fixture
    def panel_manager(self):
        """创建面板管理器。"""
        layout_manager = LayoutManager()
        return DynamicPanelManager(layout_manager)
    
    def test_create_panel(self, panel_manager):
        """测试创建面板。"""
        panel_manager.create_panel("tools", {"title": "Tools"})
        
        assert "tools" in panel_manager._panels
        assert panel_manager._panels["tools"]["title"] == "Tools"
    
    def test_destroy_panel(self, panel_manager):
        """测试销毁面板。"""
        panel_manager.create_panel("tools", {})
        panel_manager.destroy_panel("tools")
        
        assert "tools" not in panel_manager._panels
    
    def test_get_panel(self, panel_manager):
        """测试获取面板。"""
        panel_manager.create_panel("tools", {"title": "Tools"})
        panel = panel_manager.get_panel("tools")
        
        assert panel is not None
        assert panel["title"] == "Tools"
    
    def test_get_nonexistent_panel(self, panel_manager):
        """测试获取不存在的面板。"""
        panel = panel_manager.get_panel("nonexistent")
        
        assert panel is None
    
    def test_list_panels(self, panel_manager):
        """测试列表面板。"""
        panel_manager.create_panel("tools", {})
        panel_manager.create_panel("status", {})
        
        panels = panel_manager.list_panels()
        
        assert "tools" in panels
        assert "status" in panels
        assert len(panels) == 2
    
    def test_rearrange_panels(self, panel_manager):
        """测试重排面板。"""
        panel_manager.create_panel("tools", {})
        panel_manager.rearrange_panels()
        
        # 应该不抛出异常
        assert True
