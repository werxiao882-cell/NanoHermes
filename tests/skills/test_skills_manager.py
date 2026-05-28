"""Tests for skills manager module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.skills.manager import SkillManager, SkillEntry
from src.skills.loader import Skill


class TestSkillEntry:
    """Tests for SkillEntry dataclass."""

    def test_default_values(self):
        """Test default values."""
        skill = Skill(name="test", description="Test")
        entry = SkillEntry(skill=skill)
        assert entry.skill == skill
        assert entry.enabled is True
        assert entry.use_count == 0
        assert entry.last_used_at == 0.0

    def test_custom_values(self):
        """Test custom values."""
        skill = Skill(name="test", description="Test")
        entry = SkillEntry(
            skill=skill,
            enabled=False,
            use_count=5,
            last_used_at=12345.0,
        )
        assert entry.enabled is False
        assert entry.use_count == 5
        assert entry.last_used_at == 12345.0


class TestSkillManager:
    """Tests for SkillManager class."""

    def test_init_default_dir(self):
        """Test initialization with default directory."""
        with patch.object(Path, "home") as mock_home:
            mock_home.return_value = Path("/tmp")
            manager = SkillManager()
            assert manager.skills_dir == Path("/tmp/.nanohermes/skills")

    def test_init_custom_dir(self):
        """Test initialization with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            assert manager.skills_dir == Path(tmpdir)

    def test_init_creates_dir(self):
        """Test initialization creates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            manager = SkillManager(skills_dir)
            assert skills_dir.exists()

    def test_get_skill_not_found(self):
        """Test get_skill returns None for non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            assert manager.get_skill("nonexistent") is None

    def test_list_skills_empty(self):
        """Test list_skills returns empty list when no skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            assert manager.list_skills() == []

    def test_enable_skill_not_found(self):
        """Test enable_skill returns False for non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            assert manager.enable_skill("nonexistent") is False

    def test_disable_skill_not_found(self):
        """Test disable_skill returns False for non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            assert manager.disable_skill("nonexistent") is False

    def test_record_use_not_found(self):
        """Test record_use does nothing for non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            # Should not raise
            manager.record_use("nonexistent")

    def test_build_skill_prompt_empty(self):
        """Test build_skill_prompt returns empty when no skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            assert manager.build_skill_prompt() == ""

    def test_build_skill_prompt_with_skills(self):
        """Test build_skill_prompt returns formatted prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            # Manually add a skill
            skill = Skill(name="test", description="Test skill")
            manager._skills["test"] = SkillEntry(skill=skill)

            prompt = manager.build_skill_prompt()

            assert "## Available Skills" in prompt
            assert "**test**" in prompt
            assert "Test skill" in prompt
            assert "To use a skill" in prompt

    def test_build_skill_prompt_disabled_skills(self):
        """Test build_skill_prompt excludes disabled skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            skill = Skill(name="test", description="Test skill")
            entry = SkillEntry(skill=skill, enabled=False)
            manager._skills["test"] = entry

            prompt = manager.build_skill_prompt()

            assert prompt == ""

    def test_list_skills_enabled_only(self):
        """Test list_skills with enabled_only=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            skill1 = Skill(name="s1", description="Skill 1")
            skill2 = Skill(name="s2", description="Skill 2")
            manager._skills["s1"] = SkillEntry(skill=skill1, enabled=True)
            manager._skills["s2"] = SkillEntry(skill=skill2, enabled=False)

            enabled = manager.list_skills(enabled_only=True)
            assert len(enabled) == 1
            assert enabled[0].skill.name == "s1"

    def test_enable_skill(self):
        """Test enable_skill enables a skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            skill = Skill(name="test", description="Test")
            manager._skills["test"] = SkillEntry(skill=skill, enabled=False)

            result = manager.enable_skill("test")
            assert result is True
            assert manager._skills["test"].enabled is True

    def test_disable_skill(self):
        """Test disable_skill disables a skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            skill = Skill(name="test", description="Test")
            manager._skills["test"] = SkillEntry(skill=skill, enabled=True)

            result = manager.disable_skill("test")
            assert result is True
            assert manager._skills["test"].enabled is False

    def test_record_use(self):
        """Test record_use increments use count."""
        import time
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            skill = Skill(name="test", description="Test")
            manager._skills["test"] = SkillEntry(skill=skill)

            before_time = time.time()
            manager.record_use("test")
            after_time = time.time()

            assert manager._skills["test"].use_count == 1
            assert before_time <= manager._skills["test"].last_used_at <= after_time

    def test_reload_clears_skills(self):
        """Test _reload clears and reloads skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            skill = Skill(name="test", description="Test")
            manager._skills["test"] = SkillEntry(skill=skill)

            manager._reload()
            assert "test" not in manager._skills
