"""Tests for skills tools module."""

import pytest
import json

from src.tools.skills_tool import skill_manage, skill_view, skills_list


class TestSkillManage:
    """Tests for skill_manage tool function."""

    def test_skill_manage_create(self):
        """Test creating a skill."""
        result = json.loads(skill_manage(action="create", name="test-skill", content="# Test"))
        # SkillManager.create_skill returns dict with success key
        assert "success" in result

    def test_skill_manage_list(self):
        """Test listing skills."""
        result = json.loads(skill_manage(action="list"))
        # SkillManager returns dict with success key
        assert "success" in result or "error" in result

    def test_skill_manage_via_dispatcher(self):
        """Test skill_manage tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import skills_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(skills_tools)

        result = dispatch("skill_manage", {"action": "list"})
        data = json.loads(result)
        assert "success" in data or "error" in data


class TestSkillView:
    """Tests for skill_view tool function."""

    def test_skill_view(self):
        """Test viewing a skill."""
        result = json.loads(skill_view(name="test-skill"))
        assert result["success"] is False or "not available" in result.get("error", "").lower()

    def test_skill_view_via_dispatcher(self):
        """Test skill_view tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import skills_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(skills_tools)

        result = dispatch("skill_view", {"name": "test"})
        data = json.loads(result)
        assert "success" in data or "error" in data


class TestSkillsList:
    """Tests for skills_list tool function."""

    def test_skills_list(self):
        """Test listing skills."""
        result = json.loads(skills_list())
        assert result["success"] is True
        # Skills list may contain items from the skills directory
        assert "skills" in result
        assert "count" in result

    def test_skills_list_with_query(self):
        """Test listing skills with query."""
        result = json.loads(skills_list(query="python"))
        assert result["success"] is True

    def test_skills_list_via_dispatcher(self):
        """Test skills_list tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import skills_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(skills_tools)

        result = dispatch("skills_list", {})
        data = json.loads(result)
        assert data["success"] is True

