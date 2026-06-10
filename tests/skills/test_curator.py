"""Tests for skills curator module."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.skills.curator import Curator, SkillUsage


class TestSkillUsage:
    """Tests for SkillUsage dataclass."""

    def test_default_values(self):
        """Test default values."""
        usage = SkillUsage()
        assert usage.use_count == 0
        assert usage.view_count == 0
        assert usage.patch_count == 0
        assert usage.last_activity_at == 0.0
        assert usage.state == "active"
        assert usage.pinned is False

    def test_custom_values(self):
        """Test custom values."""
        usage = SkillUsage(
            use_count=10,
            view_count=20,
            patch_count=5,
            last_activity_at=12345.0,
            state="stale",
            pinned=True,
        )
        assert usage.use_count == 10
        assert usage.view_count == 20
        assert usage.patch_count == 5
        assert usage.last_activity_at == 12345.0
        assert usage.state == "stale"
        assert usage.pinned is True


class TestCurator:
    """Tests for Curator class."""

    def test_init_default_dir(self):
        """Test initialization with default directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            assert curator._skills_dir == Path(tmpdir)

    def test_init_custom_dir(self):
        """Test initialization with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            assert curator._skills_dir == Path(tmpdir)

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(
                tmpdir,
                min_idle_hours=12.0,
                interval_hours=24.0,
                stale_after_days=60,
                archive_after_days=180,
            )
            assert curator._min_idle_hours == 12.0
            assert curator._interval_hours == 24.0
            assert curator._stale_after_days == 60
            assert curator._archive_after_days == 180

    def test_maybe_run_not_idle(self):
        """Test maybe_run returns False when not idle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, min_idle_hours=1.0)
            curator._last_run = time.time()  # Just ran

            result = curator.maybe_run()
            assert result is False

    def test_maybe_run_interval_not_reached(self):
        """Test maybe_run returns False when interval not reached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, interval_hours=24.0)
            curator._last_run = time.time() - 3600  # 1 hour ago

            result = curator.maybe_run()
            assert result is False

    def test_maybe_run_runs_review(self):
        """Test maybe_run runs review when conditions met."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, min_idle_hours=0.0, interval_hours=0.0)
            curator._last_run = 0  # Long time ago

            result = curator.maybe_run()
            assert result is True
            assert curator._last_run > 0

    def test_load_usage_empty(self):
        """Test _load_usage returns empty dict when no file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            usage = curator._load_usage()
            assert usage == {}

    def test_load_usage_with_file(self):
        """Test _load_usage loads from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            usage_file = curator._skills_dir / ".usage.json"
            usage_file.write_text('{"skill1": {"use_count": 5}}', encoding="utf-8")

            usage = curator._load_usage()
            assert "skill1" in usage
            assert usage["skill1"]["use_count"] == 5

    def test_save_usage(self):
        """Test _save_usage writes to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            usage = {"skill1": {"use_count": 5}}
            curator._save_usage(usage)

            usage_file = curator._skills_dir / ".usage.json"
            assert usage_file.exists()
            content = usage_file.read_text(encoding="utf-8")
            assert "skill1" in content

    def test_record_use(self):
        """Test record_use updates usage data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_use("skill1")

            usage = curator._load_usage()
            assert "skill1" in usage
            assert usage["skill1"]["use_count"] == 1

    def test_load_usage_empty(self):
        """Test _load_usage returns empty dict when no file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            usage = curator._load_usage()
            assert usage == {}

    def test_load_usage_with_file(self):
        """Test _load_usage loads from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            usage_file = curator._skills_dir / ".usage.json"
            usage_file.write_text('{"skill1": {"use_count": 5}}', encoding="utf-8")

            usage = curator._load_usage()
            assert "skill1" in usage
            assert usage["skill1"]["use_count"] == 5

    def test_save_usage(self):
        """Test _save_usage writes to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            usage = {"skill1": {"use_count": 5}}
            curator._save_usage(usage)

            usage_file = curator._skills_dir / ".usage.json"
            assert usage_file.exists()
            content = usage_file.read_text(encoding="utf-8")
            assert "skill1" in content

    def test_entry_to_dict(self):
        """Test _entry_to_dict converts SkillUsage to dict."""
        entry = SkillUsage(
            use_count=10,
            view_count=20,
            patch_count=5,
            last_activity_at=12345.0,
            state="stale",
            pinned=True,
        )
        result = Curator._entry_to_dict(entry)
        assert result["use_count"] == 10
        assert result["view_count"] == 20
        assert result["patch_count"] == 5
        assert result["last_activity_at"] == 12345.0
        assert result["state"] == "stale"
        assert result["pinned"] is True

    def test_run_review_marks_stale(self):
        """Test _run_review marks skills as stale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, stale_after_days=1)
            # Create a skill with old activity
            usage = {
                "skill1": {
                    "use_count": 0,
                    "view_count": 0,
                    "patch_count": 0,
                    "last_activity_at": time.time() - 86400 * 2,  # 2 days ago
                    "state": "active",
                    "pinned": False,
                }
            }
            curator._save_usage(usage)

            curator._run_review()

            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "stale"

    def test_run_review_archives_stale(self):
        """Test _run_review archives stale skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, stale_after_days=1, archive_after_days=2)
            # Create a stale skill with old activity
            usage = {
                "skill1": {
                    "use_count": 0,
                    "view_count": 0,
                    "patch_count": 0,
                    "last_activity_at": time.time() - 86400 * 3,  # 3 days ago
                    "state": "stale",
                    "pinned": False,
                }
            }
            curator._save_usage(usage)

            curator._run_review()

            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "archived"

    def test_run_review_pinned_exempt(self):
        """Test _run_review exempts pinned skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, stale_after_days=1)
            # Create a pinned skill with old activity
            usage = {
                "skill1": {
                    "use_count": 0,
                    "view_count": 0,
                    "patch_count": 0,
                    "last_activity_at": time.time() - 86400 * 2,  # 2 days ago
                    "state": "active",
                    "pinned": True,
                }
            }
            curator._save_usage(usage)

            curator._run_review()

            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "active"  # Still active

    def test_maybe_run_returns_false_when_not_idle(self):
        """Test maybe_run returns False when not idle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, min_idle_hours=1.0)
            curator._last_run = time.time()  # Just ran

            result = curator.maybe_run()
            assert result is False

    def test_maybe_run_returns_false_when_interval_not_reached(self):
        """Test maybe_run returns False when interval not reached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, interval_hours=24.0)
            curator._last_run = time.time() - 3600  # 1 hour ago

            result = curator.maybe_run()
            assert result is False


