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
