"""Tests for skills loader module."""

import pytest
import tempfile
from pathlib import Path

from src.skills.loader import SkillLoader, Skill, slugify


class TestSkill:
    """Tests for Skill dataclass."""

    def test_default_values(self):
        """Test default values."""
        skill = Skill(name="test", description="Test skill")
        assert skill.name == "test"
        assert skill.description == "Test skill"
        assert skill.version == "1.0.0"
        assert skill.author == ""
        assert skill.license == ""
        assert skill.platforms is None
        assert skill.body == ""
        assert skill.path == ""

    def test_custom_values(self):
        """Test custom values."""
        skill = Skill(
            name="test",
            description="Test skill",
            version="2.0.0",
            author="Author",
            license="MIT",
            platforms=["linux", "macos"],
            body="Body content",
            path="/path/to/skill",
        )
        assert skill.version == "2.0.0"
        assert skill.author == "Author"
        assert skill.license == "MIT"
        assert skill.platforms == ["linux", "macos"]
        assert skill.body == "Body content"
        assert skill.path == "/path/to/skill"


class TestSkillLoader:
    """Tests for SkillLoader class."""

    def test_load_valid_skill(self):
        """Test loading a valid SKILL.md file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test-skill\n"
                "description: A test skill\n"
                "version: 1.0.0\n"
                "author: Test Author\n"
                "license: MIT\n"
                "---\n"
                "# Test Skill\n"
                "This is the skill body.",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)

            assert skill.name == "test-skill"
            assert skill.description == "A test skill"
            assert skill.version == "1.0.0"
            assert skill.author == "Test Author"
            assert skill.license == "MIT"
            assert "This is the skill body" in skill.body
            assert skill.path == str(skill_file)

    def test_load_missing_frontmatter(self):
        """Test loading file without frontmatter succeeds with inferred name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdirectory to infer name from
            skill_dir = Path(tmpdir) / "my-skill"
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text("# My Skill\n\nBody content", encoding="utf-8")

            loader = SkillLoader()
            # Should load successfully with inferred name
            skill = loader.load(skill_file)
            assert skill.name == "my-skill"  # inferred from directory
            assert "Body content" in skill.body

    def test_load_missing_name(self):
        """Test loading skill without name raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "description: No name\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            with pytest.raises(ValueError, match="缺少 name 字段"):
                loader.load(skill_file)

    def test_load_description_too_long(self):
        """Test loading skill with long description succeeds (no length limit)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test\n"
                "description: " + "x" * 61 + "\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)
            assert skill.name == "test"
            assert len(skill.description) == 61

    def test_load_with_platforms(self):
        """Test loading skill with platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test\n"
                "description: Test\n"
                "platforms: [linux, macos]\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)
            # platforms 应该被正确解析为列表
            assert skill.platforms == ["linux", "macos"]

    def test_parse_frontmatter_simple(self):
        """Test parsing simple frontmatter."""
        loader = SkillLoader()
        text = (
            "---\n"
            "name: test\n"
            "description: Test\n"
            "---\n"
            "Body"
        )
        frontmatter, body = loader._parse_frontmatter(text)
        assert frontmatter["name"] == "test"
        assert frontmatter["description"] == "Test"
        assert body == "Body"

    def test_parse_frontmatter_quoted_values(self):
        """Test parsing frontmatter with quoted values."""
        loader = SkillLoader()
        text = (
            "---\n"
            "name: 'test'\n"
            'description: "Test"\n'
            "---\n"
            "Body"
        )
        frontmatter, body = loader._parse_frontmatter(text)
        assert frontmatter["name"] == "test"
        assert frontmatter["description"] == "Test"


class TestSkillTriggerRules:
    """Tests for trigger/skip fields in Skill and SkillLoader."""

    def test_skill_trigger_skip_defaults(self):
        """Test default trigger/skip are None."""
        skill = Skill(name="test", description="Test")
        assert skill.trigger is None
        assert skill.skip is None

    def test_skill_trigger_skip_custom(self):
        """Test custom trigger/skip values."""
        skill = Skill(
            name="test",
            description="Test",
            trigger=["when X", "when Y"],
            skip=["when Z"],
        )
        assert skill.trigger == ["when X", "when Y"]
        assert skill.skip == ["when Z"]

    def test_load_skill_with_trigger_skip_yaml(self):
        """Test loading skill with trigger/skip as YAML lists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: deploy\n"
                "description: Deploy app\n"
                "trigger:\n"
                "  - when user wants to deploy\n"
                "  - when asked to release\n"
                "skip:\n"
                "  - when in dev mode\n"
                "---\n"
                "Deploy instructions...",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)
            assert skill.trigger == ["when user wants to deploy", "when asked to release"]
            assert skill.skip == ["when in dev mode"]

    def test_load_skill_with_trigger_skip_semicolon(self):
        """Test loading skill with trigger/skip as semicolon-separated strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test\n"
                "description: Test\n"
                "trigger: when X; when Y\n"
                "skip: when Z\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)
            assert skill.trigger == ["when X", "when Y"]
            assert skill.skip == ["when Z"]

    def test_load_skill_without_trigger_skip(self):
        """Test loading skill without trigger/skip fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test\n"
                "description: Test\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)
            assert skill.trigger is None
            assert skill.skip is None


class TestSlugify:
    """Tests for slugify function."""

    def test_simple_text(self):
        """Test slugifying simple text."""
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        """Test slugifying text with special characters."""
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        """Test slugifying text with multiple spaces."""
        assert slugify("Hello   World") == "hello-world"

    def test_underscores(self):
        """Test slugifying text with underscores."""
        assert slugify("Hello_World") == "hello-world"

    def test_mixed_case(self):
        """Test slugifying mixed case text."""
        assert slugify("HelloWorld") == "helloworld"

    def test_empty_string(self):
        """Test slugifying empty string."""
        assert slugify("") == ""

    def test_leading_trailing_whitespace(self):
        """Test slugifying text with leading/trailing whitespace."""
        assert slugify("  Hello World  ") == "hello-world"