class TestCuratorLifecycle:
    """测试 Curator 生命周期转换。"""

    def test_mark_stale(self):
        """测试标记技能为 stale。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_use("skill1")
            result = curator.mark_stale("skill1")
            assert result is True
            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "stale"

    def test_mark_stale_nonexistent(self):
        """测试标记不存在的技能。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            result = curator.mark_stale("nonexistent")
            assert result is False

    def test_mark_stale_already_stale(self):
        """测试已 stale 的技能不能重复标记。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_use("skill1")
            curator.mark_stale("skill1")
            result = curator.mark_stale("skill1")
            assert result is False

    def test_archive_skill(self):
        """测试归档技能。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            # Create skill directory for backup
            (Path(tmpdir) / "skill1").mkdir()
            (Path(tmpdir) / "skill1" / "SKILL.md").write_text("# Skill 1", encoding="utf-8")
            curator.record_use("skill1")
            result = curator.archive_skill("skill1")
            assert result is True
            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "archived"

    def test_archive_nonexistent(self):
        """测试归档不存在的技能。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            result = curator.archive_skill("nonexistent")
            assert result is False

    def test_unarchive_skill(self):
        """测试恢复归档技能。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_use("skill1")
            usage = curator._load_usage()
            usage["skill1"]["state"] = "archived"
            curator._save_usage(usage)
            result = curator.unarchive_skill("skill1")
            assert result is True
            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "active"

    def test_auto_transitions_active_to_stale(self):
        """测试自动转换 active → stale。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, stale_after_days=1)
            old_time = time.time() - 86400 * 2  # 2 days ago
            usage = {
                "skill1": {
                    "use_count": 0,
                    "view_count": 0,
                    "patch_count": 0,
                    "last_activity_at": old_time,
                    "state": "active",
                    "pinned": False,
                }
            }
            curator._save_usage(usage)
            result = curator.auto_transitions("skill1")
            assert result is not None
            assert result["from"] == "active"
            assert result["to"] == "stale"

    def test_auto_transitions_pinned_exempt(self):
        """测试 pinned 技能不自动转换。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, stale_after_days=1)
            old_time = time.time() - 86400 * 2
            usage = {
                "skill1": {
                    "use_count": 0,
                    "view_count": 0,
                    "patch_count": 0,
                    "last_activity_at": old_time,
                    "state": "active",
                    "pinned": True,
                }
            }
            curator._save_usage(usage)
            result = curator.auto_transitions("skill1")
            assert result is None

    def test_spawn_review_agent(self):
        """测试生成审查任务。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_use("skill1")
            result = curator.spawn_review_agent("skill1")
            assert result["task"] == "review_skill"
            assert result["skill_name"] == "skill1"
            assert result["usage"]["use_count"] == 1

    def test_record_view(self):
        """测试记录查看。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_view("skill1")
            usage = curator._load_usage()
            assert usage["skill1"]["view_count"] == 1

    def test_record_patch(self):
        """测试记录补丁。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_patch("skill1")
            usage = curator._load_usage()
            assert usage["skill1"]["patch_count"] == 1

    def test_set_pinned(self):
        """测试设置置顶。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_use("skill1")
            result = curator.set_pinned("skill1", True)
            assert result is True
            usage = curator._load_usage()
            assert usage["skill1"]["pinned"] is True

    def test_set_pinned_nonexistent(self):
        """测试设置不存在的技能置顶。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            result = curator.set_pinned("nonexistent", True)
            assert result is False

    def test_create_backup_creates_tar_gz(self):
        """测试创建 tar.gz 备份。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            skill_dir = Path(tmpdir) / "skill1"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")
            backup_path = curator._create_backup("skill1")
            assert backup_path is not None
            assert backup_path.endswith(".tar.gz")
            assert Path(backup_path).exists()

    def test_create_backup_nonexistent_dir(self):
        """测试不存在的技能目录备份。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            result = curator._create_backup("nonexistent")
            assert result is None


class TestCuratorStateTransitions:
    """测试技能生命周期状态转换。"""

    def test_active_to_stale(self):
        """测试 active → stale 转换。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, stale_after_days=1)
            old_time = time.time() - 86400 * 2
            usage = {
                "skill1": {
                    "use_count": 0, "view_count": 0, "patch_count": 0,
                    "last_activity_at": old_time, "state": "active", "pinned": False,
                }
            }
            curator._save_usage(usage)
            curator._run_review()
            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "stale"

    def test_stale_to_archived(self):
        """测试 stale → archived 转换。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir, stale_after_days=1, archive_after_days=2)
            old_time = time.time() - 86400 * 3
            usage = {
                "skill1": {
                    "use_count": 0, "view_count": 0, "patch_count": 0,
                    "last_activity_at": old_time, "state": "stale", "pinned": False,
                }
            }
            curator._save_usage(usage)
            curator._run_review()
            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "archived"

    def test_restore_archived_skill(self):
        """测试恢复归档技能。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            curator = Curator(tmpdir)
            curator.record_use("skill1")
            usage = curator._load_usage()
            usage["skill1"]["state"] = "archived"
            curator._save_usage(usage)
            result = curator.unarchive_skill("skill1")
            assert result is True
            usage = curator._load_usage()
            assert usage["skill1"]["state"] == "active"

